import aiohttp
import logging
from .const import BASE_URL, LOGGER_NAME

_LOGGER = logging.getLogger(f"{LOGGER_NAME}_{__name__}")

async def _make_request(hass, session, url, error_prefix="获取信息"):
    try:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            else:
                _LOGGER.error(f"{error_prefix}失败: 状态码 {response.status}")
                response.raise_for_status()
    except aiohttp.ClientError as e:
        _LOGGER.error(f"在{error_prefix}时发生错误: {e}")
        return None
    except Exception as e:
        _LOGGER.error(f"发生意外错误: {e}")
        return None

async def get_ggid(hass, token, session):
    url = f"{BASE_URL}/restapi/groups?access_token={token}"
    return await _make_request(hass, session, url, "获取组信息")

async def get_ddevices(hass, token, gid, session):
    url = f"{BASE_URL}/restapi/groups/{gid}/devices?access_token={token}"
    return await _make_request(hass, session, url, "获取设备信息")

async def get_device_info(hass, token, did, session):
    url = f"{BASE_URL}/api/devices/{did}?access_token={token}"
    return await _make_request(hass, session, url, "获取设备信息")

async def get_llock_userinfo(hass, token, did, session):
    url = f"{BASE_URL}/api/locks/{did}/users?access_token={token}"
    return await _make_request(hass, session, url, "获取锁用户信息")

async def get_llock_info(hass, token, did, session):
    url = f"{BASE_URL}/api/devices/{did}/events?page=1&per_page=15&access_token={token}"
    return await _make_request(hass, session, url, "获取锁信息")

async def get_llock_video(hass, token, did, session, stream_id):
    url = f"{BASE_URL}/api/devices/{did}/streams/{stream_id}?page=1&per_page=15&access_token={token}"
    return await _make_request(hass, session, url, "获取锁信息")