import asyncio
import logging
from aiohttp import ClientSession, TCPConnector
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import EntityPlatform
from homeassistant.const import Platform

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN, LOGGER_NAME, CONF_IDENTIFIER, CONF_CREDENTIAL, CONF_CLIENT_ID, CONF_IGNORE_SSL
from .websocket import start_websocket_connection
from .token_manager import get_access_token
from .userinfo import get_ggid, get_ddevices, get_llock_userinfo, get_llock_info
from .entity import KiwiLockDevice, KiwiLockInfo, KiwiLockStatus, KiwiLockUser, KiwiLockEvent
from .utils import get_latest_event

_LOGGER = logging.getLogger(f"{LOGGER_NAME}_{__name__}")

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up KiwiOT integration from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    identifier = entry.data.get(CONF_IDENTIFIER)
    credential = entry.data.get(CONF_CREDENTIAL)
    client_id = entry.data.get(CONF_CLIENT_ID)
    ignore_ssl = entry.data.get(CONF_IGNORE_SSL, False)  # 默认不忽略 SSL

    # 打印调试日志
    #_LOGGER.debug(f"Identifier: {identifier}, Credential: {credential}, Client ID: {client_id}, Ignore SSL: {ignore_ssl}")
 
    if not all([identifier, credential, client_id]):
        _LOGGER.error("Identifier, Credential 或 Client ID 缺失，请检查配置")
        return False

    # 创建 aiohttp 会话，配置 SSL 忽略选项
    connector = None
    if ignore_ssl:
        _LOGGER.warning("SSL 验证被忽略，此操作可能不安全")
        connector = TCPConnector(ssl=not ignore_ssl)
    session = ClientSession(connector=connector)
    hass.data[DOMAIN]["session"] = session

    # 获取 token
    try:
        access_token = await get_access_token(identifier, credential, client_id, session)
        _LOGGER.info(f"Token 获取成功{access_token}")
        if not access_token:
            _LOGGER.error("无法获取 Token，初始化失败")
            return False
    except Exception as e:
        _LOGGER.error(f"获取 token 时发生错误: {e}")
        return False
    
    try:
         # 获取所有组信息
        groups = await get_ggid(hass, access_token, session)
        if not groups:
            _LOGGER.error("获取组信息失败")
            return False

        # 创建传感器组件
        component = EntityComponent[Entity](_LOGGER, DOMAIN, hass)
        
        # 存储组件到 hass.data
        hass.data[DOMAIN]["component"] = component

        # 在创建实体之前添加
        hass.data[DOMAIN][entry.entry_id] = {
            "entities": []
        }
    
        # 遍历处理每个组
        entities_to_add = []
        
        for group in groups:
            # 获取组内设备
            devices = await get_ddevices(hass, access_token, group["gid"], session)
            if not devices:
                _LOGGER.warning(f"组 {group['gid']} 内没有设备")
                continue

            # 处理组内设备
            for device_info in devices:
                if device_info["type"] == "LOCK":
                    # 创建设备对象
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
                    
                    # 为每个物理设备创建一组实体
                    device_entities = []
                    
                    device_entities.extend([
                        KiwiLockInfo(lock_device, group),
                        KiwiLockStatus(lock_device, latest_event)
                    ])
                    
                    #添加锁用户实体
                    if users:
                        _LOGGER.info(f"用户数据结构: {users[0]}")
                        user_count = 0
                        for user in users:
                            user_count += 1
                            try:
                                # 使用 get 方法安全地获取用户ID，提供默认值
                                user_id = user.get("number", "unknown")  # 改用 number 作为用户标识
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
             

                    # 将该设备的所有实体添加到总实体列表
                    entities_to_add.extend(device_entities)

        # 存储创建的实体
        hass.data[DOMAIN][entry.entry_id]["entities"] = entities_to_add

        # 注册平台
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        # 启动 WebSocket 连接
        hass.loop.create_task(start_websocket_connection(hass, access_token, session))
        
        _LOGGER.info(f"KiwiOT 集成已成功初始化，添加了 {len(entities_to_add)} 个实体")
        return True

    except Exception as e:
        _LOGGER.error(f"设置集成时发生错误: {e}")
        if session:
            await session.close()
        return False

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload KiwiOT integration."""
    # 关闭全局 ClientSession
    session = hass.data[DOMAIN].get("session")
    if (session):
        await session.close()
    hass.data.pop(DOMAIN, None)
    _LOGGER.info("KiwiOT 集成已卸载")
    return True
