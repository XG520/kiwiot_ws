import logging
from homeassistant.components.lock import LockEntity
from .const import LOGGER_NAME

_LOGGER = logging.getLogger(LOGGER_NAME)


class LockEntity(LockEntity):
    """智能锁实体."""

    def __init__(self, hass, gid, group_name, device_data):
        self.hass = hass
        self.gid = gid
        self.group_name = group_name
        self.device_data = device_data
        self._is_locked = device_data.get("verify", False)
        self._state_attributes = device_data

    @property
    def name(self):
        """返回锁的名称."""
        return f"{self.group_name} - {self.device_data.get('name', '未知锁')}"

    @property
    def is_locked(self):
        """返回锁的状态."""
        return self._is_locked

    @property
    def extra_state_attributes(self):
        """返回锁的附加属性."""
        return self._state_attributes

    async def async_lock(self, **kwargs):
        """锁定设备."""
        _LOGGER.debug(f"尝试锁定设备 {self.device_data.get('did')}")
        # 具体的锁定逻辑可以通过云端 API 实现
        self._is_locked = True

    async def async_unlock(self, **kwargs):
        """解锁设备."""
        _LOGGER.debug(f"尝试解锁设备 {self.device_data.get('did')}")
        # 具体的解锁逻辑可以通过云端 API 实现
        self._is_locked = False
