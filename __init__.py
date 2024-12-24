import asyncio
import logging
from aiohttp import ClientSession, TCPConnector
from homeassistant.const import Platform
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, LOGGER_NAME, CONF_IDENTIFIER, CONF_CREDENTIAL, CONF_CLIENT_ID, CONF_IGNORE_SSL
from .websocket import start_websocket_connection
from .token_manager import get_access_token
from .device_manager import initialize_devices_and_groups

_LOGGER = logging.getLogger(f"{LOGGER_NAME}_{__name__}")

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up KiwiOT integration from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    identifier = entry.data.get(CONF_IDENTIFIER)
    credential = entry.data.get(CONF_CREDENTIAL)
    client_id = entry.data.get(CONF_CLIENT_ID)
    ignore_ssl = entry.data.get(CONF_IGNORE_SSL, False)  
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
        _LOGGER.info(f"Token 获取成功: {access_token}")
        if not access_token:
            _LOGGER.error("无法获取 Token，初始化失败")
            return False
    except Exception as e:
        _LOGGER.error(f"获取 token 时发生错误: {e}")
        return False

    # 初始化设备和组信息
    try:
        entities_to_add = []

        def add_entities_callback(new_entities):
            entities_to_add.extend(new_entities)

        await initialize_devices_and_groups(hass, access_token, session, add_entities_callback)
        if not entities_to_add:
            return False

        # 存储创建的实体
        hass.data[DOMAIN][entry.entry_id] = {
            "entities": entities_to_add
        }

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
    session = hass.data[DOMAIN].get("session")
    if session:
        await session.close()
    hass.data.pop(DOMAIN, None)
    _LOGGER.info("KiwiOT 集成已卸载")
    return True