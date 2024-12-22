﻿import logging
from homeassistant.helpers.entity import Entity, DeviceInfo
from .const import DOMAIN, LOGGER_NAME
from datetime import datetime

_LOGGER = logging.getLogger(f"{LOGGER_NAME}_{__name__}")

class GroupEntity(Entity):
    def __init__(self, hass, name, gid, device_count):
        self.hass = hass
        self._name = name
        self._gid = gid
        self._device_count = device_count

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._device_count

    @property
    def unique_id(self):
        return f"group_{self._gid}"

    @property
    def device_info(self):
        # 确保 identifiers 唯一且通过 DOMAIN 关联
        return {
            "identifiers": {(DOMAIN, self._gid)},
            "name": self._name,
            "manufacturer": "XG520",
            "model": "Group Model",
            "sw_version": "1.0",
        }

    @property
    def extra_state_attributes(self):
        return {
            "gid": self._gid,
            "device_count": self._device_count,
        }


class DeviceEntity(Entity):
    def __init__(self, hass, name, gid, device_info):
        self.hass = hass
        self._name = name
        self._gid = gid
        self._device_info = device_info
        self._device_type = device_info.get("type")

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._device_info

    @property
    def unique_id(self):
        return f"device_{self._gid}_{self._name}"

    @property
    def device_info(self):
        # 通过 `via_device` 确保设备关联到组
        return {
            "identifiers": {(DOMAIN, f"device_{self._gid}_{self._name}")},
            "name": self._name,
            "manufacturer": "未知",
            "model": "Device Model",
            "sw_version": "1.0",
            "via_device": (DOMAIN, self._gid),
        }

    @property
    def extra_state_attributes(self):
        return {
            "gid": self._gid,
            "device_type": self._device_type,
        }

class LockUserEntity(Entity):
    def __init__(self, hass, device_name, did, user_info):
        self.hass = hass
        self._device_name = device_name
        self._did = did
        self._user_info = user_info

    @property
    def name(self):
        return f"{self._device_name} 用户 {self._user_info['number']}"

    @property
    def state(self):
        return self._user_info

class LockEventEntity(Entity):
    def __init__(self, hass, device_name, did, event_info):
        self.hass = hass
        self._device_name = device_name
        self._did = did
        self._event_info = event_info

    @property
    def name(self):
        return f"{self._device_name} 事件 {self._event_info['name']}"

    @property
    def state(self):
        return self._event_info

    @property
    def device_state_attributes(self):
        return {
            "created_at": self._event_info["created_at"],
            "level": self._event_info["level"],
            "data": self._event_info["data"]
        }

class KiwiDeviceGroup(Entity):
    """设备组实体"""
    def __init__(self, hass, group_info):
        self.hass = hass 
        self._info = group_info
        self._group_id = group_info["gid"]
        self._name = group_info["name"]
        self._created_at = group_info["created_at"]

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"group_{self._group_id}")},  # 修改标识符格式
            "name": f"智能家居群组 - {self._name}",
            "manufacturer": "KiwiOT",
            "model": "Device Group",
            "sw_version": "1.0"
        }

    @property
    def unique_id(self):
        """提供唯一ID"""
        return f"{DOMAIN}_group_{self._group_id}"

class KiwiLockDevice:
    """表示一个智能锁设备"""
    def __init__(self, hass, device_info, group_id, group_name):
        self.hass = hass
        self.device_info = device_info
        self.device_id = device_info["did"]
        self.name = device_info["name"]
        self.group_id = group_id
        self.group_name = group_name
        self.unique_id = f"{DOMAIN}_{self.device_id}"
        
    def get_device_info(self):
        """返回设备信息"""
        return DeviceInfo(
            identifiers={(DOMAIN, self.device_id)},
            name=f"{self.group_name} - {self.name}",
            manufacturer="KiwiOT",
            model="Smart Lock",
            via_device=(DOMAIN, f"group_{self.group_id}"),
            sw_version=self.device_info.get("version", "unknown")
        )

class KiwiLockStatus(Entity):
    """锁状态实体"""
    def __init__(self, device):
        self._device = device
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{DOMAIN}_{device.device_id}_status"
        self._attr_name = "Status"

    @property
    def device_info(self):
        """返回设备信息"""
        return self._device.get_device_info()

    @property
    def state(self):
        return self._device.device_info.get("status", "unknown")

class KiwiLockBattery(Entity):
    """锁电量实体"""
    def __init__(self, device):
        self._device = device
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{DOMAIN}_{device.device_id}_battery"
        self._attr_name = "Battery"

    @property
    def device_info(self):
        """返回设备信息"""
        return self._device.get_device_info()

    @property
    def state(self):
        return self._device.device_info.get("battery", 0)

class KiwiLockUser(Entity):
    """锁用户实体"""
    def __init__(self, hass, lock_device, user_info, device_id, unique_id):
        """初始化锁用户实体
        
        Args:
            hass: HomeAssistant 实例
            lock_device: KiwiLockDevice 实例
            user_info: 用户信息字典
        """
        self.hass = hass
        self._lock_device = lock_device
        self._user_info = user_info
        self._user_type = user_info.get("type", "unknown")
        self._user_number = user_info.get("number", "unknown")
        self._device_id = device_id
        self._unique_id = unique_id
        
    @property
    def name(self):
        """实体名称"""
        return f"{self._lock_device.name} User {self._user_number}"

    @property
    def unique_id(self):
        """唯一标识符"""
        return self._unique_id  # 使用传入的唯一标识符

    @property
    def state(self):
        """实体状态"""
        return self._user_info.get("updated_at", "unknown")
        
    @property
    def device_info(self):
        """设备信息"""
        return {
            "identifiers": {(DOMAIN, self._device_id)},
        }

    @property
    def extra_state_attributes(self):
        """额外属性"""
        return {
            "type": self._user_type,
            "number": self._user_number,
            "created_at": self._user_info.get("created_at"),
            "updated_at": self._user_info.get("updated_at")
        }

class KiwiLockEvent(Entity):
    """锁事件实体"""
    def __init__(self, hass, lock_device, event_info, device_id, unique_id):
        self.hass = hass
        self._lock_device = lock_device
        self._event_info = event_info
        self._event_time = datetime.strptime(event_info["created_at"], "%Y-%m-%dT%H:%M:%SZ")
        self._device_id = device_id
        self._unique_id = unique_id

    @property
    def name(self):
        return f"{self._lock_device.name} Event {self._event_info['name']}"

    @property
    def unique_id(self):
        return self._unique_id  # 使用传入的唯一标识符
        
    @property
    def state(self):
        return self._event_info["name"]

    @property 
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
        }

    @property
    def extra_state_attributes(self):
        return {
            "level": self._event_info["level"],
            "created_at": self._event_info["created_at"],
            "data": self._event_info["data"]
        }
