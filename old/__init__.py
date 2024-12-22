import asyncio
import logging
from aiohttp import ClientSession, TCPConnector
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.entity import Entity
from .entity import GroupEntity, DeviceEntity, LockUserEntity, LockEventEntity

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

    # 启动 WebSocket 连接（异步任务，非阻塞）
    hass.loop.create_task(start_websocket_connection(hass, access_token, session))

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
