import aiohttp
import logging
from .const import BASE_URL, LOGGER_NAME

_LOGGER = logging.getLogger(LOGGER_NAME)

async def get_ggid(hass, token, session):
    url = f"{BASE_URL}/groups?access_token={token}"
    try:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                #_LOGGER.debug(f"组信息: {data}")
                result = {
                    "count": len(data),
                    "groups": [{"name": item["name"], "gid": item["gid"]} for item in data]
                }
                return result
            else:
                _LOGGER.error(f"获取用户信息失败: 状态码 {response.status}")
                response.raise_for_status()
    except aiohttp.ClientError as e:
        _LOGGER.error(f"在获取用户信息时发生错误: {e}")
        return None
    except Exception as e:
        _LOGGER.error(f"发生意外错误: {e}")
        return None
    
async def get_ddevices(hass, token, gid, session):
    url = f"{BASE_URL}/groups/{gid}/devices?access_token={token}"
    try:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                #_LOGGER.debug(f"设备信息: {data}")
#[{"did":"xxxxx","gid":"xxxxxx","type":"LOCK","name":"智能","pk":"1","verify":true,"created_at":"2022-06-05T14:28:32.256338Z"}]
                # result = {
                #     "count": len(data),
                #     "groups": [{"name": item["name"], "did": item["did"], "type": item["type"]} for item in data]
                # }
                return data
            else:
                _LOGGER.error(f"获取用户信息失败: 状态码 {response.status}")
                response.raise_for_status()
    except aiohttp.ClientError as e:
        _LOGGER.error(f"在获取用户信息时发生错误: {e}")
        return None
    except Exception as e:
        _LOGGER.error(f"发生意外错误: {e}")
        return None