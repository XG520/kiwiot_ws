﻿import aiohttp
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

async def update_lock_user_alias(hass, token, did, user_type, user_id, new_alias, session):
    """更新锁用户别名"""
    if len(new_alias) > 16:
        _LOGGER.error("用户别名长度不能超过16个字符")
        return False
        
    _LOGGER.debug(f"更新用户别名: {new_alias}")
    url = f"{BASE_URL}/api/locks/{did}/users/{user_type}/{user_id}/alias"
    
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        
        async with session.put(url, json=new_alias, headers=headers) as response:
            if response.status == 204:
                _LOGGER.info(f"成功更新用户别名为: {new_alias}")
                return True
            else:
                try:
                    error_data = await response.json()
                    _LOGGER.error(f"更新用户别名失败: 状态码 {response.status}, 错误信息: {error_data}")
                except:
                    _LOGGER.error(f"更新用户别名失败: 状态码 {response.status}")
                return False
                
    except aiohttp.ClientError as e:
        _LOGGER.error(f"更新用户别名时发生错误: {e}")
        return False
    except Exception as e:
        _LOGGER.error(f"发生意外错误: {e}")
        return False