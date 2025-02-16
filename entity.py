import logging
import aiohttp

from homeassistant.helpers.entity import Entity, DeviceInfo
from .const import DOMAIN, LOGGER_NAME
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image, ImageFile
from io import BytesIO
from homeassistant.components.camera import Camera
from homeassistant.const import STATE_UNKNOWN
from homeassistant.const import EntityCategory

_LOGGER = logging.getLogger(f"{LOGGER_NAME}_{__name__}")

ImageFile.LOAD_TRUNCATED_IMAGES = True

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
    def __init__(self, hass, device, group):
        self.hass = hass
        self._device = device
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{DOMAIN}_{device.device_id}_info"
        self._attr_name = "家庭"
        self._group = group
        self._attr_entity_category = None
        self._attr_translation_key = "lock_info"
        self._attr_should_poll = False

    @property
    def device_info(self):
        """返回设备信息"""
        return self._device.get_device_info()
    
    @property
    def icon(self):
        return "mdi:home"

    @property
    def state(self):
        return self._group.get("name", "unknown")


class KiwiLockStatus(Entity):
    """状态"""
    USER_TYPE_MAP = {
        "FACE": "人脸",
        "PASSWORD": "密码",
        "FINGERPRINT": "指纹"
    }
    STATE_MAP = {
        "UNLOCKED": "锁已经打开",
        "LOCKED": "锁已锁上",
        "LOCK_INDOOR_BUTTON_UNLOCK": "门内按键开锁",
    }
    def __init__(self, hass, device, event, history_events):
        self.hass = hass
        self._device = device
        self._event = event
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{DOMAIN}_{device.device_id}_status"
        self._attr_name = "门锁状态"
        self._event_time = None
        self._event_history = history_events or []
        self._attr_entity_category = None 
        self._attr_entity_registry_enabled_default = True
        self._attr_entity_registry_visible_default = True
        self._attr_translation_key = "lock_status"
        self._attr_should_poll = False

        try:
            event_time_utc = datetime.fromisoformat(event["created_at"].replace('Z', '+00:00'))
            event_time_local = event_time_utc.astimezone(ZoneInfo("Asia/Shanghai"))
            self._event_time = event_time_local.strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            _LOGGER.error(f"处理事件时间失败: {e}")
            self._event_time = str(datetime.now())
        

    @property
    def device_info(self):
        """返回设备信息"""
        return self._device.get_device_info()

    @property
    def icon(self):
        if self._event.get("name") == "UNLOCKED" or self._event.get("name") == "LOCK_INDOOR_BUTTON_UNLOCK":
            return "mdi:door-open"
        elif self._event.get("name") == "LOCKED":
            return "mdi:door-closed-lock"
        else:
            return "mdi:alert-circle"

    @property
    def state(self):
        name = self._event.get("name", "unknown")   
        return self.STATE_MAP.get(name, name)

    @property
    def extra_state_attributes(self):
        """返回额外的状态属性"""
        if self._event.get("name") == "LOCK_INDOOR_BUTTON_UNLOCK":
            attributes = {
                "更新时间": self._event_time,
                "设备ID": self._device.device_id,
                "用户ID": "unknown",
                "开关锁方式": "门内按键开锁",
                "图像地址": "unknown",
                "类型": self._event.get("level", "unknown"),
            }
            return attributes
        else:
            return {
                "更新时间": self._event_time,
                "设备ID": self._device.device_id,
                "用户ID": self._event.get("data", {}).get("lock_user", {}).get("id", "unknown"),
                "开关锁方式": self.USER_TYPE_MAP.get(self._event.get("data", {}).get("lock_user", {}).get("type", "unknown"), "unknown"),
                "图像地址": self._event.get("data", {}).get("image", {}).get("uri", "unknown"),                
                "类型": self._event.get("level", "unknown"),

            }
    
class KiwiLockEvent(Entity):
    """事件"""
    USER_TYPE_MAP = {
        "FACE": "人脸",
        "PASSWORD": "密码",
        "FINGERPRINT": "指纹"
    }
    STATE_MAP = {
        "UNLOCKED": "锁已经打开",
        "LOCKED": "锁已锁上",
        "LOCK_INDOOR_BUTTON_UNLOCK": "门内按键开锁",
        "HUMAN_WANDERING": "有人徘徊",
        "LOCK_ADD_USER": "添加用户"
    }
    def __init__(self, hass, device, event, history_events, users):
        self.hass = hass
        self._device = device
        self._event = event
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{DOMAIN}_{device.device_id}_event"
        self._attr_name = "门锁事件"
        self._event_time = None
        self._event_history = history_events or []
        self._users = users
        self._attr_entity_category = None  
        self._attr_entity_registry_enabled_default = True
        self._attr_entity_registry_visible_default = True
        self._attr_translation_key = "lock_event"
        self._attr_should_poll = False

        try:
            event_time_utc = datetime.fromisoformat(event["created_at"].replace('Z', '+00:00'))
            event_time_local = event_time_utc.astimezone(ZoneInfo("Asia/Shanghai"))
            self._event_time = event_time_local.strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            _LOGGER.error(f"处理事件时间失败: {e}")
            self._event_time = str(datetime.now())
        

    @property
    def device_info(self):
        """返回设备信息"""
        return self._device.get_device_info()

    @property
    def icon(self):
        if self._event.get("name") == "UNLOCKED":
            return "mdi:door-open"
        elif self._event.get("name") == "LOCKED":
            return "mdi:door-closed-lock"
        else:
            return "mdi:alert-circle"

    @property
    def state(self):
        name = self._event.get("name", "unknown")
        data = self._event.get("data", "unknown")
        lock_user = data.get("lock_user", {})
        event_type = lock_user.get("type", "unknown")
        user_id = lock_user.get("id", "unknown")
        alias = user_id
        if self._users and isinstance(self._users, list):
            try:
                user_id_int = int(user_id) if user_id != "unknown" else -1
                matching_user = next(
                    (user for user in self._users 
                     if user.get("type") == event_type 
                     and user.get("number") == user_id_int),
                    None
                )
                if matching_user and matching_user.get("alias"):
                    alias = matching_user["alias"]
            except (ValueError, TypeError) as e:
                _LOGGER.warning(f"处理用户ID时出错: {e}")
        if name == "UNLOCKED" and event_type == "FACE":
            return f"{alias}人脸解锁"
        elif name == "UNLOCKED" and event_type == "PASSWORD":
            return f"{alias}密码解锁"
        elif name == "UNLOCKED" and event_type == "FINGERPRINT":
            return f"{alias}指纹解锁"
        else:    
            return self.STATE_MAP.get(name, name)

    @property
    def extra_state_attributes(self):
        """返回额外的状态属性"""

        attributes = {
            "更新时间": self._event_time,
            "设备ID": self._device.device_id,
            "类型": self._event.get("level", "unknown"),
            "数据": self._event.get("data", "unknown")
        }

        # if self._event_history:
        #     attributes["history"] = self._event_history

        return attributes


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
        self._attr_entity_category = EntityCategory.CONFIG 
        self._attr_translation_key = "lock_user"
        self._attr_should_poll = False
        
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
        alias = self._user_info.get("alias", "")
        if not alias:
            return "No Alias"
        else:
            return alias
        
    @property
    def icon(self):
        if self._user_type == "FACE":
            return "mdi:face-recognition"
        elif self._user_type == "PASSWORD":
            return "mdi:key"
        elif self._user_type == "FINGERPRINT":
            return "mdi:fingerprint"
        else:
            return "mdi:account"
        
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
            "类型": self._user_type,
            "用户id": self._user_number,
            "created_at": self._user_info.get("created_at"),
            "updated_at": self._user_info.get("updated_at")
        }

class KiwiLockCamera(Camera):
    USER_TYPE_MAP = {
        "FACE": "人脸",
        "PASSWORD": "密码",
        "FINGERPRINT": "指纹"
    }
    STATE_MAP = {
        "UNLOCKED": "锁已经打开",
        "LOCKED": "锁已锁上",
        "LOCK_INDOOR_BUTTON_UNLOCK": "门内按键开锁",
        "HUMAN_WANDERING": "有人徘徊"
    }

    def __init__(self, hass, device, event_data, video_info):
        super().__init__()
        self.hass = hass
        self._device = device
        self._event_data = event_data
        self._video_info = video_info
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{DOMAIN}_{device.device_id}_camera"
        self._attr_name = "最近一次图像事件"
        self._attr_is_streaming = False
        self._state = STATE_UNKNOWN

    @property
    def device_info(self):
        return self._device.get_device_info()

    @property
    def state(self):
        if not self._event_data:
            return STATE_UNKNOWN
        name = self._event_data.get("name", "")
        return self.STATE_MAP.get(name, name)

    @property
    def extra_state_attributes(self):
        if not self._event_data:
            return {}

        data = self._event_data.get("data", {})
        lock_user = data.get("lock_user", {})
        
        # 获取用户类型并转换
        user_type = lock_user.get("type", "")
        displayed_type = self.USER_TYPE_MAP.get(user_type, user_type)
        
        return {
            "level": self._event_data.get("level"),
            "created_at": self._event_data.get("created_at"),
            "用户ID": lock_user.get("id"),
            "开锁类型": displayed_type,
            "事件时间": self._event_data.get("created_at")
        }

    async def async_camera_image(self, width=320, height=480):
        """获取摄像头图片或视频."""
        if self._video_info and "media" in self._video_info and "uri" in self._video_info["media"]:
            url = self._video_info["media"]["uri"]
        elif (self._event_data and 
              "data" in self._event_data and 
              "image" in self._event_data["data"] and
              "uri" in self._event_data["data"]["image"]):
            url = self._event_data["data"]["image"]["uri"]
        else:
            return None
            
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    if response.status != 200:
                        return None
                    image_data = await response.read()
                    image = Image.open(BytesIO(image_data))
                    rotated_image = image.rotate(-90, expand=True)
                    output = BytesIO()
                    rotated_image.save(output, format=image.format)
                    return output.getvalue()
            except Exception as ex:
                _LOGGER.error("获取图片或视频失败: %s", ex)
                return None