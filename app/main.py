"""
文件传输助手 - FastAPI主应用
支持文件上传、消息管理、WebSocket实时通信
"""
from loguru import logger
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import settings
from .database import init_db, close_db, check_db_health
from .api import auth_router, files_router, messages_router, websocket_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    """
    # 启动时执行
    logger.info("🚀 启动文件传输助手...")

    # 确保目录存在
    settings.ensure_directories()
    logger.info("✓ 目录结构检查完成")

    # 初始化数据库
    await init_db()
    logger.info("✓ 数据库初始化完成")

    # 检查数据库健康状态
    if await check_db_health():
        logger.info("✓ 数据库连接正常")
    else:
        logger.warning("⚠ 数据库连接异常")

    logger.info(f"✓ 服务启动成功，监听地址: {settings.APP_HOST}:{settings.APP_PORT}")
    logger.info(f"✓ 调试模式: {'开启' if settings.DEBUG else '关闭'}")

    yield

    # 关闭时执行
    logger.info("👋 关闭文件传输助手...")
    await close_db()
    logger.info("✓ 数据库连接已关闭")


# 创建FastAPI应用
app = FastAPI(
    title="文件传输助手",
    description="个人文件传输助手API - 支持文件上传、消息管理、实时通信",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)


# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 全局异常处理
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    HTTP异常处理
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    请求验证异常处理
    """
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": True,
            "message": "请求参数验证失败",
            "details": exc.errors(),
            "status_code": 422
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    通用异常处理
    """
    import traceback

    error_detail = str(exc)

    if settings.DEBUG:
        error_detail = f"{str(exc)}\n\n{traceback.format_exc()}"

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "message": "服务器内部错误",
            "detail": error_detail if settings.DEBUG else "请联系管理员",
            "status_code": 500
        }
    )


# 注册路由
app.include_router(auth_router)
app.include_router(files_router)
app.include_router(messages_router)
app.include_router(websocket_router)


# 根路由
@app.get("/", tags=["系统"])
async def root():
    """
    根路径，返回API信息
    """
    return {
        "name": "文件传输助手",
        "version": "0.1.0",
        "description": "个人文件传输助手API",
        "docs": "/docs" if settings.DEBUG else None,
        "endpoints": {
            "auth": "/api/auth",
            "files": "/api/files",
            "messages": "/api/messages",
            "websocket": "/ws"
        }
    }


# 健康检查
@app.get("/health", tags=["系统"])
async def health_check():
    """
    健康检查端点
    """
    db_healthy = await check_db_health()

    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "database": "connected" if db_healthy else "disconnected",
        "version": "0.1.0"
    }


# 系统信息
@app.get("/api/system/info", tags=["系统"])
async def system_info():
    """
    获取系统信息
    """
    import sys

    return {
        "version": "0.1.0",
        "python_version": sys.version,
        "platform": sys.platform,
        "debug": settings.DEBUG,
        "max_file_size": settings.MAX_FILE_SIZE,
        "max_file_size_formatted": f"{settings.MAX_FILE_SIZE / 1024 / 1024:.1f}MB",
        "allowed_extensions": settings.ALLOWED_EXTENSIONS,
        "upload_dir": settings.UPLOAD_DIR,
        "file_dedup_enabled": settings.ENABLE_FILE_DEDUP
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info"
    )