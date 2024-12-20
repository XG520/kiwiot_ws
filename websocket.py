import logging
import aiohttp
import asyncio
import re
import random
#from .token_manager import get_access_token
from .const import LOGGER_NAME, WS_URL

_LOGGER = logging.getLogger(LOGGER_NAME)


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

#v1.0.0/websocket.py
# async def start_websocket_connection(hass, config):
#     """启动 WebSocket 连接并维护心跳和消息处理."""
#     identifier = config.get(CONF_IDENTIFIER)
#     credential = config.get(CONF_CREDENTIAL)
#     client_id = config.get(CONF_CLIENT_ID)

#     # 获取 access_token
#     access_token = await get_access_token(identifier, credential, client_id)
#     if not access_token:
#         _LOGGER.error("无法获取 token，WebSocket 连接无法启动")
#         return

#     # 拼接 WebSocket URL
#     ws_url = f"wss://wsapi.kiwiot.com/?access_token={access_token}"
#     _LOGGER.debug(f"WebSocket URL: {ws_url}")

#     try:
#         async with aiohttp.ClientSession() as session:
#             async with session.ws_connect(ws_url) as ws:
#                 _LOGGER.info("WebSocket 连接已建立")

#                 # 启动后台任务：心跳与消息处理
#                 tasks = [
#                     asyncio.create_task(send_heartbeat(ws)),
#                     asyncio.create_task(handle_websocket_messages(ws))
#                 ]

#                 # 等待任务完成
#                 done, pending = await asyncio.wait(
#                     tasks,
#                     return_when=asyncio.FIRST_EXCEPTION
#                 )

#                 # 取消未完成的任务
#                 for task in pending:
#                     task.cancel()

#                 # 检查是否有异常
#                 for task in done:
#                     if task.exception():
#                         raise task.exception()
#     except aiohttp.ClientResponseError as e:
#         _LOGGER.error(f"WebSocket 连接失败: 状态码={e.status}, 响应={e.message}, URL={ws_url}")
#     except asyncio.TimeoutError:
#         _LOGGER.error("WebSocket 连接超时")
#     except Exception as e:
#         _LOGGER.error(f"WebSocket 连接时发生其他错误: {e}")

async def start_websocket_connection(hass, access_token, session):
    """启动 WebSocket 连接并维护心跳和消息处理."""
    ws_url = f"{WS_URL}/?access_token={access_token}"
    _LOGGER.debug(f"WebSocket URL: {ws_url}")

    try:
        async with session.ws_connect(ws_url) as ws:
            _LOGGER.info(f"WebSocket 连接已建立，WebSocket URL: {ws_url}")
            # 启动后台任务：心跳与消息处理
            tasks = [
                asyncio.create_task(send_heartbeat(ws)),
                asyncio.create_task(handle_websocket_messages(ws))
            ]
            # 等待任务完成
            done, pending = await asyncio.wait(
                tasks,
                return_when=asyncio.FIRST_EXCEPTION
            )
            # 取消未完成的任务
            for task in pending:
                task.cancel()
            # 检查是否有异常
            for task in done:
                if task.exception():
                    raise task.exception()
    except aiohttp.ClientResponseError as e:
        _LOGGER.error(f"WebSocket 连接失败: 状态码={e.status}, 响应={e.message}, URL={ws_url}")
    except asyncio.TimeoutError:
        _LOGGER.error("WebSocket 连接超时")
    except Exception as e:
        _LOGGER.error(f"WebSocket 连接时发生其他错误: {e}")

async def send_heartbeat(ws):
    """发送心跳消息."""
    interval = 30  # 心跳间隔时间，单位为秒
    try:
        while True:
            ping_message = {
                "header": {
                    "namespace": "Iot.Application",
                    "name": "Ping",
                    "messageId": generate_uuid(),
                    "payloadVersion": 1
                }
            }
            await ws.send_json(ping_message)
            _LOGGER.debug(f"发送心跳消息: {ping_message}")
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        _LOGGER.info("心跳任务已取消")
    except Exception as e:
        _LOGGER.error(f"发送心跳消息失败: {e}")
        raise


async def handle_websocket_messages(ws):
    """处理 WebSocket 消息."""
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
    """停止 WebSocket 连接任务."""
    try:
        websocket_task.cancel()
        await websocket_task
        _LOGGER.info("WebSocket 连接任务已成功停止")
    except asyncio.CancelledError:
        _LOGGER.info("WebSocket 连接任务被取消")
    except Exception as e:
        _LOGGER.error(f"停止 WebSocket 连接任务时发生错误: {e}")
