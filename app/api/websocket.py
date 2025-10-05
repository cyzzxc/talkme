"""
WebSocket通信API
实现实时消息推送、设备状态管理
"""

import json
import asyncio
from typing import Dict, Set
from datetime import datetime, UTC

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from loguru import logger

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """
    WebSocket连接管理器
    管理所有活动的WebSocket连接
    """

    def __init__(self):
        # 活动连接字典：device_id -> Set[WebSocket]
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # 连接到设备ID的映射：WebSocket -> device_id
        self.connection_to_device: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, device_id: str):
        """
        接受新的WebSocket连接
        """
        await websocket.accept()

        # 添加到活动连接
        if device_id not in self.active_connections:
            self.active_connections[device_id] = set()

        self.active_connections[device_id].add(websocket)
        self.connection_to_device[websocket] = device_id

        # 广播设备上线消息
        await self.broadcast_device_status(device_id, "online")

    def disconnect(self, websocket: WebSocket):
        """
        断开WebSocket连接
        """
        # 获取设备ID
        device_id = self.connection_to_device.get(websocket)

        if device_id:
            # 从活动连接中移除
            if device_id in self.active_connections:
                self.active_connections[device_id].discard(websocket)

                # 如果该设备没有其他连接，移除设备记录
                if not self.active_connections[device_id]:
                    del self.active_connections[device_id]

            # 从映射中移除
            del self.connection_to_device[websocket]

        return device_id

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """
        向特定连接发送消息
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"发送消息失败: {e}")

    async def send_to_device(self, message: dict, device_id: str):
        """
        向特定设备的所有连接发送消息
        """
        if device_id in self.active_connections:
            # 复制集合以避免迭代时修改
            connections = list(self.active_connections[device_id])

            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"向设备 {device_id} 发送消息失败: {e}")
                    # 连接失败，清理该连接
                    self.disconnect(connection)

    async def broadcast(self, message: dict, exclude_device: str = None):
        """
        广播消息给所有连接
        """
        # 收集所有需要发送的连接
        connections_to_send = []

        for device_id, connections in self.active_connections.items():
            if exclude_device and device_id == exclude_device:
                continue

            connections_to_send.extend(connections)

        # 并发发送消息
        tasks = []
        for connection in connections_to_send:
            tasks.append(self.send_personal_message(message, connection))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def broadcast_device_status(self, device_id: str, status: str):
        """
        广播设备状态变化
        """
        message = {
            "type": "device_status",
            "device_id": device_id,
            "status": status,
            "timestamp": datetime.now(UTC).isoformat(),
            "online_devices": list(self.active_connections.keys())
        }

        await self.broadcast(message)

    async def broadcast_new_message(self, message_data: dict):
        """
        广播新消息
        """
        message = {
            "type": "new_message",
            "data": message_data,
            "timestamp": datetime.now(UTC).isoformat()
        }

        await self.broadcast(message)

    async def broadcast_message_deleted(self, message_id: int):
        """
        广播消息删除事件
        """
        message = {
            "type": "message_deleted",
            "message_id": message_id,
            "timestamp": datetime.now(UTC).isoformat()
        }

        await self.broadcast(message)

    async def send_typing_indicator(self, device_id: str, is_typing: bool):
        """
        发送正在输入指示器
        """
        message = {
            "type": "typing",
            "device_id": device_id,
            "is_typing": is_typing,
            "timestamp": datetime.now(UTC).isoformat()
        }

        await self.broadcast(message, exclude_device=device_id)

    def get_online_devices(self) -> list:
        """
        获取所有在线设备
        """
        return list(self.active_connections.keys())

    def get_connection_count(self, device_id: str = None) -> int:
        """
        获取连接数
        """
        if device_id:
            return len(self.active_connections.get(device_id, set()))
        else:
            return sum(len(conns) for conns in self.active_connections.values())


# 全局连接管理器实例
manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    device_id: str = Query(default="unknown")
):
    """
    WebSocket连接端点
    支持实时消息推送和设备状态管理
    """
    await manager.connect(websocket, device_id)

    try:
        # 发送欢迎消息
        await manager.send_personal_message({
            "type": "connected",
            "message": "WebSocket连接成功",
            "device_id": device_id,
            "online_devices": manager.get_online_devices(),
            "timestamp": datetime.now(UTC).isoformat()
        }, websocket)

        # 监听客户端消息
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                message_type = message.get("type")

                # 处理不同类型的消息
                if message_type == "ping":
                    # 心跳响应
                    await manager.send_personal_message({
                        "type": "pong",
                        "timestamp": datetime.now(UTC).isoformat()
                    }, websocket)

                elif message_type == "typing":
                    # 正在输入指示器
                    is_typing = message.get("is_typing", False)
                    await manager.send_typing_indicator(device_id, is_typing)

                elif message_type == "broadcast":
                    # 广播消息（测试用）
                    content = message.get("content", "")
                    await manager.broadcast({
                        "type": "broadcast",
                        "device_id": device_id,
                        "content": content,
                        "timestamp": datetime.now(UTC).isoformat()
                    })

                elif message_type == "get_online_devices":
                    # 获取在线设备列表
                    await manager.send_personal_message({
                        "type": "online_devices",
                        "devices": manager.get_online_devices(),
                        "count": manager.get_connection_count(),
                        "timestamp": datetime.now(UTC).isoformat()
                    }, websocket)

                else:
                    # 未知消息类型
                    await manager.send_personal_message({
                        "type": "error",
                        "message": f"未知的消息类型: {message_type}",
                        "timestamp": datetime.now(UTC).isoformat()
                    }, websocket)

            except json.JSONDecodeError:
                # JSON解析错误
                await manager.send_personal_message({
                    "type": "error",
                    "message": "无效的JSON格式",
                    "timestamp": datetime.now(UTC).isoformat()
                }, websocket)

            except Exception as e:
                # 其他错误
                await manager.send_personal_message({
                    "type": "error",
                    "message": f"处理消息时出错: {str(e)}",
                    "timestamp": datetime.now(UTC).isoformat()
                }, websocket)

    except WebSocketDisconnect:
        # WebSocket断开连接
        disconnected_device = manager.disconnect(websocket)

        if disconnected_device:
            # 广播设备离线消息
            await manager.broadcast_device_status(disconnected_device, "offline")

    except Exception as e:
        # 其他异常
        logger.error(f"WebSocket错误: {e}")
        disconnected_device = manager.disconnect(websocket)

        if disconnected_device:
            await manager.broadcast_device_status(disconnected_device, "offline")


@router.get("/ws/stats")
async def get_websocket_stats():
    """
    获取WebSocket连接统计信息
    不需要WebSocket连接即可访问
    """
    return {
        "online_devices": manager.get_online_devices(),
        "total_connections": manager.get_connection_count(),
        "device_connections": {
            device_id: manager.get_connection_count(device_id)
            for device_id in manager.get_online_devices()
        },
        "timestamp": datetime.now(UTC).isoformat()
    }


# 导出manager以便其他模块使用
__all__ = ["router", "manager"]