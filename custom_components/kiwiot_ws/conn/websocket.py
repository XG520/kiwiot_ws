import logging
import aiohttp
import asyncio
import re
import random
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional, Dict, Any
from ..entity.lock import KiwiLockEvent, KiwiLockCamera, KiwiLockStatus
from ..const import LOGGER_NAME, WS_URL, DOMAIN
from .utils import convert_wsevent_format, convert_media_event_format
from homeassistant.helpers.dispatcher import async_dispatcher_send
from .userinfo import get_llock_userinfo
from .token_manager import TokenManager

_LOGGER = logging.getLogger(f"{LOGGER_NAME}_{__name__}")

response_futures: Dict[str, asyncio.Future] = {}

async def generate_uuid() -> str:
    """生成符合特定格式的 UUID 字符串。"""
    def replace_x_or_y(match):
        char = match.group(0)
        return hex(random.randint(8, 11))[2] if char == 'y' else hex(random.randint(0, 15))[2]

    uuid_pattern = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'
    return re.sub(r'[xy]', replace_x_or_y, uuid_pattern)

async def send_register_request(ws, hass, entry):
    """发送设备注册/订阅请求，确保能接收门锁事件。"""
    try:
        domain_data = hass.data.get(DOMAIN, {})
        devices = domain_data.get("devices", {})

        if not devices:
            _LOGGER.warning("没有可用的设备，跳过注册/订阅")
            return False

        device_ids = list(devices.keys())
        _LOGGER.info(f"准备订阅 {len(device_ids)} 个设备: {device_ids}")

        for device_id in device_ids:
            uuid = await generate_uuid()
            subscribe_msg = {
                "header": {
                    "namespace": "Iot.Device",
                    "name": "Subscribe",
                    "messageId": uuid,
                    "payloadVersion": 1
                },
                "payload": {
                    "did": device_id
                }
            }
            try:
                await ws.send_json(subscribe_msg)
                _LOGGER.info(f"已发送设备订阅请求: {device_id}")
            except Exception as e:
                _LOGGER.error(f"发送设备 {device_id} 订阅请求失败: {e}")

        await asyncio.sleep(1)
        _LOGGER.info("设备注册/订阅请求已全部发送，等待服务器推送事件")
        return True

    except Exception as e:
        _LOGGER.error(f"发送注册请求失败: {e}")
        return False

async def start_websocket_connection(hass, entry, session):
    """启动 WebSocket 连接并维护心跳和消息处理。支持 Session 自动重建。"""
    token_manager = TokenManager(hass, entry)
    base_retry_delay = 5

    msg_queue = asyncio.Queue()
    hass.data[DOMAIN]["msg_queue"] = msg_queue

    retry_count = 0
    current_session = session

    while True:
        tasks = None
        health_task = None
        try:
            # 【核心修复1】检查 session 是否有效，无效则重建
            if current_session.closed:
                _LOGGER.warning("Session已关闭，正在重新创建...")
                from aiohttp import ClientSession, TCPConnector, ClientTimeout
                timeout = ClientTimeout(total=30, connect=10)
                connector = TCPConnector(
                    ssl=True,
                    enable_cleanup_closed=True
                )
                current_session = ClientSession(
                    connector=connector,
                    timeout=timeout,
                    raise_for_status=False
                )
                hass.data[DOMAIN]["session"] = current_session
                _LOGGER.info("Session已重新创建")

            # 检查集成是否仍在运行
            if DOMAIN not in hass.data:
                _LOGGER.warning("集成已被移除,停止WebSocket连接")
                return

            # 获取 token（如果 session 重建，会使用新 session）
            access_token = await token_manager.get_token(current_session)
            if not access_token:
                _LOGGER.error("无法获取有效的 access_token，等待后重试")
                await asyncio.sleep(30)
                continue

            ws_url = f"{WS_URL}/?access_token={access_token}"

            _LOGGER.info(f"WebSocket 连接已建立 (重试次数: {retry_count})")
            async with current_session.ws_connect(ws_url) as ws:
                hass.data[DOMAIN]["ws"] = ws
                _LOGGER.info(f"WebSocket 连接已建立 (重试次数: {retry_count})")
                
                # 【核心修复2】每次连接建立后都执行订阅
                _LOGGER.info("执行设备注册/订阅...")
                await send_register_request(ws, hass, entry)
                # 重连后补拉最新事件，弥补断连期间丢的事件
                if retry_count > 0:
                    await pull_latest_events(hass, entry, current_session)

                # 连接健康检查任务：每2分钟检查一次
                async def connection_health_check(ws_conn, hass_instance, entry):
                    resubscribe_interval = 1800  # 每 30 分钟重新订阅一次，防订阅静默失效
                    reconnect_interval = 14400  # 每 4 小时主动重连一次，防 token 过期后 WebSocket 用旧 token 静默断流
                    loop = asyncio.get_running_loop()
                    last_resubscribe = loop.time()
                    last_reconnect = loop.time()
                    while not ws_conn.closed:
                        await asyncio.sleep(120)
                        if ws_conn.closed:
                            _LOGGER.warning("健康检查发现连接已断开")
                            raise aiohttp.ClientError("连接已断开")
                        # 额外检查：设备列表是否还在
                        if DOMAIN not in hass_instance.data:
                            _LOGGER.warning("健康检查：集成数据已丢失")
                            raise Exception("集成数据丢失")
                        # 定期重新订阅
                        if loop.time() - last_resubscribe >= resubscribe_interval:
                            _LOGGER.info("定期重新订阅设备...")
                            await send_register_request(ws_conn, hass_instance, entry)
                            last_resubscribe = loop.time()
                        # 定期主动重连，防 token 过期后 WebSocket 静默断流
                        if loop.time() - last_reconnect >= reconnect_interval:
                            _LOGGER.warning("定期主动重连 WebSocket（防 token 过期静默断流）")
                            raise aiohttp.ClientError("定期主动重连")
                    _LOGGER.debug("健康检查任务结束")

                health_task = asyncio.create_task(connection_health_check(ws, hass, entry))
                tasks = [
                    asyncio.create_task(send_heartbeat(ws)),
                    asyncio.create_task(handle_websocket_messages(ws, hass, entry)),
                    asyncio.create_task(process_message_queue(ws, msg_queue)),
                    health_task
                ]

                try:
                    done, pending = await asyncio.wait(
                        tasks,
                        return_when=asyncio.FIRST_EXCEPTION
                    )

                    for task in pending:
                        task.cancel()
                        try:
                            await asyncio.wait_for(task, timeout=5)
                        except (asyncio.CancelledError, asyncio.TimeoutError):
                            pass

                    for task in done:
                        exc = task.exception()
                        if exc:
                            _LOGGER.error(f"WebSocket任务异常: {exc}")

                except asyncio.CancelledError:
                    _LOGGER.info("WebSocket任务被取消")
                    return
                finally:
                    if tasks:
                        for task in tasks:
                            if not task.done():
                                task.cancel()
                        try:
                            await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=5)
                        except asyncio.TimeoutError:
                            _LOGGER.warning("清理WebSocket子任务超时，继续重连")
                        _LOGGER.debug("所有WebSocket子任务已清理")

        except aiohttp.ClientError as e:
            if "Session is closed" in str(e):
                _LOGGER.warning("检测到Session已关闭，将在下次循环中重建")
                # 不立即返回，让外层循环处理
            else:
                _LOGGER.error(f"WebSocket 连接错误: {e}")
            retry_count += 1

        except Exception as e:
            _LOGGER.error(f"WebSocket 连接发生未知异常: {e}")
            retry_count += 1

        # 检查是否应该停止
        if DOMAIN not in hass.data:
            _LOGGER.warning("集成已被移除,停止重连")
            return

        # 如果 session 已关闭，标记并在下次循环重建
        if current_session.closed:
            _LOGGER.warning("Session已关闭，将在下次循环重建")
            # 继续循环，下一轮会重建 session
            
        wait_time = base_retry_delay * min(10, 2 ** retry_count)
        _LOGGER.info(f"等待 {wait_time} 秒后重试连接 (当前重试次数: {retry_count})")
        await asyncio.sleep(wait_time)

async def send_heartbeat(ws):
    """发送心跳消息。"""
    interval = 30
    try:
        while not ws.closed:
            uuid = await generate_uuid()
            ping_message = {
                "header": {
                    "namespace": "Iot.Application",
                    "name": "Ping",
                    "messageId": uuid,
                    "payloadVersion": 1
                }
            }
            try:
                await ws.send_json(ping_message)
                _LOGGER.debug("心跳消息已发送")
            except Exception as e:
                _LOGGER.error(f"心跳发送失败: {e}")
                raise

            await asyncio.sleep(interval)

    except asyncio.CancelledError:
        _LOGGER.info("心跳任务被取消")
        raise
    except Exception as e:
        _LOGGER.error(f"心跳任务异常: {e}")
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
        _LOGGER.debug(f"开锁指令已加入队列: {device_id}")
        return True

    except Exception as e:
        _LOGGER.error(f"发送开锁指令失败: {e}")
        return False

async def handle_websocket_messages(ws, hass, entry):
    """处理 WebSocket 消息并更新实体状态。"""
    try:
        while not ws.closed:
            try:
                msg = await ws.receive()

                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        _LOGGER.debug(f"接收到消息: {data}")

                        header = data.get("header", {})
                        if header.get("name") == "CtrlResponse":
                            message_id = header.get("messageId")
                            if message_id in response_futures:
                                response_futures[message_id].set_result(data)
                                del response_futures[message_id]
                                continue

                        if (header.get("namespace") == "Iot.Device" and
                            header.get("name") == "EventNotify"):
                            await process_device_event(hass, entry, data)

                    except json.JSONDecodeError as e:
                        _LOGGER.error(f"JSON解析错误: {e}")
                        continue

                elif msg.type == aiohttp.WSMsgType.ERROR:
                    _LOGGER.error(f"WebSocket 错误: {msg.data}")
                    break
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    _LOGGER.warning("WebSocket 连接已关闭")
                    break

            except asyncio.CancelledError:
                _LOGGER.info("WebSocket消息处理任务被取消")
                raise
            except Exception as e:
                _LOGGER.error(f"接收消息异常: {e}")
                raise

    except asyncio.CancelledError:
        _LOGGER.info("WebSocket消息处理任务被取消")
        raise
    except Exception as e:
        _LOGGER.error(f"处理 WebSocket 消息时发生错误: {e}")
        for future in response_futures.values():
            if not future.done():
                future.set_exception(e)
        raise
    finally:
        for future in response_futures.values():
            if not future.done():
                future.cancel()

async def process_device_event(hass, entry, data):
    """处理设备事件通知"""
    payload = data.get("payload", {})
    device_id = payload.get("did")
    event_name = payload.get("name")
    event_type = payload.get("level")

    try:
        if event_name in {"UNLOCKED", "LOCKED"}:
            payload = await convert_wsevent_format(payload)
        elif event_type == "CRITICAL" and event_name == "REMOTE_UNLOCK":
            payload = await convert_media_event_format(payload)
        else:
            # 将这些"已知但无附加数据"的事件加入白名单，不再报警
            if event_name in {"LOCK_INDOOR_BUTTON_UNLOCK", "HUMAN_WANDERING", "LOCK_FINGER_VEIN_FRONZEN", "ACTIVE_MONITOR"}:
                _LOGGER.debug(f"接收到已知事件（无附加数据）: {event_name}")
            else:
                _LOGGER.warning(f"未知事件类型: {payload}")

        _LOGGER.debug(f"事件数据格式化: {payload}")
        await update_device_state(hass, entry, device_id, payload)

    except Exception as e:
        _LOGGER.error(f"处理设备事件失败: {e}")

async def pull_latest_events(hass, entry, session):
    """重连后补拉各设备最新事件，弥补断连期间丢的事件"""
    from .userinfo import get_llock_info
    from .utils import get_latest_event
    domain_data = hass.data.get(DOMAIN, {})
    devices = domain_data.get("devices", {})
    if not devices:
        return
    for device_id in devices:
        try:
            events = await get_llock_info(hass, entry, device_id, session)
            if not events:
                continue
            latest = await get_latest_event(events)
            if not latest:
                continue
            name = latest.get("name")
            level = latest.get("level")
            event_data = {
                "did": device_id,
                "name": name,
                "level": level,
                "created_at": latest.get("created_at"),
                "data": latest.get("data", {}),
            }
            if name in {"UNLOCKED", "LOCKED"}:
                event_data = await convert_wsevent_format(event_data)
            elif level == "CRITICAL" and name == "REMOTE_UNLOCK":
                event_data = await convert_media_event_format(event_data)
            await update_device_state(hass, entry, device_id, event_data)
        except Exception as e:
            _LOGGER.error(f"补拉设备 {device_id} 事件失败: {e}")

async def update_device_state(hass, entry, device_id, event_data):
    """根据WebSocket消息更新设备实体状态"""
    try:
        domain_data = hass.data.get(DOMAIN, {})
        device_entities = domain_data.get("devices", {}).get(device_id, [])

        if not device_entities:
            _LOGGER.warning(f"未找到设备ID {device_id} 对应的实体")
            return

        session = domain_data.get("session")
        if not session:
            _LOGGER.error("无法获取会话实例")
            return

        users = await get_llock_userinfo(hass, entry, device_id, session)

        update_tasks = []
        for entity in device_entities:
            if isinstance(entity, KiwiLockEvent):
                update_tasks.append(update_lock_event(entity, event_data, users))
            elif isinstance(entity, KiwiLockStatus) and event_data.get("name") in {"UNLOCKED", "LOCKED", "LOCK_INDOOR_BUTTON_UNLOCK"}:
                update_tasks.append(update_lock_status(entity, event_data))
            elif isinstance(entity, KiwiLockCamera) and event_data.get("data"):
                update_tasks.append(update_camera(entity, event_data))

        await asyncio.gather(*update_tasks, return_exceptions=True)
        async_dispatcher_send(hass, f"{DOMAIN}_{device_id}_update")

    except Exception as e:
        _LOGGER.error(f"更新设备状态失败: {e}，错误数据结构：{event_data}")

async def update_lock_event(entity, event_data, users):
    """更新门锁事件实体"""
    try:
        entity._event = event_data
        entity._users = users
        if "created_at" in event_data:
            timestamp = datetime.fromisoformat(
                event_data["created_at"].replace('Z', '+00:00')
            ).astimezone(ZoneInfo("Asia/Shanghai"))
            entity._event_time = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            entity._notify_time = timestamp.strftime("%H:%M:%S")
        await entity.async_update_ha_state(True)
        _LOGGER.debug(f"已更新设备事件状态: {entity}")
    except Exception as e:
        _LOGGER.error(f"更新门锁事件失败: {e}")

async def update_lock_status(entity, event_data):
    """更新门锁状态实体"""
    try:
        entity._event = event_data
        if "created_at" in event_data:
            timestamp = datetime.fromisoformat(
                event_data["created_at"].replace('Z', '+00:00')
            ).astimezone(ZoneInfo("Asia/Shanghai"))
            entity._event_time = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            entity._notify_time = timestamp.strftime("%H:%M:%S")
        await entity.async_update_ha_state(True)
        _LOGGER.debug(f"已更新门锁状态: {entity}")
    except Exception as e:
        _LOGGER.error(f"更新门锁状态失败: {e}")

async def update_camera(entity, event_data):
    """更新相机实体"""
    try:
        await entity.update_from_event(event_data)
        await entity.async_update_ha_state(True)
        _LOGGER.debug("已更新相机状态和图片")
    except Exception as e:
        _LOGGER.error(f"更新相机状态失败: {e}")

async def stop_websocket_connection(websocket_task):
    """停止 WebSocket 连接任务。"""
    if not websocket_task:
        return

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
                _LOGGER.debug(f"消息队列发送消息: {msg}")
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
