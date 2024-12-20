import asyncio
import logging
from aiohttp import ClientSession

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN, LOGGER_NAME, CONF_IDENTIFIER, CONF_CREDENTIAL, CONF_CLIENT_ID
from .websocket import start_websocket_connection
from .token_manager import get_access_token
from .entities import UserEntity, GroupEntity, TextEntity

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
