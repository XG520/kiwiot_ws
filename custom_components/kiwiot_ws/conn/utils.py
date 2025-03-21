﻿import logging
import aiohttp
import aiofiles
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
import hashlib
from PIL import Image
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
import os

_LOGGER = logging.getLogger(__name__)

async def get_latest_event(events: List[Dict]) -> Optional[Dict]:
    """获取最新的事件."""
    try:
        if not events:
            return None
            
        sorted_events = sorted(
            events,
            key=lambda x: datetime.fromisoformat(x.get("created_at", "").replace('Z', '+00:00')),
            reverse=True
        )
        
        latest_event = sorted_events[0]
        _LOGGER.debug(f"最新事件: {latest_event}")
        
        return latest_event
        
    except Exception as e:
        _LOGGER.error(f"获取最新事件失败: {e}")
        return None

async def get_latest_event_with_data(events: List[Dict]) -> Optional[Dict]:
    """获取最近一次包含data的事件."""
    try:
        if not events:
            return None
            
        sorted_events = sorted(
            events,
            key=lambda x: datetime.fromisoformat(x.get("created_at", "").replace('Z', '+00:00')),
            reverse=True
        )
        
        for event in sorted_events:
            if (event.get("data") and 
                isinstance(event["data"], dict) and 
                len(event["data"]) > 0):
                _LOGGER.debug(f"找到最近的data事件: {event}")
                return event
                
        return None
        
    except Exception as e:
        _LOGGER.error(f"获取最近data事件失败: {e}")
        return None
    
async def get_history_events(events: List[Dict]) -> List[Dict]:
    """获取除最新事件外的所有事件."""
    try:
        if not events or len(events) <= 1:
            return []
            
        sorted_events = sorted(
            events,
            key=lambda x: datetime.fromisoformat(x.get("created_at", "").replace('Z', '+00:00')),
            reverse=True
        )
        
        history_events = sorted_events[1:]
        _LOGGER.debug(f"历史事件数量: {len(history_events)}")
        
        return history_events
        
    except Exception as e:
        _LOGGER.error(f"获取历史事件失败: {e}")
        return []
    
    
async def convert_wsevent_format(event_data: dict) -> dict:
    USER_TYPE_MAP = {
        0: "门内", 
        1: "FINGERPRINT",
        2: "PASSWORD",
        3: "CARD",
        5: "远程",
        6: "FACE",
        7: "掌纹",
        9: "临时密码"
    } 
    
    data = event_data.get("data", {})
    if not data:
        formatted_data = {}
    else:
        formatted_data = {
            "image": {
                "uri": data.get("image_uri")
            },
            "lock_user": {
                "id": data.get("lock_user", {}).get("id"),
                "type": USER_TYPE_MAP.get(
                    data.get("lock_user", {}).get("type"),
                    "UNKNOWN"
                )
            }
        }

    converted_data = {
        "device_id": event_data.get("did"),
        "name": event_data.get("name"),
        "level": event_data.get("level"),
        "created_at": event_data.get("created_at"),
        "data": formatted_data
    }

    return converted_data

async def convert_media_event_format(event_data: dict) -> dict:
    try:
        formatted_data = {
            "image": {
                "uri": event_data.get("data", {}).get("image_uri")
            },
            "lock_user": {
                "id": "UNKNOWN",
                "type": "UNKNOWN"
            }
        }
        
        if "data" in event_data and "media" in event_data["data"]:
            formatted_data["media"] = event_data["data"]["media"]
            
        if "data" in event_data and "stream_id" in event_data["data"]:
            formatted_data["stream_id"] = event_data["data"]["stream_id"]

        converted_data = {
            "device_id": event_data.get("did"),
            "name": event_data.get("name"),
            "level": event_data.get("level"),
            "created_at": event_data.get("created_at"),
            "data": formatted_data
        }
        
        return converted_data
        
    except Exception as e:
        _LOGGER.error(f"转换媒体事件数据失败: {e}")
        return None

class ImageCache:
    def __init__(self, hass, cache_dir: Path):
        self.hass = hass
        self._cache_dir = cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._current_image_url = None
        self._current_cache_file = None
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._max_cache_files = 10
        self._downloading = False

    async def _cleanup_old_cache(self):
        """清理旧的缓存文件，只保留最近的10个文件"""
        try:
            cache_files = sorted(
                [f for f in self._cache_dir.glob("*.jpg")],
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            
            if len(cache_files) > self._max_cache_files:
                for old_file in cache_files[self._max_cache_files:]:
                    try:
                        old_file.unlink()
                        _LOGGER.debug(f"删除旧缓存文件: {old_file}")
                    except Exception as e:
                        _LOGGER.error(f"删除缓存文件失败: {e}")

        except Exception as e:
            _LOGGER.error(f"清理缓存文件失败: {e}")

    async def _save_image_to_file(self, image: Image.Image, cache_file: Path) -> None:
        def _save():
            image.save(cache_file, format="JPEG")
        
        await self.hass.async_add_executor_job(_save)
        await self._cleanup_old_cache()  
    def _get_cache_filename(self, url: str) -> str:
        _LOGGER.info( "保存文件：" + hashlib.md5(url.encode()).hexdigest() + ".jpg")
        return hashlib.md5(url.encode()).hexdigest() + ".jpg"

    async def _read_file_bytes(self, cache_file: Path) -> bytes:
        async with aiofiles.open(cache_file, mode='rb') as file:
            return await file.read()

    async def clear_cache(self) -> None:
        if self._current_cache_file and os.path.exists(self._current_cache_file):
            try:
                os.remove(self._current_cache_file)
                self._current_image_url = None
                self._current_cache_file = None
            except Exception as e:
                _LOGGER.error(f"清除缓存文件失败: {e}")

    async def get_image(self, url: str) -> Optional[bytes]:
        """获取图片，支持缓存和预下载"""
        if not url:
            return None

        cache_file = self._cache_dir / self._get_cache_filename(url)
        
        if self._current_image_url == url and cache_file.exists():
            try:
                _LOGGER.debug(f"使用缓存图片: {cache_file}")
                return await self._read_file_bytes(cache_file)
            except Exception as e:
                _LOGGER.error(f"读取缓存图片失败: {e}")

        while self._downloading:
            await asyncio.sleep(0.1)

        try:
            self._downloading = True
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        _LOGGER.error(f"下载图片失败: HTTP {response.status}")
                        return None

                    image_data = await response.read()
                    
                    def process_image():
                        image = Image.open(BytesIO(image_data))
                        return image.rotate(-90, expand=True)
                    
                    rotated_image = await self.hass.async_add_executor_job(process_image)
                    await self._save_image_to_file(rotated_image, cache_file)
                    
                    self._current_image_url = url
                    self._current_cache_file = cache_file
                    
                    _LOGGER.debug(f"图片已下载并缓存: {url}")
                    return await self._read_file_bytes(cache_file)

        except Exception as e:
            _LOGGER.error(f"处理图片失败: {e}")
            return None
        finally:
            self._downloading = False
