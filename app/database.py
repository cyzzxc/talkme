"""
数据库连接和配置模块
支持 SQLite 数据库，提供异步和同步会话管理
"""

import os
from typing import AsyncGenerator, Generator
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from loguru import logger


# 数据库配置
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./files.db")
ASYNC_DATABASE_URL = DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://")

# 创建同步引擎（用于初始化和迁移）
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=os.getenv("DEBUG", "false").lower() == "true"
)

# 创建异步引擎（用于应用运行时）
logger.info(f"正在创建异步引擎，URL: {ASYNC_DATABASE_URL}")
try:
    async_engine = create_async_engine(
        ASYNC_DATABASE_URL,
        echo=os.getenv("DEBUG", "false").lower() == "true"
    )
    logger.info("异步引擎创建成功")
except Exception as e:
    logger.error(f"异步引擎创建失败: {e}")
    raise

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False
)

# 创建基础模型类
Base = declarative_base()

# 元数据对象，用于表创建和迁移
metadata = MetaData()


def create_tables():
    """
    创建所有数据库表
    """
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """
    删除所有数据库表（用于测试和重置）
    """
    Base.metadata.drop_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    获取同步数据库会话
    用于依赖注入
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    获取异步数据库会话
    用于异步依赖注入
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """
    初始化数据库
    创建所有表和索引
    """
    async with async_engine.begin() as conn:
        # 导入所有模型以确保它们被注册

        # 创建所有表
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """
    关闭数据库连接
    用于应用关闭时清理资源
    """
    await async_engine.dispose()


# 数据库健康检查
async def check_db_health() -> bool:
    """
    检查数据库连接是否正常
    """
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception:
        return False


def check_db_health_sync() -> bool:
    """
    同步版本的数据库健康检查
    """
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
            return True
    except Exception:
        return False


def debug_engine_status():
    """
    调试引擎状态
    """
    logger.info("=" * 50)
    logger.info("数据库引擎调试信息")
    logger.info("=" * 50)
    logger.info(f"同步数据库URL: {DATABASE_URL}")
    logger.info(f"异步数据库URL: {ASYNC_DATABASE_URL}")
    logger.info(f"同步引擎状态: {engine}")
    logger.info(f"异步引擎状态: {async_engine}")
    logger.info(f"DEBUG模式: {os.getenv('DEBUG', 'false').lower() == 'true'}")
    
    # 检查同步引擎
    try:
        with SessionLocal() as session:
            result = session.execute(text("SELECT 1")).scalar()
            logger.info(f"同步引擎测试: 成功 (结果: {result})")
    except Exception as e:
        logger.error(f"同步引擎测试: 失败 - {e}")
    
    # 检查异步引擎（需要异步上下文）
    logger.info("异步引擎测试需要异步上下文，请使用 check_db_health() 函数")
    logger.info("=" * 50)