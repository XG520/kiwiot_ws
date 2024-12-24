import logging
import aiohttp
import asyncio
import re
import random
#from .token_manager import get_access_token
from .const import LOGGER_NAME, WS_URL

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
    retry_delay = 5  # 初始重试延迟(秒)

    while retry_count < max_retries:
        try:
            async with session.ws_connect(ws_url) as ws:
                _LOGGER.info(f"WebSocket 连接已建立 (重试次数: {retry_count})")
                
                # 重置重试计数
                retry_count = 0
                retry_delay = 5
                
                # 启动后台任务
                tasks = [
                    asyncio.create_task(send_heartbeat(ws)),
                    asyncio.create_task(handle_websocket_messages(ws))
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
                    
        except aiohttp.ClientResponseError as e:
            _LOGGER.error(f"WebSocket 连接失败: 状态码={e.status}")
            retry_count += 1
        except asyncio.TimeoutError:
            _LOGGER.error("WebSocket 连接超时")
            retry_count += 1
        except Exception as e:
            _LOGGER.error(f"WebSocket 连接错误: {e}")
            retry_count += 1
            
        if retry_count < max_retries:
            wait_time = retry_delay * (2 ** retry_count)  # 指数退避
            _LOGGER.info(f"等待 {wait_time} 秒后重试连接...")
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


async def handle_websocket_messages(ws):
    """处理 WebSocket 消息。"""
    try:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
            #    continue
               _LOGGER.info(f"收到消息: {msg.data}")
            elif msg.type == aiohttp.WSMsgType.ERROR:
                _LOGGER.error(f"WebSocket 错误: {msg.data}")
                break
            elif msg.type == aiohttp.WSMsgType.CLOSED:
                _LOGGER.warning("WebSocket 已关闭")
                break
    except asyncio.CancelledError:
        _LOGGER.info("消息处理任务已取消")
    except Exception as e:
        _LOGGER.error(f"处理 WebSocket 消息时发生错误: {e}")
        raise


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
