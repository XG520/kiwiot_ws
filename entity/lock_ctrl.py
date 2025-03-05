import logging
from homeassistant.helpers.entity import Entity
from homeassistant.components.text import TextEntity
from homeassistant.const import EntityCategory
from ..const import DOMAIN, LOGGER_NAME
from ..conn.userinfo import create_mfa_token

_LOGGER = logging.getLogger(f"{LOGGER_NAME}_{__name__}")

class KiwiLockPasswordInput(TextEntity):
    """密码输入实体，用于远程开锁验证"""
    def __init__(self, hass, lock_device, uid, device_id):
        self.hass = hass
        self._lock_device = lock_device
        self._device_id = device_id
        self._uid = uid
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{DOMAIN}_{device_id}_password_input"
        self._attr_name = "远程开锁密码"
        self._attr_native_value = ""
        self._attr_mode = "password"  
        self._attr_native_max = 32
        self._attr_entity_category = None
        self._attr_translation_key = "password_input"
        self._attr_should_poll = False

    @property
    def icon(self):
        """返回实体图标."""
        return "mdi:form-textbox-password"

    @property
    def device_info(self):
        """返回设备信息."""
        return {
            "identifiers": {(DOMAIN, self._device_id)},
        }

    async def async_set_value(self, value: str) -> None:
        """处理密码输入并发送验证请求."""
        if not value or value.strip() == "":
            raise ValueError("密码不能为空")

        domain_data = self.hass.data.get(DOMAIN, {})
        token_manager = domain_data.get("token_manager")
        session = domain_data.get("session")
        access_token = domain_data.get("access_token")

        if not all([token_manager, session, access_token]):
            raise ValueError("无法获取必要组件")

        try:
            success = await create_mfa_token(
                self.hass,
                access_token,
                self._uid,
                value,
                session
            )
            
            if success:
                self._attr_native_value = ""  
                self.async_write_ha_state()
                return

        except Exception as e:
            if "invalid_token" in str(e):
                _LOGGER.info("Token已失效，尝试刷新...")
                try:
                    new_token = await token_manager.get_token(session)
                    if not new_token:
                        raise ValueError("刷新token失败")
                    
                    domain_data["access_token"] = new_token
                    success = await create_mfa_token(
                        self.hass,
                        new_token,
                        self._uid,
                        value,
                        session
                    )
                    
                    if success:
                        self._attr_native_value = ""
                        self.async_write_ha_state()
                        return

                except Exception as token_error:
                    _LOGGER.error(f"刷新token时发生错误: {token_error}")
                    raise ValueError(f"验证失败: {token_error}")
            else:
                _LOGGER.error(f"验证过程中发生错误: {e}")
                raise ValueError(f"验证失败: {e}")

        raise ValueError("验证失败")