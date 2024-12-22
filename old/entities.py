import aiohttp
import logging
from homeassistant.helpers.entity import Entity
from .const import DOMAIN,LOGGER_NAME,BASE_URL

_LOGGER = logging.getLogger(LOGGER_NAME)

# class UserEntity(Entity):
#     """用户信息实体."""

#     def __init__(self, hass, access_token):
#         self.hass = hass
#         self.access_token = access_token
#         self._state = None
#         self._attributes = {}

#     @property
#     def name(self):
#         return "User Information"

#     @property
#     def state(self):
#         return self._state

#     @property
#     def extra_state_attributes(self):
#         return self._attributes

#     async def async_update(self):
#         url = f"{BASE_URL}/user?access_token={self.access_token}"
#         async with aiohttp.ClientSession() as session:
#             async with session.get(url) as response:
#                 if response.status == 200:
#                     data = await response.json()
#                     self._state = data.get("display_name", "Unknown")
#                     self._attributes.update(data)
#                 else:
#                     _LOGGER.error("无法获取用户信息: %s", response.status)

class UserEntity(Entity):
    """用户信息实体."""

    def __init__(self, hass, access_token):
        self.hass = hass
        self.access_token = access_token
        self._state = None
        self._attributes = {}

    @property
    def name(self):
        return "User Information"

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return self._attributes

    async def async_update(self):
        session = self.hass.data[DOMAIN]["session"]
        url = f"{BASE_URL}/user?access_token={self.access_token}"
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    self._state = data.get("display_name", "Unknown")
                    self._attributes.update(data)
                else:
                    _LOGGER.error("无法获取用户信息: %s", response.status)
        except Exception as e:
            _LOGGER.error("更新用户信息时发生错误: %s", e)

class GroupEntity(Entity):
    """家庭信息实体."""

    def __init__(self, hass, access_token, session):
        self.hass = hass
        self.access_token = access_token
        self.session = session
        self.groups = []

    async def async_update(self):
        url = f"{BASE_URL}/groups?access_token={self.access_token}"
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    self.groups = await response.json()
                else:
                    _LOGGER.error("无法获取家庭信息: %s", response.status)
        except Exception as e:
            _LOGGER.error("更新家庭信息时发生错误: %s", e)

    async def get_device_entities(self):
        """根据家庭信息创建设备实体."""
        device_entities = []
        for group in self.groups:
            gid = group["gid"]
            url = f"{BASE_URL}/groups/{gid}/devices?access_token={self.access_token}"
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        devices = await response.json()
                        for device in devices:
                            device_entities.append(DeviceEntity(self.hass, gid, device))
                    else:
                        _LOGGER.error("无法获取设备信息: %s", response.status)
            except Exception as e:
                _LOGGER.error("获取设备信息时发生错误: %s", e)
        return device_entities



# class GroupEntity(Entity):
#     """家庭信息实体."""

#     def __init__(self, hass, access_token):
#         self.hass = hass
#         self.access_token = access_token
#         self._state = None
#         self._attributes = {}
#         self.groups = []

#     @property
#     def name(self):
#         return "Group Information"

#     @property
#     def state(self):
#         return len(self.groups)

#     @property
#     def extra_state_attributes(self):
#         return {"groups": self.groups}

#     async def async_update(self):
#         url = f"{BASE_URL}/groups?access_token={self.access_token}"
#         async with aiohttp.ClientSession() as session:
#             async with session.get(url) as response:
#                 if response.status == 200:
#                     data = await response.json()
#                     self.groups = data
#                     self._state = len(data)
#                     self._attributes.update({"groups": data})
#                 else:
#                     _LOGGER.error("无法获取家庭信息: %s", response.status)

#     async def get_device_entities(self):
#         """根据家庭信息创建设备实体."""
#         device_entities = []
#         for group in self.groups:
#             gid = group["gid"]
#             url = f"{BASE_URL}/groups/{gid}/devices?access_token={self.access_token}"
#             async with aiohttp.ClientSession() as session:
#                 async with session.get(url) as response:
#                     if response.status == 200:
#                         devices = await response.json()
#                         for device in devices:
#                             device_entities.append(DeviceEntity(self.hass, gid, device))
#                     else:
#                         _LOGGER.error("无法获取设备信息: %s", response.status)
#         return device_entities

class DeviceEntity(Entity):
    """设备实体."""

    def __init__(self, hass, gid, device_data):
        self.hass = hass
        self.gid = gid
        self.device_data = device_data
        self._state = device_data.get("type", "Unknown")
        self._attributes = device_data

    @property
    def name(self):
        return f"Device {self.device_data.get('name', 'Unknown')}"

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return self._attributes

    async def async_update(self):
        """设备状态通常可以从外部实时更新."""
        pass  # 如果需要实时更新设备状态，可以实现此方法

class TextEntity(Entity):
    """文本实体，用于表示设备信息."""

    def __init__(self, hass, gid, group_name, device_data):
        self.hass = hass
        self.gid = gid
        self.group_name = group_name
        self.device_data = device_data
        self._state = device_data.get("name", "Unknown Device")
        self._attributes = {
            "type": device_data.get("type", "Unknown"),
            "device_id": device_data.get("did", "Unknown ID"),
            "group_name": group_name
        }

    @property
    def name(self):
        return f"Device {self.device_data.get('name', 'Unknown')}"

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return self._attributes

    async def async_update(self):
        """设备状态通常可以从外部实时更新."""
        pass  # 如果需要实时更新设备状态，可以在此实现逻辑