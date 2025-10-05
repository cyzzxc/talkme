"""
Pytest配置文件
提供测试所需的共享fixture
"""

import os
import sys
import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from httpx import AsyncClient, ASGITransport

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.database import Base, get_async_db
from app.config import settings


# 测试数据库配置
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_db_engine():
    """创建测试数据库引擎"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True
    )

    # 创建所有表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # 清理数据库
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """创建测试数据库会话"""
    async_session = async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def test_client(test_db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """创建测试HTTP客户端（未认证）"""

    # 覆盖依赖项
    async def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_async_db] = override_get_db

    # 设置测试密码
    os.environ["APP_SECRET"] = "test_secret"

    # 创建客户端（不带认证头）
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test"
    ) as client:
        yield client

    # 清理
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def authenticated_client(test_db_session: AsyncSession) -> AsyncGenerator[tuple[AsyncClient, str], None]:
    """创建已认证的测试HTTP客户端"""

    # 覆盖依赖项
    async def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_async_db] = override_get_db

    # 设置测试密码
    os.environ["APP_SECRET"] = "test_secret"

    # 创建客户端
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test"
    ) as client:
        # 执行登录获取token
        login_response = await client.post(
            "/api/auth/login",
            json={"password": "test_secret"}
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # 设置认证头
        client.headers.update({"Authorization": f"Bearer {token}"})

        yield client, token

    # 清理
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    """获取认证头（需要手动获取token后使用）"""
    return lambda token: {"Authorization": f"Bearer {token}"}
