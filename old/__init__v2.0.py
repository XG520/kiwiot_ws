﻿import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN, LOGGER_NAME,CONF_IDENTIFIER, CONF_CREDENTIAL, CONF_CLIENT_ID
from .websocket import start_websocket_connection
from .token_manager import get_access_token
from .entities import UserEntity, GroupEntity, DeviceEntity

_LOGGER = logging.getLogger(LOGGER_NAME)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up KiwiOT integration from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    identifier = entry.data.get(CONF_IDENTIFIER)
    credential = entry.data.get(CONF_CREDENTIAL)
    client_id = entry.data.get(CONF_CLIENT_ID)

    # 打印调试日志，检查传入的参数
    _LOGGER.debug(f"Identifier: {identifier}, Credential: {credential}, Client ID: {client_id}")

    # 验证参数是否有效
    if not all([identifier, credential, client_id]):
        _LOGGER.error("Identifier, Credential 或 Client ID 缺失，请检查配置")
        return False

    # 获取 token
    try:
        access_token = await get_access_token(identifier, credential, client_id)
        _LOGGER.info(f"Token 获取成功：{access_token}")
        if not access_token:
            _LOGGER.error("无法获取 Token，初始化失败")
            return False
    except Exception as e:
        _LOGGER.error(f"获取 token 时发生错误: {e}")
        return False

    # 启动 WebSocket 连接
    try:
        await start_websocket_connection(hass, access_token)
    except Exception as e:
        _LOGGER.error(f"WebSocket 连接失败: {e}")
        return False

    # 注册实体
    try:
        user_entity = UserEntity(hass, entry, access_token)
        group_entity = GroupEntity(hass, entry, access_token)
        device_entity = DeviceEntity(hass, entry, access_token)

        hass.data[DOMAIN][entry.entry_id] = {
            "user_entity": user_entity,
            "group_entity": group_entity,
            "device_entity": device_entity,
        }

        await asyncio.gather(
            user_entity.async_add(),
            group_entity.async_add(),
            device_entity.async_add()
        )
    except Exception as e:
        _LOGGER.error(f"注册实体失败: {e}")
        return False

    _LOGGER.info("KiwiOT 集成已成功初始化")
    return True

