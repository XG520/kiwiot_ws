import asyncio
import logging
from aiohttp import ClientSession, TCPConnector
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.entity import Entity
from .entity import *

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN, LOGGER_NAME, CONF_IDENTIFIER, CONF_CREDENTIAL, CONF_CLIENT_ID, CONF_IGNORE_SSL
from .websocket import start_websocket_connection
from .token_manager import get_access_token
from .userinfo import get_ggid, get_ddevices, get_lock_userinfo, get_lock_info

_LOGGER = logging.getLogger(f"{LOGGER_NAME}_{__name__}")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up KiwiOT integration from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    identifier = entry.data.get(CONF_IDENTIFIER)
    credential = entry.data.get(CONF_CREDENTIAL)
    client_id = entry.data.get(CONF_CLIENT_ID)
    ignore_ssl = entry.data.get(CONF_IGNORE_SSL, False)  # 默认不忽略 SSL

    # 打印调试日志
    _LOGGER.debug(f"Identifier: {identifier}, Credential: {credential}, Client ID: {client_id}, Ignore SSL: {ignore_ssl}")
    # 配置需要显示日志的包
    # 验证配置是否完整
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

        # 遍历处理每个组
        entities_to_add = []
        
        for group in groups:
            # 创建组实体
            group_entity = KiwiDeviceGroup(hass, group)
            entities_to_add.append(group_entity)

            # 获取组内设备
            devices = await get_ddevices(hass, access_token, group["gid"], session)
            if not devices:
                _LOGGER.warning(f"组 {group['gid']} 内没有设备")
                continue

            # 处理组内设备
            for device in devices:
                if device["type"] == "LOCK":
                    # 创建锁设备实体
                    lock_device = KiwiLockDevice(hass, device, group["gid"])
                    entities_to_add.append(lock_device)

                    # 获取并创建锁用户实体
                    users = await get_lock_userinfo(hass, access_token, device["did"], session)
                    if users:
                        user_entities = [
                            KiwiLockUser(hass, lock_device, user) 
                            for user in users
                        ]
                        entities_to_add.extend(user_entities)

                    # 获取并创建锁事件实体
                    events = await get_lock_info(hass, access_token, device["did"], session)
                    if events:
                        event_entities = [
                            KiwiLockEvent(hass, lock_device, event)
                            for event in events
                        ]
                        entities_to_add.extend(event_entities)

        # 一次性添加所有实体
        await component.async_add_entities(entities_to_add)

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
    if session:
        await session.close()
    hass.data.pop(DOMAIN, None)
    _LOGGER.info("KiwiOT 集成已卸载")
    return True
