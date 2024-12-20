import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from homeassistant.helpers import entity_platform

from .const import DOMAIN, LOGGER_NAME
from .websocket import start_websocket_connection, stop_websocket_connection
from .entities import *

_LOGGER = logging.getLogger(LOGGER_NAME)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up KiwiOT integration from YAML configuration (not used here)."""
    _LOGGER.info("KiwiOT integration setup using YAML is not supported.")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up KiwiOT integration from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}

    # 启动 WebSocket 连接
    try:
        websocket_task = hass.loop.create_task(start_websocket_connection(hass, entry.data))
        hass.data[DOMAIN][entry.entry_id]['websocket_task'] = websocket_task
        _LOGGER.info("WebSocket 连接任务已启动")
    except Exception as e:
        _LOGGER.error(f"初始化 WebSocket 连接失败: {e}")
        return False

    # 获取 access_token
    access_token = await start_websocket_connection(hass, entry.data)
    if not access_token:
        _LOGGER.error("获取 access_token 失败，无法注册实体")
        return False

    # 注册实体
    user_entity = UserEntity(hass, access_token)
    group_entity = GroupEntity(hass, access_token)
    device_entities = await group_entity.get_device_entities()

    # 将实体添加到 Home Assistant
    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        "update_data",
        {},
        "async_update",
    )
    async_add_entities = hass.helpers.entity_platform.async_add_entities
    async_add_entities([user_entity, group_entity] + device_entities)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    websocket_task = hass.data[DOMAIN][entry.entry_id].get('websocket_task')
    if websocket_task:
        await stop_websocket_connection(websocket_task)
        _LOGGER.info("WebSocket 连接已停止")
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True
