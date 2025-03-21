import logging
from .const import LOGGER_NAME
from .conn.userinfo import (
    get_ggid, 
    get_ddevices, 
    get_llock_userinfo, 
    get_llock_info, 
    get_llock_video, 
    get_user_info
    )
from .entity.lock import (
    KiwiLockDevice, 
    KiwiLockInfo, 
    KiwiLockEvent, 
    KiwiLockUser, 
    KiwiLockCamera, 
    KiwiLockStatus
    )
from .entity.lock_ctrl import KiwiLockPasswordInput, KiwiLockPasswordConfirm, KiwiLockUnlockDataInput
from .conn.utils import (
    get_latest_event, 
    get_history_events, 
    get_latest_event_with_data
    )

_LOGGER = logging.getLogger(f"{LOGGER_NAME}_{__name__}")


async def initialize_devices_and_groups(hass, entry, session, callback):
    """初始化设备和组信息."""
    try:
        groups = await get_ggid(hass, entry, session)
        if not groups:
            _LOGGER.error("获取组信息失败")
            return

        all_device_entities = []  
        for group in groups:
            devices = await get_ddevices(hass, entry, group["gid"], session)
            if not devices:
                _LOGGER.warning(f"组 {group['gid']} 内没有设备")
                continue

            for device_info in devices:
                if device_info["type"] == "LOCK":
                    lock_device = KiwiLockDevice(hass, device_info, group["gid"], group["name"])
                    _LOGGER.info(f"设备信息: {lock_device.device_info}")  

                    users = await get_llock_userinfo(hass, entry, device_info["did"], session)
                    master = await get_user_info(hass, entry, session)
                    master_uid = master.get("uid", "unknown")
                    #_LOGGER.info(f"主人数据结构示例: {master}")
                    events = await get_llock_info(hass, entry, device_info["did"], session)
                    latest_event = await get_latest_event(events)
                    latest_data_event = await get_latest_event_with_data(events)
                    history_events = await get_history_events(events)
                    video_info = None
                    if latest_data_event.get("name") == "HUMAN_WANDERING":
                        stream_id = latest_data_event.get("data", {}).get("stream_id")
                        video_info = await get_llock_video(hass, entry, device_info["did"], session, stream_id)
                        
                    _LOGGER.info(f"图像事件: {video_info}")

                    password_input = KiwiLockPasswordInput(hass, lock_device, master_uid, device_info["did"])
                    unlock_data_input = KiwiLockUnlockDataInput(hass, lock_device, master_uid, device_info["did"])
                    password_confirm = KiwiLockPasswordConfirm(hass, entry, lock_device, master_uid, device_info["did"], password_input, unlock_data_input)
                    device_entities = [
                        KiwiLockStatus(hass, lock_device, latest_event, history_events),  
                        KiwiLockEvent(hass, lock_device, latest_event, history_events, users),  
                        KiwiLockInfo(hass, lock_device, group),
                        password_input, 
                        password_confirm,
                        unlock_data_input,
                        KiwiLockCamera(hass, lock_device, latest_data_event, video_info) 
                    ]

                    if users:
                        #_LOGGER.info(f"用户数据结构示例: {users[0]}")  
                        for user_count, user in enumerate(users, start=1):
                            try:
                                user_id = user.get("number", "unknown")
                                user_entity = KiwiLockUser(
                                    hass,
                                    entry,
                                    lock_device,
                                    user,
                                    device_id=lock_device.device_id,
                                    unique_id=f"{lock_device.unique_id}_user_{user_id}_{user_count}"
                                )
                                device_entities.append(user_entity)
                            except ValueError as ve:  
                                _LOGGER.error(f"创建用户实体时发生值错误: {ve}, user_data: {user}")
                                continue
                            except Exception as e:  
                                _LOGGER.error(f"创建用户实体失败: {e}, user_data: {user}")
                                continue

                    all_device_entities.extend(device_entities)  

        callback(all_device_entities)  

    except Exception as e:  
        _LOGGER.error(f"初始化设备和组信息时发生错误: {e}")