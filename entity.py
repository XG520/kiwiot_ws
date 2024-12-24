import logging
from homeassistant.components.image import ImageEntity
from homeassistant.helpers.entity import Entity, DeviceInfo
from .const import DOMAIN, LOGGER_NAME
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image
from io import BytesIO
import base64
import aiohttp
import asyncio

_LOGGER = logging.getLogger(f"{LOGGER_NAME}_{__name__}")

class GroupEntity(Entity):
    def __init__(self, hass, name, gid, device_count):
        """初始化组实体."""
        self.hass = hass
        self._name = name
        self._gid = gid
        self._device_count = device_count

    @property
    def name(self):
        """返回实体的名称."""
        return self._name

    @property
    def state(self):
        """返回实体的状态."""
        return self._device_count

    @property
    def unique_id(self):
        """返回实体的唯一 ID."""
        return f"group_{self._gid}"

    @property
    def device_info(self):
        """返回设备信息，用于将实体关联到设备."""
        return {
            "identifiers": {(DOMAIN, self._gid)},
            "name": self._name,
            "manufacturer": "XG520",
            "model": "Group Model",
            "sw_version": "1.0",
        }

    @property
    def extra_state_attributes(self):
        """返回额外的状态属性."""
        return {
            "gid": self._gid,
            "device_count": self._device_count,
        }


class DeviceEntity(Entity):
    def __init__(self, hass, name, gid, device_info):
        """初始化设备实体."""
        self.hass = hass
        self._name = name
        self._gid = gid
        self._device_info = device_info
        self._device_type = device_info.get("type")

    @property
    def name(self):
        """返回实体的名称."""
        return self._name

    @property
    def state(self):
        """返回实体的状态."""
        return self._device_type

    @property
    def unique_id(self):
        """返回实体的唯一 ID."""
        return f"device_{self._gid}_{self._name}"

    @property
    def device_info(self):
        """返回设备信息，用于将实体关联到设备."""
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
        """返回额外的状态属性."""
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

class KiwiLockInfo(Entity):
    """获取组名"""
    def __init__(self, device, group):
        self._device = device
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{DOMAIN}_{device.device_id}_info"
        self._attr_name = "家庭"
        self._group = group

    @property
    def device_info(self):
        """返回设备信息"""
        return self._device.get_device_info()

    @property
    def state(self):
        return self._group.get("name", "unknown")

class KiwiLockImage(ImageEntity):
    """门锁图片实体"""
    def __init__(self, device, event_data):
        self._device = device
        self._event_data = event_data
        self._attr_has_entity_name = True
        timestamp = int(datetime.now().timestamp() * 1000)
        self._attr_unique_id = f"{DOMAIN}_{device.device_id}_image_{timestamp}"
        self._attr_name = "记录"
        self._image_data = None
        self._access_tokens = []

    @property
    def device_info(self):
        """返回设备信息"""
        return self._device.get_device_info()

    @property
    def image_url(self):
        """返回图片URL"""
        if (self._event_data and 
            "data" in self._event_data and 
            "image" in self._event_data["data"]):
            return self._event_data["data"]["image"].get("uri")
        return "https://via.placeholder.com/640x960.png"  

    async def async_download_image(self):
        """异步下载图片并存储在 _image_data 中"""
        url = self.image_url
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.read()
                    image = Image.open(BytesIO(data))
                    buffered = BytesIO()
                    image.save(buffered, format="JPEG")
                    self._image_data = buffered.getvalue()
                else:
                    _LOGGER.error(f"无法下载图片，状态码: {response.status}")

    @property
    def entity_picture(self):
        """返回实体的图片 URL"""
        if self._image_data:
            return f"data:image/jpeg;base64,{base64.b64encode(self._image_data).decode()}"
        return self.image_url

    @property
    def extra_state_attributes(self):
        """返回额外属性"""
        attributes = {}
        
        # 添加时间信息
        if "created_at" in self._event_data:
            try:
                event_time_utc = datetime.fromisoformat(
                    self._event_data["created_at"].replace('Z', '+00:00')
                )
                event_time_local = event_time_utc.astimezone(ZoneInfo("Asia/Shanghai"))
                attributes["time"] = event_time_local.strftime("%Y-%m-%d %H:%M:%S")
            except Exception as e:
                _LOGGER.error(f"处理时间失败: {e}")
        
        # 添加用户信息
        if (self._event_data and 
            "data" in self._event_data and 
            "lock_user" in self._event_data["data"]):
            lock_user = self._event_data["data"]["lock_user"]
            attributes.update({
                "user_id": lock_user.get("id"),
                "user_type": lock_user.get("type")
            })
            
        return attributes

    async def async_rotate_image(self, image_url):
        """获取图片并旋转90度"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        image = Image.open(BytesIO(image_data))
                        rotated_image = image.rotate(-90, expand=True)
                        buffered = BytesIO()
                        rotated_image.save(buffered, format="JPEG")
                        self._image_data = buffered.getvalue()
                    else:
                        _LOGGER.error(f"无法获取图片，状态码: {response.status}")
        except Exception as e:
            _LOGGER.error(f"旋转图片失败: {e}")

    @property
    def access_tokens(self):
        """返回访问令牌"""
        if self._access_tokens:
            return self._access_tokens
        return ["default_token"]

    async def async_update(self):
        """更新实体状态"""
        await self.async_download_image()
        self._state = self._event_data.get("name", "UNKNOWN")
        self._attributes = self.extra_state_attributes

class KiwiLockStatus(Entity):
    """状态"""
    def __init__(self, device, event):
        self._device = device
        self._event = event
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{DOMAIN}_{device.device_id}_status"
        self._attr_name = "状态"
        self._state = None
        self._attributes = {}

    @property
    def device_info(self):
        """返回设备信息"""
        return self._device.get_device_info()

    @property
    def extra_state_attributes(self):
        """返回额外属性"""
        return self._attributes

    async def async_update(self):
        """更新实体状态"""
        self._state = self._event.get("status", "UNKNOWN")
        self._attributes = self._event.get("attributes", {})

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
        return self._unique_id  

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
