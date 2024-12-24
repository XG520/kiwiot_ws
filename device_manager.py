﻿import logging
from aiohttp import ClientSession
from homeassistant.core import HomeAssistant

from .const import LOGGER_NAME
from .userinfo import get_ggid, get_ddevices, get_llock_userinfo, get_llock_info
from .entity import KiwiLockDevice, KiwiLockInfo, KiwiLockStatus, KiwiLockUser, KiwiLockImage
from .utils import get_latest_event

_LOGGER = logging.getLogger(f"{LOGGER_NAME}_{__name__}")

async def initialize_devices_and_groups(hass: HomeAssistant, access_token: str, session: ClientSession, callback):
    """初始化设备和组信息."""
    try:
        groups = await get_ggid(hass, access_token, session)
        if not groups:
            _LOGGER.error("获取组信息失败")
            return

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

                    test_data ={
                                "device_id":"32E8329FCB40",
                                "name":"UNLOCKED",
                                "level":"INFO",
                                "data":{
                                    "image":{
                                        "uri":"https://ims.kwicdn.com/bb8d5c2ddc79c27723be09eec76c4348/676B6A94/hghJEBfUST9/m515fcw9.jpg"
                                        },
                                    "lock_user":{
                                        "id":5,
                                        "type":"FINGERPRINT"
                                        }
                                    },
                                "created_at":"2024-12-23T14:44:58Z"
                                }

                    device_entities = [
                        KiwiLockInfo(lock_device, group),
                        KiwiLockStatus(lock_device, latest_event),
                        KiwiLockImage(lock_device, test_data)
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

                    callback(device_entities)

    except Exception as e:
        _LOGGER.error(f"初始化设备和组信息时发生错误: {e}")