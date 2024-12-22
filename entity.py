import logging
from homeassistant.helpers.entity import Entity
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
    def name(self):
        return f"Group {self._name}"

    @property
    def unique_id(self):
        return f"kiwiot_group_{self._group_id}"
    
    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._group_id)},
            "name": self._name,
            "manufacturer": "KiwiOT",
            "model": "Device Group",
            "sw_version": "1.0"
        }

class KiwiLockDevice(Entity):
    """锁设备实体"""
    def __init__(self, hass, device_info, group_id):
        self.hass = hass
        self._info = device_info
        self._device_id = device_info["did"]
        self._name = device_info["name"] 
        self._group_id = group_id

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return f"kiwiot_lock_{self._device_id}"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._name,
            "manufacturer": "KiwiOT",
            "model": "Smart Lock",
            "via_device": (DOMAIN, self._group_id)
        }

class KiwiLockUser(Entity):
    """锁用户实体"""
    def __init__(self, hass, lock_device, user_info):
        self.hass = hass
        self._lock_device = lock_device
        self._user_info = user_info
        self._user_type = user_info["type"]
        self._user_number = user_info["number"]

    @property
    def name(self):
        return f"{self._lock_device.name} {self._user_type} User {self._user_number}"

    @property
    def unique_id(self):
        return f"kiwiot_user_{self._lock_device._device_id}_{self._user_type}_{self._user_number}"

    @property
    def state(self):
        return self._user_info["updated_at"]
        
    @property
    def device_info(self):
        return self._lock_device.device_info

class KiwiLockEvent(Entity):
    """锁事件实体"""
    def __init__(self, hass, lock_device, event_info):
        self.hass = hass
        self._lock_device = lock_device
        self._event_info = event_info
        self._event_time = datetime.strptime(event_info["created_at"], "%Y-%m-%dT%H:%M:%SZ")

    @property
    def name(self):
        return f"{self._lock_device.name} Event {self._event_info['name']}"

    @property
    def unique_id(self):
        return f"kiwiot_event_{self._lock_device._device_id}_{self._event_time.timestamp()}"
        
    @property
    def state(self):
        return self._event_info["name"]

    @property 
    def device_info(self):
        return self._lock_device.device_info

    @property
    def extra_state_attributes(self):
        return {
            "level": self._event_info["level"],
            "created_at": self._event_info["created_at"],
            "data": self._event_info["data"]
        }
