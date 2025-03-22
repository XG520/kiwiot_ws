import aiohttp
import logging
import json
import time
import os
import aiofiles
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from asyncio import Lock
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from ..const import BASE_URL, LOGGER_NAME, CONF_IDENTIFIER, CONF_CREDENTIAL, CONF_CLIENT_ID

_LOGGER = logging.getLogger(f"{LOGGER_NAME}_{__name__}")

class TokenManager:
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """初始化 TokenManager"""
        self.hass = hass
        self._entry = entry
        self._identifier = entry.data.get(CONF_IDENTIFIER)
        self._credential = entry.data.get(CONF_CREDENTIAL)
        self._client_id = entry.data.get(CONF_CLIENT_ID)
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_type: str = "bearer"
        self._expires_at: Optional[float] = None
        self._lock = Lock()
        
        storage_dir = Path(hass.config.path("kiwiot_config"))
        storage_dir.mkdir(parents=True, exist_ok=True)
        safe_identifier = self._identifier.replace("+", "_").replace("/", "_")
        self._storage_file = storage_dir / f"kiwiot_tokens_{safe_identifier}.json"

    async def _load_stored_tokens(self) -> None:
        """从存储文件异步加载令牌"""
        try:
            if self._storage_file.exists():
                async with aiofiles.open(self._storage_file, "r") as f:
                    data = json.loads(await f.read())
                    if self._identifier == data.get("identifier"):
                        self._access_token = data.get("access_token")
                        self._refresh_token = data.get("refresh_token")
                        self._expires_at = data.get("expires_at")
                        self._token_type = data.get("token_type", "bearer")
                        _LOGGER.info(f"已从{self._storage_file}存储加载Token信息:{data}")
        except Exception as e:
            _LOGGER.error(f"加载Token存储失败: {e}")

    async def _save_tokens(self) -> None:
        """保存令牌到存储文件"""
        try:
            self._storage_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "identifier": self._identifier,
                "access_token": self._access_token,
                "refresh_token": self._refresh_token,
                "expires_at": self._expires_at,
                "token_type": self._token_type,
                "updated_at": datetime.now().isoformat()
            }
            
            async with aiofiles.open(self._storage_file, "w") as f:
                await f.write(json.dumps(data, indent=2))
            _LOGGER.debug(f"Token信息已保存到: {self._storage_file}")
            
        except Exception as e:
            _LOGGER.error(f"保存Token失败: {e}")
            raise

    def _is_token_expired(self) -> bool:
        """检查token是否过期"""
        if not self._expires_at:
            return True
        return time.time() > (self._expires_at - 300)

    async def get_token(self, session) -> Optional[str]:
        """获取有效的access token"""
        async with self._lock:
            try:
                if not self._storage_file.exists(): 
                    _LOGGER.debug(f"Token存储文件不存在，将获取新token: {self._storage_file}")
                    await self._fetch_new_token(session)
                    return self._access_token  
                
                if self._access_token is None:
                    if self._storage_file.exists():
                        await self._load_stored_tokens()
                    else:
                        _LOGGER.debug(f"Token存储文件不存在，将获取新token: {self._storage_file}")
                        try:
                            await self._fetch_new_token(session)
                            if self._access_token:
                                return self._access_token
                            raise ValueError("获取新token失败")
                        except Exception as e:
                            _LOGGER.error(f"初始获取token失败: {e}")
                            return None
                      
                if not self._is_token_expired():
                    if await self.is_token_valid(session):
                        _LOGGER.info(f"使用缓存的token, 过期时间: {datetime.fromtimestamp(self._expires_at)}")
                        return self._access_token
                else:
                    _LOGGER.warning("Token已过期")
                    await self._fetch_new_token(session)
                    _LOGGER.info(f"{self._access_token}使用新token, 过期时间: {datetime.fromtimestamp(self._expires_at)}")
                return self._access_token

                # if self._refresh_token:
                #     try:
                #         _LOGGER.debug("尝试使用refresh_token刷新")
                #         await self._refresh_access_token(session)
                #         return self._access_token
                #     except Exception as e:
                #         _LOGGER.warning(f"刷新token失败: {e}")

                # _LOGGER.info("获取新token")


            except Exception as e:
                _LOGGER.error(f"获取token失败: {e}")
                return None

    async def _refresh_access_token(self, session) -> None:
        """使用refresh_token刷新access_token"""
        headers = {"X-Kiwik-Client-Id": self._client_id}
        data = {
            "client_id": self._client_id,
            "grant_type": "refresh_token",
            "refresh_token": self._refresh_token
        }

        try:
            async with session.post(
                f"{BASE_URL}/restapi/oauth/token", 
                headers=headers, 
                json=data,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                response_data = await response.json()
                
                if response.status == 401:
                    _LOGGER.info("Refresh token已失效，需要重新获取token")
                    raise ValueError("refresh_token_expired")
                    
                if response.status != 200:
                    raise ValueError(f"刷新token失败: {response_data}")
                    
                if not response_data.get("success", False):
                    raise ValueError(f"刷新token请求失败: {response_data.get('message')}")
                    
                token_data = response_data.get("data", {})
                await self._update_tokens(token_data)
                _LOGGER.info("Token刷新成功")
        except Exception as e:
            _LOGGER.error(f"刷新token时发生错误: {e}")
            raise

    async def _fetch_new_token(self, session) -> None:
        """获取新的token"""
        headers = {"X-Kiwik-Client-Id": self._client_id}
        data = {
            "identifier": self._identifier,
            "credential": self._credential,
            "auth_type": "password"
        }

        try:
            async with session.post(
                f"{BASE_URL}/restapi/auth/tokens", 
                headers=headers, 
                json=data,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                response_data = await response.json()
                
                if response.status == 201:
                    await self._update_tokens(response_data)
                    #_LOGGER.info("获取新token成功{}". format(response_data))  
                else:
                    raise ValueError(f"获取token请求失败: {response_data.get('message')}")
                    

        except Exception as e:
            _LOGGER.error(f"获取新token时发生错误: {e}")
            raise

    async def _update_tokens(self, token_data: Dict[str, Any]) -> None:
        """更新token信息"""
        if "access_token" not in token_data:
            raise ValueError("token数据无效")
            
        self._access_token = token_data["access_token"]
        self._refresh_token = token_data.get("refresh_token")
        self._token_type = token_data.get("token_type", "secure")
        expires_in = int(token_data.get("expires_in", 3600))
        self._expires_at = time.time() + expires_in - 300

        await self._save_tokens()

    async def is_token_valid(self, session) -> bool:
        """验证当前token是否有效"""
        if not self._access_token or self._is_token_expired():
            return False
        # _LOGGER.info(f"验证Token有效性: {self._access_token}, {self._token_type}")
        try:
            test_url = f"{BASE_URL}/restapi/groups"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"{self._token_type} {self._access_token}"
            }
            # _LOGGER.info(f"hearders: {headers}")
            async with session.get(
                test_url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=3)
            ) as response:
                if response.status == 401:
                    _LOGGER.info("验证：Token已失效")
                    return False
                return response.status == 200
                
        except Exception as e:
            _LOGGER.debug(f"Token验证失败: {e}")
            return False

    async def invalidate_token(self) -> None:
        """使当前token失效"""
        self._access_token = None
        self._refresh_token = None
        self._expires_at = None
        await self._save_tokens()