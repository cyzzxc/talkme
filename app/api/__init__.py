"""
API路由包
包含所有API端点的路由定义
"""

from .auth import router as auth_router
from .files import router as files_router
from .messages import router as messages_router
from .websocket import router as websocket_router

__all__ = ["auth_router", "files_router", "messages_router", "websocket_router"]