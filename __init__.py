import asyncio
import logging
from aiohttp import ClientSession
from homeassistant.helpers.entity_component import EntityComponent
from .entity import GroupEntity, DeviceEntity

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN, LOGGER_NAME, CONF_IDENTIFIER, CONF_CREDENTIAL, CONF_CLIENT_ID
from .websocket import start_websocket_connection
from .token_manager import get_access_token
from .userinfo import get_ggid, get_ddevices

_LOGGER = logging.getLogger(LOGGER_NAME)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up KiwiOT integration from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    identifier = entry.data.get(CONF_IDENTIFIER)
    credential = entry.data.get(CONF_CREDENTIAL)
    client_id = entry.data.get(CONF_CLIENT_ID)

    # 打印调试日志
    _LOGGER.debug(f"Identifier: {identifier}, Credential: {credential}, Client ID: {client_id}")

    # 验证配置是否完整
    if not all([identifier, credential, client_id]):
        _LOGGER.error("Identifier, Credential 或 Client ID 缺失，请检查配置")
        return False

    # 获取全局 aiohttp 会话
    session = ClientSession()
    hass.data[DOMAIN]["session"] = session

    # 获取 token
    try:
        access_token = await get_access_token(identifier, credential, client_id, session)
        _LOGGER.info("Token 获取成功")
        if not access_token:
            _LOGGER.error("无法获取 Token，初始化失败")
            return False
    except Exception as e:
        _LOGGER.error(f"获取 token 时发生错误: {e}")
        return False

    # 启动 WebSocket 连接（异步任务，非阻塞）
    hass.loop.create_task(start_websocket_connection(hass, access_token, session))

    _LOGGER.info("开始获取用户信息")
    try:
        group_info = await get_ggid(hass, access_token, session)
        _LOGGER.info(f"用户信息获取成功，组数量: {group_info['count']}")
    except Exception as e:
        _LOGGER.error(f"获取用户信息时发生错误: {e}")
        return False

    # 创建实体组件
    component = EntityComponent(_LOGGER, DOMAIN, hass)

    # 创建组实体
    entities = []
    for group in group_info["groups"]:
        gid = group["gid"]
        name = group["name"]
        devices_info = await get_ddevices(hass, access_token, gid, session)
        device_count = len(devices_info)
        group_entity = GroupEntity(hass, name, gid, device_count)
        entities.append(group_entity)
        _LOGGER.info(f"设备信息: {devices_info}")

        # 如果组中没有设备，跳过设备实体的创建
        if device_count == 0:
            continue

        # 创建每个设备的实体并添加到实体列表
        for device in devices_info:
            device_name = device["name"]
            device_type = device["type"]
            device_entity = DeviceEntity(hass, device_name, gid, device_type)
            entities.append(device_entity)

    # 添加所有实体到 Home Assistant
    await component.async_add_entities(entities)

    _LOGGER.info("KiwiOT 集成已成功初始化")
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload KiwiOT integration."""
    # 关闭全局 ClientSession
    session = hass.data[DOMAIN].get("session")
    if session:
        await session.close()
    hass.data.pop(DOMAIN, None)
    _LOGGER.info("KiwiOT 集成已卸载")
    return True
