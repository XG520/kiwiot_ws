﻿import logging
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