import logging
from homeassistant.helpers.entity import Entity
from homeassistant.components.text import TextEntity
from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from ..const import DOMAIN, LOGGER_NAME
from ..conn.userinfo import create_mfa_token
import asyncio
from datetime import datetime, timedelta
from ..conn.websocket import send_unlock_command

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
        return "mdi:form-textbox-password"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
        }

    async def async_set_value(self, value: str) -> None:
        """仅保存密码值"""
        if not value or value.strip() == "":
            raise ValueError("密码不能为空")
        self._attr_native_value = value
        self.async_write_ha_state()

class KiwiLockUnlockDataInput(TextEntity):
    """密码输入实体，用于远程开锁验证"""
    def __init__(self, hass, lock_device, uid, device_id):
        self.hass = hass
        self._lock_device = lock_device
        self._device_id = device_id
        self._uid = uid
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{DOMAIN}_{device_id}_unlock_data_input"
        self._attr_name = "远程开锁数据"
        self._attr_native_value = ""
        self._attr_mode = "password"  
        self._attr_native_max = 32
        self._attr_entity_category = None
        self._attr_translation_key = "password_input"
        self._attr_should_poll = False

    @property
    def icon(self):
        return "mdi:form-textbox-password"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
        }

    async def async_set_value(self, value: str) -> None:
        if not value or value.strip() == "":
            raise ValueError("DATA不能为空")
        self._attr_native_value = value
        self.async_write_ha_state()

class KiwiLockPasswordConfirm(ButtonEntity):
    """确认按钮实体"""
    def __init__(self, hass, lock_device, uid, device_id, password_entity, unlock_data_entity):
        self.hass = hass
        self._lock_device = lock_device
        self._device_id = device_id
        self._uid = uid
        self._password_entity = password_entity
        self._unlock_data_entity = unlock_data_entity
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{DOMAIN}_{device_id}_password_confirm"
        self._attr_name = "确认开锁"
        self._attr_entity_category = None
        self._attr_translation_key = "password_confirm"
        self._attr_should_poll = False
        self._last_press_time = None
        self._cooldown_period = 60  
        self._update_timer = None
    
    async def _schedule_update(self):
        """安排一个状态更新"""
        await asyncio.sleep(self._cooldown_period)
        self._last_press_time = None
        self.async_write_ha_state()

    @property
    def icon(self):
        return "mdi:lock-open-check"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
        }

    @property
    def available(self) -> bool:
        """检查按钮是否可用(是否在冷却期)."""
        if self._last_press_time is None:
            return True
            
        elapsed = (datetime.now() - self._last_press_time).total_seconds()
        return elapsed >= self._cooldown_period

    async def async_press(self) -> None:
        """按钮按下时处理验证请求"""
        if not self.available:
            remaining = self._cooldown_period - (datetime.now() - self._last_press_time).total_seconds()
            raise ValueError(f"请等待 {int(remaining)} 秒后再试")

        password = self._password_entity._attr_native_value
        if not password:
            raise ValueError("请先输入密码")
        unlock_data = self._unlock_data_entity._attr_native_value
        if not unlock_data:
            raise ValueError("请先输入DATA")

        domain_data = self.hass.data.get(DOMAIN, {})
        token_manager = domain_data.get("token_manager")
        session = domain_data.get("session")
        access_token = domain_data.get("access_token")

        if not all([token_manager, session, access_token]):
            raise ValueError("无法获取必要组件")

        try:
            response = await create_mfa_token(
                self.hass,
                access_token,
                self._uid,
                password,
                session
            )
            _LOGGER.info(f"验证结果: {response}")
            
            if response.get("success"):
                self._last_press_time = datetime.now()  
                self._password_entity._attr_native_value = ""
                self._password_entity.async_write_ha_state()
                self.async_write_ha_state()  
                #开锁ws
                send_token = response.get("data", {}).get("access_token", '')
                _LOGGER.info(f"发送开锁ws: {send_token},unlock_data: {unlock_data},device_id: {self._device_id}")
                await send_unlock_command(self.hass, send_token, unlock_data, self._device_id)
                # 创建自动更新任务
                if self._update_timer:
                    self._update_timer.cancel()
                self._update_timer = asyncio.create_task(self._schedule_update())
                return

        except Exception as e:
            if "invalid_token" in str(e):
                _LOGGER.info("Token已失效，尝试刷新...")
                try:
                    new_token = await token_manager.get_token(session)
                    if not new_token:
                        raise ValueError("刷新token失败")
                    
                    domain_data["access_token"] = new_token
                    self.hass.data[DOMAIN]["access_token"] = new_token
                    response = await create_mfa_token(
                        self.hass,
                        new_token,
                        self._uid,
                        password,
                        session
                    )
                    
                    if response.get("success"):
                        self._last_press_time = datetime.now()  
                        self._password_entity._attr_native_value = ""
                        self._password_entity.async_write_ha_state()
                        self.async_write_ha_state() 
                        
                        # 创建自动更新任务
                        if self._update_timer:
                            self._update_timer.cancel()
                        self._update_timer = asyncio.create_task(self._schedule_update())
                        return

                except Exception as token_error:
                    _LOGGER.error(f"刷新token时发生错误: {token_error}")
                    raise ValueError(f"验证失败: {token_error}")
            else:
                _LOGGER.error(f"验证过程中发生错误: {e}")
                raise ValueError(f"验证失败: {e}")

        raise ValueError("验证失败")