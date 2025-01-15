import logging
from datetime import datetime
from typing import List, Dict, Optional

_LOGGER = logging.getLogger(__name__)

async def get_latest_event(events: List[Dict]) -> Optional[Dict]:
    """获取最新的事件."""
    try:
        if not events:
            return None
            
        # 按创建时间排序事件
        sorted_events = sorted(
            events,
            key=lambda x: datetime.fromisoformat(x.get("created_at", "").replace('Z', '+00:00')),
            reverse=True
        )
        
        # 获取最新事件
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
            
        # 按创建时间排序事件
        sorted_events = sorted(
            events,
            key=lambda x: datetime.fromisoformat(x.get("created_at", "").replace('Z', '+00:00')),
            reverse=True
        )
        
        # 查找第一个包含data且不为空的事件
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
            
        # 按创建时间排序事件
        sorted_events = sorted(
            events,
            key=lambda x: datetime.fromisoformat(x.get("created_at", "").replace('Z', '+00:00')),
            reverse=True
        )
        
        # 返回除第一个事件外的所有事件
        history_events = sorted_events[1:]
        _LOGGER.debug(f"历史事件数量: {len(history_events)}")
        
        return history_events
        
    except Exception as e:
        _LOGGER.error(f"获取历史事件失败: {e}")
        return []
    
async def get_stream_id(data: dict) -> str | None:
    try:
        if data.get("name") == "HUMAN_WANDERING":
            return data.get("data", {}).get("stream_id")
        return None
    except Exception:
        return None
    
async def convert_wsevent_format(event_data: dict) -> dict:
    USER_TYPE_MAP = {
        0: "门内", 
        1: "FINGERPRINT",
        2: "PASSWORD",
        5: "微信",
        6: "FACE"
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
