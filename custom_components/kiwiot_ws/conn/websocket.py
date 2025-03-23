import logging
import aiohttp
import asyncio
import re
import random
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional
from ..entity.lock import KiwiLockEvent, KiwiLockCamera, KiwiLockStatus
from ..const import LOGGER_NAME, WS_URL, DOMAIN
from .utils import convert_wsevent_format, convert_media_event_format
from homeassistant.helpers.dispatcher import async_dispatcher_send
from .userinfo import get_llock_userinfo
from .token_manager import TokenManager

_LOGGER = logging.getLogger(f"{LOGGER_NAME}_{__name__}")


async def generate_uuid():
    """生成符合特定格式的 UUID 字符串。"""
    def replace_x_or_y(match):
        char = match.group(0)
        if (char == 'x'):
            return hex(random.randint(0, 15))[2]
        elif (char == 'y'):
            return hex(random.randint(8, 11))[2]

    uuid_pattern = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'
    return re.sub(r'[xy]', replace_x_or_y, uuid_pattern)


async def start_websocket_connection(hass, entry, session):
    """启动 WebSocket 连接并维护心跳和消息处理."""
    token_manager = TokenManager(hass, entry)
    access_token = await token_manager.get_token(session)
    ws_url = f"{WS_URL}/?access_token={access_token}" 
    retry_count = 0
    max_retries = 5
    retry_delay = 5
    
    # 创建消息队列
    msg_queue = asyncio.Queue()
    hass.data[DOMAIN]["msg_queue"] = msg_queue
    
    while retry_count < max_retries:
        try:
            if session.closed:
                _LOGGER.warning("Session已关闭,停止WebSocket连接") 
                return
            if DOMAIN not in hass.data:
                _LOGGER.warning("集成已被移除,停止WebSocket连接")
                return
                
            async with session.ws_connect(ws_url) as ws:
                hass.data[DOMAIN]["ws"] = ws
                _LOGGER.info(f"WebSocket 连接已建立 (重试次数: {retry_count})")
                
                tasks = [
                    asyncio.create_task(send_heartbeat(ws)),
                    asyncio.create_task(handle_websocket_messages(ws, hass, entry)),
                    asyncio.create_task(process_message_queue(ws, msg_queue))
                ]
                
                try:
                    done, pending = await asyncio.wait(
                        tasks, 
                        return_when=asyncio.FIRST_EXCEPTION
                    )
                    
                    for task in pending:
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass
                            
                    for task in done:
                        if task.exception():
                            _LOGGER.error(f"WebSocket任务异常: {task.exception()}")
                            raise task.exception()
                            
                except asyncio.CancelledError:
                    _LOGGER.info("WebSocket任务被取消")
                    return
                    
        except aiohttp.ClientError as e:
            if "Session is closed" in str(e):
                _LOGGER.warning("Session已关闭,停止重试")
                return
            _LOGGER.error(f"WebSocket 连接错误: {e}")
            retry_count += 1
            
        if retry_count < max_retries:
            if DOMAIN not in hass.data or session.closed:
                _LOGGER.warning("集成已被移除或session已关闭,停止重试")
                return
            wait_time = retry_delay * (2 ** retry_count)
            await asyncio.sleep(wait_time)
        else:
            _LOGGER.error(f"WebSocket 连接重试次数达到上限 ({max_retries})")
            break

async def send_heartbeat(ws):
    """发送心跳消息。"""
    uuid = await generate_uuid()
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
                    "messageId": uuid,
                    "payloadVersion": 1
                }
            }
            await ws.send_json(ping_message)
            _LOGGER.debug("心跳消息已发送")
            await asyncio.sleep(interval)
    except Exception as e:
        _LOGGER.error(f"心跳消息发送失败: {e}")
        raise

async def send_unlock_command(hass, send_token, unlock_data, device_id) -> bool:
    """发送开锁指令"""
    try:
        msg_queue = hass.data.get(DOMAIN, {}).get("msg_queue")
        if not msg_queue:
            _LOGGER.error("消息队列未初始化")
            return False
            
        uuid = await generate_uuid()
        msg = {
            "header": {
                "namespace": "Iot.Device",
                "name": "Ctrl", 
                "messageId": uuid,
                "payloadVersion": 1,
                "secureToken": send_token
            },
            "payload": {
                "did": device_id,
                "verify": True,
                "data": unlock_data
            }
        }
        
        await msg_queue.put(msg)
        _LOGGER.debug("开锁指令已加入队列")
        return True
        
    except Exception as e:
        _LOGGER.error(f"发送开锁指令失败: {e}")
        return False

async def handle_websocket_messages(ws, hass, entry):
    """处理 WebSocket 消息并更新实体状态"""
    response_futures = {}  
    
    try:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)
                _LOGGER.info(f"接收到消息: {data}")
                
                if data.get("header", {}).get("name") == "CtrlResponse":
                    message_id = data.get("header", {}).get("messageId")
                    if message_id in response_futures:
                        response_futures[message_id].set_result(data)
                        del response_futures[message_id]
                        continue
                
                if (data.get("header", {}).get("namespace") == "Iot.Device" and 
                    data.get("header", {}).get("name") == "EventNotify"):
                    
                    payload = data.get("payload", {})
                    device_id = payload.get("did")
                    event_name = payload.get("name")
                    event_type = payload.get("level")
                    if event_name == "UNLOCKED" or event_name == "LOCKED":
                        payload = await convert_wsevent_format(payload)
                    elif event_type == "CRITICAL" and event_name == "REMOTE_UNLOCK":
                        payload = await convert_media_event_format(payload)
                    else:
                        _LOGGER.warning(f"未知事件类型: {payload}")
                    _LOGGER.info(f"事件数据格式化: {payload}")

                    await update_device_state(hass, entry, device_id, payload)
                    
            elif msg.type == aiohttp.WSMsgType.ERROR:
                _LOGGER.error(f"WebSocket 错误: {msg.data}")
                break
            
    except Exception as e:
        _LOGGER.error(f"处理 WebSocket 消息时发生错误: {e}")
        for future in response_futures.values():
            if not future.done():
                future.set_exception(e)
        raise

async def update_device_state(hass, entry, device_id, event_data):
    """根据WebSocket消息更新设备实体状态"""
    try:
        device_entities = []
        domain_data = hass.data.get(DOMAIN, {})
        
        session = domain_data.get("session")
        if not all([session]):
            _LOGGER.error("无法获取必要组件")
            return
            
        users = await get_llock_userinfo(hass, entry, device_id, session)
  
        if "devices" in domain_data and device_id in domain_data["devices"]:
            device_entities = domain_data["devices"][device_id]
        
        if not device_entities:
            _LOGGER.warning(f"未找到设备ID {device_id} 对应的实体")
            return

        for entity in device_entities:
            try:
                if isinstance(entity, KiwiLockEvent):
                    await update_lock_event(entity, event_data, users)
                elif isinstance(entity, KiwiLockStatus) and event_data.get("name") in {"UNLOCKED", "LOCKED", "LOCK_INDOOR_BUTTON_UNLOCK"}:
                    await update_lock_status(entity, event_data)
                elif isinstance(entity, KiwiLockCamera) and event_data.get("data"):
                    await update_camera(entity, event_data)
            except Exception as entity_error:
                _LOGGER.error(f"更新实体失败: {entity_error}")
                continue

        async_dispatcher_send(hass, f"{DOMAIN}_{device_id}_update")
            
    except Exception as e:
        _LOGGER.error(f"更新设备状态失败: {e}，错误数据结构：{event_data}")

async def update_lock_event(entity, event_data, users):
    """更新门锁事件实体"""
    entity._event = event_data
    entity._users = users
    if "created_at" in event_data:
        entity._event_time = datetime.fromisoformat(
            event_data["created_at"].replace('Z', '+00:00')
        ).astimezone(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")
        entity._notify_time = datetime.fromisoformat(
            event_data["created_at"].replace('Z', '+00:00')
        ).astimezone(ZoneInfo("Asia/Shanghai")).strftime("%H:%M:%S")
    await entity.async_update_ha_state(True)
    _LOGGER.debug(f"已更新设备事件状态: {entity}")

async def update_lock_status(entity, event_data):
    """更新门锁状态实体"""
    entity._event = event_data
    if "created_at" in event_data:
        entity._event_time = datetime.fromisoformat(
            event_data["created_at"].replace('Z', '+00:00')
        ).astimezone(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")
        entity._notify_time = datetime.fromisoformat(
            event_data["created_at"].replace('Z', '+00:00')
        ).astimezone(ZoneInfo("Asia/Shanghai")).strftime("%H:%M:%S")
    await entity.async_update_ha_state(True)
    _LOGGER.debug(f"已更新门锁状态: {entity}")

async def update_camera(entity, event_data):
    """更新相机实体"""
    await entity.update_from_event(event_data)
    await entity.async_update_ha_state(True)
    _LOGGER.debug(f"已更新相机状态和图片")

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

async def process_message_queue(ws, queue):
    """处理消息队列中的请求"""
    try:
        while True:
            try:
                msg = await queue.get()
                if ws.closed:
                    _LOGGER.error("WebSocket已关闭,无法发送消息")
                    queue.task_done()
                    continue

                await ws.send_json(msg)
                _LOGGER.info(f"消息队列发送消息: {msg}")
                queue.task_done()
                    
            except asyncio.CancelledError:
                _LOGGER.info("消息队列处理被取消")
                raise
            except Exception as e:
                _LOGGER.error(f"处理消息队列异常: {e}")
                if not queue.empty():
                    queue.task_done()
                
    except asyncio.CancelledError:
        _LOGGER.info("消息队列处理任务结束")
        raise
    finally:
        for fut in response_futures.values():
            if not fut.done():
                fut.cancel()

response_futures = {}



