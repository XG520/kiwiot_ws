import logging
from aiohttp import ClientSession
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import async_get_platforms
from .const import DOMAIN, LOGGER_NAME, CONF_IDENTIFIER, CONF_CREDENTIAL, CONF_CLIENT_ID, BASE_URL
from .websocket import start_websocket_connection
from .token_manager import get_access_token
from .entities import UserEntity, GroupEntity
from .lock import LockEntity

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

    # 初始化全局 ClientSession
    session = ClientSession()
    hass.data[DOMAIN]["session"] = session

    # 获取 token
    _LOGGER.info("获取 token")
    try:
        access_token = await get_access_token(identifier, credential, client_id, session)
        _LOGGER.info(f"Token 获取成功：{access_token}")
        if not access_token:
            _LOGGER.error("无法获取 Token，初始化失败")
            return False
        hass.data[DOMAIN]["token"] = access_token
    except Exception as e:
        _LOGGER.error(f"获取 token 时发生错误: {e}")
        await session.close()
        return False

    # 注册实体
    _LOGGER.info("注册实体")
    try:
        platform = next(
            platform for platform in async_get_platforms(hass, DOMAIN) if platform.domain == "sensor"
        )

        user_entity = UserEntity(hass, access_token)
        group_entity = GroupEntity(hass, access_token, session)

        # 添加家庭实体
       # await platform.async_add_entities([user_entity, group_entity])

        # 获取家庭列表
        url = f"{BASE_URL}/groups?access_token={access_token}"
        async with session.get(url) as response:
            _LOGGER.info(f"获取家庭信息: {response.status}")
            if response.status != 200:
                _LOGGER.error(f"获取家庭信息失败: {response.status}")
                return False
            groups = await response.json()

        # 获取每个家庭的设备并注册
        for group in groups:
            gid = group["gid"]
            group_name = group["name"]
            devices_url = f"{BASE_URL}/groups/{gid}/devices?access_token={access_token}"
            async with session.get(devices_url) as response:
                if response.status != 200:
                    _LOGGER.error(f"获取设备信息失败: {response.status} (家庭: {group_name})")
                    continue
                devices = await response.json()

                # 注册设备
                for device in devices:
                    if device["type"] == "LOCK":
                        lock_entity = LockEntity(hass, gid, group_name, device)
                        await platform.async_add_entities([lock_entity])

    except Exception as e:
        _LOGGER.error(f"注册实体失败: {e}")
        await session.close()
        return False

    # 启动 WebSocket 连接
    _LOGGER.info("启动 WebSocket 连接")
    try:
        await start_websocket_connection(hass, access_token, session)
    except Exception as e:
        _LOGGER.error(f"WebSocket 连接失败: {e}")
        await session.close()
        return False

    _LOGGER.info("KiwiOT 集成已加载")
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
