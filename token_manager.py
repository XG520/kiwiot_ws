import aiohttp
import logging
import json
from .const import AUTH_URL, LOGGER_NAME
from asyncio import Lock

_LOGGER = logging.getLogger(f"{LOGGER_NAME}_{__name__}")

class TokenManager:
    def __init__(self, hass, identifier, credential, client_id):
        self.hass = hass
        self._identifier = identifier
        self._credential = credential
        self._client_id = client_id
        self._access_token = None
        self._lock = Lock()
        
    async def get_token(self, session):
        """获取当前token,如果无效则刷新"""
        async with self._lock:
            return await self._get_or_refresh_token(session)
            
    async def _get_or_refresh_token(self, session):
        """获取或刷新token"""
        if not self._access_token:
            self._access_token = await self._fetch_new_token(session)
        return self._access_token
        
    async def validate_and_refresh(self, session, response_data):
        """验证响应并在需要时刷新token"""
        if isinstance(response_data, str):
            try:
                response_data = json.loads(response_data)
            except json.JSONDecodeError:
                return self._access_token
                
        if isinstance(response_data, dict) and response_data.get("error") == "invalid_token":
            _LOGGER.info("Token已失效,正在刷新...")
            async with self._lock:
                self._access_token = await self._fetch_new_token(session)
                return self._access_token
        return self._access_token

    async def _fetch_new_token(self, session):
        """获取新的access_token"""
        headers = {
            "X-Kiwik-Client-Id": self._client_id
        }
        data = {
            "identifier": self._identifier,
            "credential": self._credential,
            "auth_type": "password"
        }

        try:
            async with session.post(AUTH_URL, headers=headers, json=data) as response:
                response_data = await response.json()
                
                if response.status != 201:
                    raise ValueError(f"获取token失败,状态码: {response.status}")
                
                token = response_data.get("access_token")
                if not token:
                    raise ValueError("响应中没有access_token")
                    
                _LOGGER.info("成功获取新token")
                return token
                
        except Exception as e:
            _LOGGER.error(f"获取token失败: {e}")
            raise


async def get_access_token(identifier, credential, client_id, session):
    try:
        headers = {"X-Kiwik-Client-Id": client_id}
        data = {
            "identifier": identifier,
            "credential": credential,
            "auth_type": "password"
        }
        
        async with session.post(AUTH_URL, headers=headers, json=data) as response:
            response_data = await response.json()
            if response.status != 201:
                raise ValueError(f"状态码错误: {response.status}")
            
            token = response_data.get("access_token")
            if not token:
                raise ValueError("未获取到access_token")
            return token
            
    except Exception as e:
        _LOGGER.error(f"获取token失败: {e}")
        return None

