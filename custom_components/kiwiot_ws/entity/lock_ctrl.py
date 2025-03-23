import logging
import os
import json
import aiofiles
from homeassistant.components.text import TextEntity
from homeassistant.components.button import ButtonEntity
from ..const import DOMAIN, LOGGER_NAME
from ..conn.userinfo import create_mfa_token
import asyncio
from datetime import datetime
from ..conn.websocket import send_unlock_command
from pathlib import Path

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
        config_dir = Path(hass.config.path("kiwiot_config"))
        config_dir.mkdir(exist_ok=True)
        self._config_file = config_dir / f"unlock_data_{device_id}.json"
        self._attr_native_value = ""

    async def async_added_to_hass(self) -> None:
        """当实体被添加到 HA 时调用"""
        await self._load_stored_value()
        
    async def _load_stored_value(self) -> None:
        """加载存储的值"""
        try:
            if self._config_file.exists():
                async with aiofiles.open(self._config_file, 'r') as f:
                    content = await f.read()
                    config = json.loads(content)
                    self._attr_native_value = config.get('unlock_data', '')
                    _LOGGER.debug(f"已加载存储的解锁数据: {self._config_file}")
                    self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error(f"加载解锁数据失败: {e}")

    async def _save_value(self, value: str) -> None:
        """保存值到配置文件"""
        try:
            config = {'unlock_data': value}
            async with aiofiles.open(self._config_file, 'w') as f:
                await f.write(json.dumps(config, indent=2))
            _LOGGER.debug(f"已保存解锁数据到: {self._config_file}")
        except Exception as e:
            _LOGGER.error(f"保存解锁数据失败: {e}")
            raise

    async def async_set_value(self, value: str) -> None:
        """设置并保存密码值"""
        if not value or value.strip() == "":
            raise ValueError("解锁数据不能为空")   
        self._attr_native_value = value
        self.async_write_ha_state()
        await self._save_value(value)

    @property
    def icon(self):
        return "mdi:form-textbox-password"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
        }

class KiwiLockPasswordConfirm(ButtonEntity):
    """确认按钮实体"""
    def __init__(self, hass, entry, lock_device, uid, device_id, password_entity, unlock_data_entity):
        self.hass = hass
        self._entry = entry
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
        session = domain_data.get("session")

        if not all([session]):
            raise ValueError("无法获取必要组件")

        response = await create_mfa_token(
            self.hass,
            self._entry,
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
            #_LOGGER.info(f"发送开锁ws: {send_token},unlock_data: {unlock_data},device_id: {self._device_id}")
            await send_unlock_command(self.hass, send_token, unlock_data, self._device_id)
            # 创建自动更新任务
            if self._update_timer:
                self._update_timer.cancel()
            self._update_timer = asyncio.create_task(self._schedule_update())
            return

        raise ValueError("验证失败")