#!/usr/bin/env python3
"""
启动脚本
启动文件传输助手后端服务
"""

import os
import sys
import uvicorn
from loguru import logger

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import settings


def main():
    """
    主函数
    """
    logger.info("=" * 60)
    logger.info("文件传输助手 - 后端服务")
    logger.info("=" * 60)
    logger.info(f"监听地址: {settings.APP_HOST}:{settings.APP_PORT}")
    logger.info(f"调试模式: {'开启' if settings.DEBUG else '关闭'}")
    logger.info(f"最大文件大小: {settings.MAX_FILE_SIZE / 1024 / 1024:.1f}MB")
    logger.info(f"文件去重: {'开启' if settings.ENABLE_FILE_DEDUP else '关闭'}")
    logger.info("=" * 60)

    # 启动服务
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
        access_log=True
    )


if __name__ == "__main__":
    main()