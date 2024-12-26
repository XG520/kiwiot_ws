import logging
import aiohttp
import asyncio
import re
import random
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from .entity import KiwiLockStatus, KiwiLockCamera
from .const import LOGGER_NAME, WS_URL, DOMAIN
from .utils import convert_wsevent_format
from .userinfo import get_llock_video
from homeassistant.helpers.dispatcher import async_dispatcher_send

_LOGGER = logging.getLogger(f"{LOGGER_NAME}_{__name__}")


def generate_uuid():
    """生成符合特定格式的 UUID 字符串。"""
    def replace_x_or_y(match):
        char = match.group(0)
        if char == 'x':
            return hex(random.randint(0, 15))[2]
        elif char == 'y':
            return hex(random.randint(8, 11))[2]

    uuid_pattern = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'
    return re.sub(r'[xy]', replace_x_or_y, uuid_pattern)


async def start_websocket_connection(hass, access_token, session):
    """启动 WebSocket 连接并维护心跳和消息处理."""
    ws_url = f"{WS_URL}/?access_token={access_token}"
    retry_count = 0
    max_retries = 5
    retry_delay = 5
    
    while retry_count < max_retries:
        try:
            async with session.ws_connect(ws_url) as ws:
                _LOGGER.info(f"WebSocket 连接已建立 (重试次数: {retry_count})")
                
                tasks = [
                    asyncio.create_task(send_heartbeat(ws)),
                    asyncio.create_task(handle_websocket_messages(ws, hass))  
                ]
                
                # 等待任务完成或异常
                try:
                    done, pending = await asyncio.wait(
                        tasks, 
                        return_when=asyncio.FIRST_EXCEPTION
                    )
                    # 取消未完成的任务
                    for task in pending:
                        task.cancel()
                    # 检查异常    
                    for task in done:
                        if task.exception():
                            raise task.exception()
                except Exception as e:
                    _LOGGER.error(f"WebSocket 任务异常: {e}")
                    raise
                    
        except Exception as e:
            _LOGGER.error(f"WebSocket 连接错误: {e}")
            retry_count += 1
            
        if retry_count < max_retries:
            wait_time = retry_delay * (2 ** retry_count)
            await asyncio.sleep(wait_time)
        else:
            _LOGGER.error(f"WebSocket 连接重试次数达到上限 ({max_retries})")
            break

async def send_heartbeat(ws):
    """发送心跳消息."""
    interval = 30
    try:
        while True:
            if ws.closed:
                _LOGGER.warning("WebSocket 已关闭，停止发送心跳")
                break
                
            ping_message = {
                "header": {
                    "namespace": "Iot.Application",
                    "name": "Ping",
                    "messageId": generate_uuid(),
                    "payloadVersion": 1
                }
            }
            await ws.send_json(ping_message)
            _LOGGER.debug("心跳消息已发送")
            await asyncio.sleep(interval)
    except Exception as e:
        _LOGGER.error(f"心跳消息发送失败: {e}")
        raise


async def handle_websocket_messages(ws, hass):
    """处理 WebSocket 消息并更新实体状态"""
    try:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                # 解析消息
                data = json.loads(msg.data)
                
                # 检查是否是设备事件消息
                if (data.get("header", {}).get("namespace") == "Iot.Device" and 
                    data.get("header", {}).get("name") == "EventNotify"):
                    
                    payload = data.get("payload", {})
                    device_id = payload.get("did")
                    event_name = payload.get("name")
                    if event_name == "UNLOCKED" or event_name == "LOCKED":
                        payload = await convert_wsevent_format(payload)
                    else:
                        _LOGGER.debug(f"未知事件类型: {payload}")
                    # 调用更新实体状态的方法
                    await update_device_state(hass, device_id, payload)
                    
            elif msg.type == aiohttp.WSMsgType.ERROR:
                _LOGGER.error(f"WebSocket 错误: {msg.data}")
                break
            
    except Exception as e:
        _LOGGER.error(f"处理 WebSocket 消息时发生错误: {e}")
        raise

async def update_device_state(hass, device_id, event_data):
    """根据WebSocket消息更新设备实体状态"""
    try:
        # 获取与此设备关联的所有实体
        device_entities = [
            entity for entity in hass.data[DOMAIN].values()
            for entity_list in entity.values()
            if isinstance(entity_list, list)
            for entity in entity_list.get("entities", [])
            if hasattr(entity, "_device") and entity._device.device_id == device_id
        ]
        
        for entity in device_entities:
            if isinstance(entity, KiwiLockStatus):
                # 更新状态实体
                entity._event = event_data
                entity._event_time = datetime.fromisoformat(
                    event_data["created_at"].replace('Z', '+00:00')
                ).astimezone(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")
                
            elif isinstance(entity, KiwiLockCamera):
                # 更新摄像头实体
                entity._event_data = event_data
                if event_data.get("name") == "HUMAN_WANDERING":
                    # 获取新的视频流信息
                    stream_id = event_data.get("data", {}).get("stream_id")
                    if stream_id:
                        session = hass.data[DOMAIN]["session"]
                        token = hass.data[DOMAIN]["access_token"]
                        video_info = await get_llock_video(
                            hass, token, device_id, session, stream_id
                        )
                        entity._video_info = video_info
            
            # 通知Home Assistant更新实体状态
            async_dispatcher_send(hass, f"{DOMAIN}_{device_id}_update")
            await entity.async_update_ha_state(True)
            
    except Exception as e:
        _LOGGER.error(f"更新设备状态失败: {e}，错误数据结构：{event_data}")


async def stop_websocket_connection(websocket_task):
    """停止 WebSocket 连接任务。"""
    try:
        websocket_task.cancel()
        await websocket_task
        _LOGGER.info("WebSocket 连接任务已成功停止")
    except asyncio.CancelledError:
        _LOGGER.info("WebSocket 连接任务被取消")
    except Exception as e:
        _LOGGER.error(f"停止 WebSocket 连接任务时发生错误: {e}")



