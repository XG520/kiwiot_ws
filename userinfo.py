import aiohttp
import logging
from .const import BASE_URL, LOGGER_NAME

_LOGGER = logging.getLogger(f"{LOGGER_NAME}_{__name__}")

async def get_ggid(hass, token, session):
    url = f"{BASE_URL}/restapi/groups?access_token={token}"
    try:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data
            else:
                _LOGGER.error(f"获取组信息失败: 状态码 {response.status}")
                response.raise_for_status()
    except aiohttp.ClientError as e:
        _LOGGER.error(f"在获取组信息时发生错误: {e}")
        return None
    except Exception as e:
        _LOGGER.error(f"发生意外错误: {e}")
        return None
    
async def get_ddevices(hass, token, gid, session):
    url = f"{BASE_URL}/restapi/groups/{gid}/devices?access_token={token}"
    try:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data
            else:
                _LOGGER.error(f"获取设备信息失败: 状态码 {response.status}")
                response.raise_for_status()
    except aiohttp.ClientError as e:
        _LOGGER.error(f"在获取设备息时发生错误: {e}")
        return None
    except Exception as e:
        _LOGGER.error(f"发生意外错误: {e}")
        return None
    
async def get_lock_userinfo(hass, token, did, session):
    url = f"{BASE_URL}/api/locks/{did}/users?access_token={token}"
    try:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data
            else:
                _LOGGER.error(f"获取锁用户信息失败: 状态码 {response.status}")
                response.raise_for_status()
    except aiohttp.ClientError as e:
        _LOGGER.error(f"在获取锁用户信息时发生错误: {e}")
        return None
    except Exception as e:
        _LOGGER.error(f"发生意外错误: {e}")
        return None
    
async def get_lock_info(hass, token, did, session):
    url = f"{BASE_URL}/api/devices/{did}/events?page=1&per_page=15&access_token={token}"
    try:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data
            else:
                _LOGGER.error(f"获取锁事件失败: 状态码 {response.status}")
                response.raise_for_status()
    except aiohttp.ClientError as e:
        _LOGGER.error(f"在获取锁事件时发生错误: {e}")
        return None
    except Exception as e:
        _LOGGER.error(f"发生意外错误: {e}")
        return None