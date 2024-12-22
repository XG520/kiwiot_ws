import logging

from homeassistant.helpers.entity import Entity
from .const import DOMAIN, LOGGER_NAME

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
    def __init__(self, hass, name, gid, device_type):
        self.hass = hass
        self._name = name
        self._gid = gid
        self._device_type = device_type

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._device_type

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
