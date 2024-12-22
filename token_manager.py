import aiohttp
import logging
from .const import AUTH_URL, LOGGER_NAME

_LOGGER = logging.getLogger(f"{LOGGER_NAME}_{__name__}")

# async def get_access_token(identifier, credential, client_id):
#     """使用 aiohttp 异步获取新的 access_token。"""
#     headers = {
#         "X-Kiwik-Client-Id": client_id
#     }
#     data = {
#         "identifier": identifier,
#         "credential": credential,
#         "auth_type": "password"
#     }

#     try:
#         async with aiohttp.ClientSession() as session:
#             async with session.post(AUTH_URL, headers=headers, json=data) as response:
#                 if response.status != 201:
#                     raise ValueError(f"Unexpected status code: {response.status}")
#                 response_data = await response.json()
#                 token = response_data.get("access_token")
#                 if not token:
#                     raise ValueError("未从响应中获取到 access_token")
#                 return token
#     except Exception as e:
#         _LOGGER.error(f"获取 token 时发生错误: {e}")
#         return None
async def get_access_token(identifier, credential, client_id, session):
    """使用传入的 session 获取新的 access_token。"""
    headers = {
        "X-Kiwik-Client-Id": client_id
    }
    data = {
        "identifier": identifier,
        "credential": credential,
        "auth_type": "password"
    }

    try:
        _LOGGER.debug(f"发送的请求数据: {data}")
        async with session.post(AUTH_URL, headers=headers, json=data) as response:
            _LOGGER.debug(f"响应状态码: {response.status}")
            response_data = await response.json()
            _LOGGER.debug(f"响应内容: {response_data}")

            if response.status != 201:
                raise ValueError(f"Unexpected status code: {response.status}")
            
            token = response_data.get("access_token")
            if not token:
                raise ValueError("未从响应中获取到 access_token")
            return token
    except Exception as e:
        _LOGGER.error(f"获取 token 时发生错误: {e} 请求数据{data}")
        return None

