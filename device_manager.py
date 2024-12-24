import logging
from aiohttp import ClientSession
from homeassistant.core import HomeAssistant

from .const import LOGGER_NAME
from .userinfo import get_ggid, get_ddevices, get_llock_userinfo, get_llock_info
from .entity import KiwiLockDevice, KiwiLockInfo, KiwiLockStatus, KiwiLockUser, KiwiLockImage
from .utils import get_latest_event

_LOGGER = logging.getLogger(f"{LOGGER_NAME}_{__name__}")

async def initialize_devices_and_groups(hass: HomeAssistant, access_token: str, session: ClientSession):
    """初始化设备和组信息."""
    try:
        groups = await get_ggid(hass, access_token, session)
        if not groups:
            _LOGGER.error("获取组信息失败")
            return None

        entities_to_add = []

        for group in groups:
            devices = await get_ddevices(hass, access_token, group["gid"], session)
            if not devices:
                _LOGGER.warning(f"组 {group['gid']} 内没有设备")
                continue

            for device_info in devices:
                if device_info["type"] == "LOCK":
                    lock_device = KiwiLockDevice(
                        hass,
                        device_info,
                        group["gid"],
                        group["name"]
                    )
                    _LOGGER.info(f"设备信息: {lock_device.device_info}")

                    users = await get_llock_userinfo(hass, access_token, device_info["did"], session)
                    events = await get_llock_info(hass, access_token, device_info["did"], session)
                    latest_event = await get_latest_event(events)

                    device_entities = [
                        KiwiLockInfo(lock_device, group),
                        KiwiLockStatus(lock_device, latest_event)
                    ]

                    if users:
                        _LOGGER.info(f"用户数据结构: {users[0]}")
                        for user_count, user in enumerate(users, start=1):
                            try:
                                user_id = user.get("number", "unknown")
                                user_entity = KiwiLockUser(
                                    hass,
                                    lock_device,
                                    user,
                                    device_id=lock_device.device_id,
                                    unique_id=f"{lock_device.unique_id}_user_{user_id}_{user_count}"
                                )
                                device_entities.append(user_entity)
                            except Exception as e:
                                _LOGGER.error(f"创建用户实体失败: {e}, user_data: {user}")
                                continue

                    entities_to_add.extend(device_entities)

        return entities_to_add

    except Exception as e:
        _LOGGER.error(f"初始化设备和组信息时发生错误: {e}")
        return None