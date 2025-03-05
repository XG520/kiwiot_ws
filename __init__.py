import asyncio
import logging
from aiohttp import ClientSession, TCPConnector
from homeassistant.const import Platform
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, LOGGER_NAME, CONF_IDENTIFIER, CONF_CREDENTIAL, CONF_CLIENT_ID, CONF_IGNORE_SSL
from .conn.websocket import start_websocket_connection
from .conn.token_manager import get_access_token
from .device_manager import initialize_devices_and_groups

_LOGGER = logging.getLogger(f"{LOGGER_NAME}_{__name__}")

PLATFORMS = [Platform.SENSOR, Platform.CAMERA, Platform.TEXT, Platform.BUTTON]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    identifier = entry.data.get(CONF_IDENTIFIER)
    credential = entry.data.get(CONF_CREDENTIAL)
    client_id = entry.data.get(CONF_CLIENT_ID)
    ignore_ssl = entry.data.get(CONF_IGNORE_SSL, False)
    
    # 创建TokenManager实例
    from .conn.token_manager import TokenManager
    token_manager = TokenManager(hass, identifier, credential, client_id)
    
    # 创建session
    connector = None
    if ignore_ssl:
        connector = TCPConnector(ssl=False)
    session = ClientSession(connector=connector)
    
    try:
        # 获取初始token
        access_token = await token_manager.get_token(session)
        if not access_token:
            return False
            
        # 存储token_manager和session
        hass.data[DOMAIN].update({
            "token_manager": token_manager,
            "session": session,
            "access_token": access_token
        })

        # 初始化设备和组信息
        try:
            entities_to_add = []
            entities_by_device = {}

            def add_entities_callback(new_entities):
                """按设备ID组织实体"""
                nonlocal entities_by_device
                for entity in new_entities:
                    if hasattr(entity, '_device'):
                        device_id = entity._device.device_id
                        if device_id not in entities_by_device:
                            entities_by_device[device_id] = []
                        entities_by_device[device_id].append(entity)
                entities_to_add.extend(new_entities)

            await initialize_devices_and_groups(hass, access_token, session, add_entities_callback)
            if not entities_to_add:
                return False

            # 存储创建的实体，按设备ID组织
            hass.data[DOMAIN].update({
                "session": session,
                "access_token": access_token,
                "devices": entities_by_device,
                entry.entry_id: {
                    "entities": entities_to_add
                }
            })

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

    except Exception as e:
        _LOGGER.error(f"获取 token 时发生错误: {e}")
        return False

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # 首先卸载所有平台
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        # 关闭 session
        session = hass.data[DOMAIN].get("session")
        if session:
            await session.close()
        
        # 清理该条目的数据
        if entry.entry_id in hass.data[DOMAIN]:
            hass.data[DOMAIN].pop(entry.entry_id)
        
        # 如果没有其他条目使用这个域，则完全删除域数据
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)
            
        _LOGGER.info("KiwiOT 集成已成功卸载")
    
    return unload_ok