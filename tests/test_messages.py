"""
消息API测试模块
测试文本消息的发送、接收、删除等功能
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.message import Message

class TestAuthentication:
    """认证相关测试"""

    @pytest.mark.asyncio
    async def test_send_message_without_auth(self, test_client: AsyncClient):
        """测试未认证时发送消息应失败"""
        message_data = {
            "content": "测试消息",
            "device_id": "test_device"
        }

        response = await test_client.post("/api/messages/text", json=message_data)

        assert response.status_code == 401
        assert "detail" in response.json()

    @pytest.mark.asyncio
    async def test_get_messages_without_auth(self, test_client: AsyncClient):
        """测试未认证时获取消息列表应失败"""
        response = await test_client.get("/api/messages/")

        assert response.status_code == 401
        assert "detail" in response.json()


class TestTextMessages:
    """文本消息相关测试"""

    @pytest.mark.asyncio
    async def test_send_text_message_success(
        self, authenticated_client: tuple, test_db_session: AsyncSession
    ):
        """测试成功发送文本消息"""
        test_client, token = authenticated_client

        # 准备测试数据
        message_data = {
            "content": "这是一条测试消息",
            "device_id": "test_device_001"
        }

        # 发送请求
        response = await test_client.post("/api/messages/text", json=message_data)

        # 验证响应
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["message_type"] == "text"
        assert response_data["content"] == message_data["content"]
        assert response_data["device_id"] == message_data["device_id"]
        assert response_data["is_deleted"] is False
        assert response_data["status"] == "sent"
        assert "id" in response_data
        assert "timestamp" in response_data

        # 验证数据库
        stmt = select(Message).where(Message.id == response_data["id"])
        result = await test_db_session.execute(stmt)
        db_message = result.scalar_one_or_none()

        assert db_message is not None
        assert db_message.content == message_data["content"]
        assert db_message.device_id == message_data["device_id"]
        assert db_message.message_type == "text"

    @pytest.mark.asyncio
    async def test_send_text_message_without_device_id(
        self, authenticated_client: tuple
    ):
        """测试不带设备ID发送消息"""
        test_client, token = authenticated_client

        message_data = {
            "content": "测试消息不带设备ID"
        }

        response = await test_client.post("/api/messages/text", json=message_data)

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["content"] == message_data["content"]
        assert response_data["device_id"] is None

    @pytest.mark.asyncio
    async def test_send_empty_text_message(self, authenticated_client: tuple):
        """测试发送空消息（应该失败）"""
        test_client, token = authenticated_client

        message_data = {
            "content": "   ",  # 空白消息
            "device_id": "test_device_001"
        }

        response = await test_client.post("/api/messages/text", json=message_data)

        assert response.status_code == 400
        assert "消息内容不能为空" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_send_long_text_message(self, authenticated_client: tuple):
        """测试发送长文本消息"""
        test_client, token = authenticated_client

        long_content = "测试" * 1000  # 2000个字符
        message_data = {
            "content": long_content,
            "device_id": "test_device_001"
        }

        response = await test_client.post("/api/messages/text", json=message_data)

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["content"] == long_content


class TestMessageRetrieval:
    """消息获取相关测试"""

    @pytest.mark.asyncio
    async def test_get_message_list_empty(self, authenticated_client: tuple):
        """测试获取空消息列表"""
        test_client, token = authenticated_client

        response = await test_client.get("/api/messages/")

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["total"] == 0
        assert response_data["messages"] == []
        assert response_data["page"] == 1

    @pytest.mark.asyncio
    async def test_get_message_list_with_messages(
        self, authenticated_client: tuple, test_db_session: AsyncSession
    ):
        """测试获取消息列表（有消息）"""
        test_client, token = authenticated_client

        # 先创建几条消息
        messages = [
            Message.create_text_message(f"测试消息 {i}", f"device_{i}")
            for i in range(5)
        ]
        for msg in messages:
            test_db_session.add(msg)
        await test_db_session.commit()

        # 获取消息列表
        response = await test_client.get("/api/messages/")

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["total"] == 5
        assert len(response_data["messages"]) == 5

        # 验证消息按时间倒序排列
        timestamps = [msg["timestamp"] for msg in response_data["messages"]]
        assert timestamps == sorted(timestamps, reverse=True)

    @pytest.mark.asyncio
    async def test_get_message_list_pagination(
        self, authenticated_client: tuple, test_db_session: AsyncSession
    ):
        """测试消息列表分页"""
        test_client, token = authenticated_client

        # 创建10条消息
        messages = [
            Message.create_text_message(f"测试消息 {i}", "test_device")
            for i in range(10)
        ]
        for msg in messages:
            test_db_session.add(msg)
        await test_db_session.commit()

        # 获取第1页，每页3条
        response = await test_client.get("/api/messages/?page=1&page_size=3")

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["total"] == 10
        assert len(response_data["messages"]) == 3
        assert response_data["page"] == 1
        assert response_data["page_size"] == 3

        # 获取第2页
        response = await test_client.get("/api/messages/?page=2&page_size=3")
        response_data = response.json()
        assert len(response_data["messages"]) == 3
        assert response_data["page"] == 2

    @pytest.mark.asyncio
    async def test_get_message_list_filter_by_type(
        self, authenticated_client: tuple, test_db_session: AsyncSession
    ):
        """测试按消息类型过滤"""
        test_client, token = authenticated_client

        # 创建不同类型的消息
        text_messages = [
            Message.create_text_message(f"文本消息 {i}", "test_device")
            for i in range(3)
        ]
        for msg in text_messages:
            test_db_session.add(msg)
        await test_db_session.commit()

        # 只获取文本消息
        response = await test_client.get("/api/messages/?message_type=text")

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["total"] == 3
        for msg in response_data["messages"]:
            assert msg["message_type"] == "text"

    @pytest.mark.asyncio
    async def test_get_single_message_success(
        self, authenticated_client: tuple, test_db_session: AsyncSession
    ):
        """测试获取单条消息"""
        test_client, token = authenticated_client

        # 创建一条消息
        message = Message.create_text_message("测试消息", "test_device")
        test_db_session.add(message)
        await test_db_session.commit()
        await test_db_session.refresh(message)

        # 获取消息
        response = await test_client.get(f"/api/messages/{message.id}")

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["id"] == message.id
        assert response_data["content"] == "测试消息"

    @pytest.mark.asyncio
    async def test_get_single_message_not_found(self, authenticated_client: tuple):
        """测试获取不存在的消息"""
        test_client, token = authenticated_client

        response = await test_client.get("/api/messages/99999")

        assert response.status_code == 404
        assert "消息不存在" in response.json()["detail"]


class TestMessageDeletion:
    """消息删除相关测试"""

    @pytest.mark.asyncio
    async def test_delete_text_message_success(
        self, authenticated_client: tuple, test_db_session: AsyncSession
    ):
        """测试成功删除文本消息"""
        test_client, token = authenticated_client

        # 创建一条消息
        message = Message.create_text_message("要删除的消息", "test_device")
        test_db_session.add(message)
        await test_db_session.commit()
        await test_db_session.refresh(message)
        message_id = message.id

        # 删除消息
        response = await test_client.delete(f"/api/messages/{message_id}")

        assert response.status_code == 200
        assert "消息已删除" in response.json()["message"]

        # 验证数据库中消息被标记为删除
        stmt = select(Message).where(Message.id == message_id)
        result = await test_db_session.execute(stmt)
        db_message = result.scalar_one_or_none()

        assert db_message is not None
        assert db_message.is_deleted is True

    @pytest.mark.asyncio
    async def test_delete_message_not_found(self, authenticated_client: tuple):
        """测试删除不存在的消息"""
        test_client, token = authenticated_client

        response = await test_client.delete("/api/messages/99999")

        assert response.status_code == 404
        assert "消息不存在" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_already_deleted_message(
        self, authenticated_client: tuple, test_db_session: AsyncSession
    ):
        """测试删除已删除的消息"""
        test_client, token = authenticated_client

        # 创建并标记为删除的消息
        message = Message.create_text_message("已删除的消息", "test_device")
        message.mark_as_deleted()
        test_db_session.add(message)
        await test_db_session.commit()
        await test_db_session.refresh(message)

        # 尝试再次删除
        response = await test_client.delete(f"/api/messages/{message.id}")

        assert response.status_code == 404


class TestMessageStatus:
    """消息状态相关测试"""

    @pytest.mark.asyncio
    async def test_update_message_status_success(
        self, authenticated_client: tuple, test_db_session: AsyncSession
    ):
        """测试成功更新消息状态"""
        test_client, token = authenticated_client

        # 创建消息
        message = Message.create_text_message("测试消息", "test_device")
        test_db_session.add(message)
        await test_db_session.commit()
        await test_db_session.refresh(message)

        # 更新状态为已读
        response = await test_client.put(
            f"/api/messages/{message.id}/status?new_status=read"
        )

        assert response.status_code == 200
        assert "已更新为: read" in response.json()["message"]

        # 验证数据库
        await test_db_session.refresh(message)
        assert message.status == "read"

    @pytest.mark.asyncio
    async def test_update_message_status_invalid(
        self, authenticated_client: tuple, test_db_session: AsyncSession
    ):
        """测试使用无效状态更新消息"""
        test_client, token = authenticated_client

        # 创建消息
        message = Message.create_text_message("测试消息", "test_device")
        test_db_session.add(message)
        await test_db_session.commit()
        await test_db_session.refresh(message)

        # 使用无效状态
        response = await test_client.put(
            f"/api/messages/{message.id}/status?new_status=invalid_status"
        )

        assert response.status_code == 400
        assert "无效的状态值" in response.json()["detail"]


class TestMessageStats:
    """消息统计相关测试"""

    @pytest.mark.asyncio
    async def test_get_message_stats_empty(self, authenticated_client: tuple):
        """测试获取空统计信息"""
        test_client, token = authenticated_client

        response = await test_client.get("/api/messages/stats/summary")

        assert response.status_code == 200
        stats = response.json()
        assert stats["total_messages"] == 0
        assert stats["today_messages"] == 0

    @pytest.mark.asyncio
    async def test_get_message_stats_with_data(
        self, authenticated_client: tuple, test_db_session: AsyncSession
    ):
        """测试获取包含数据的统计信息"""
        test_client, token = authenticated_client

        # 创建不同类型和设备的消息
        messages = [
            Message.create_text_message("消息1", "device_A"),
            Message.create_text_message("消息2", "device_A"),
            Message.create_text_message("消息3", "device_B"),
        ]
        for msg in messages:
            test_db_session.add(msg)
        await test_db_session.commit()

        response = await test_client.get("/api/messages/stats/summary")

        assert response.status_code == 200
        stats = response.json()
        assert stats["total_messages"] == 3
        assert stats["today_messages"] == 3
        assert stats["type_stats"]["text"] == 3
        assert stats["device_stats"]["device_A"] == 2
        assert stats["device_stats"]["device_B"] == 1


class TestMessageDisplay:
    """消息显示相关测试"""

    @pytest.mark.asyncio
    async def test_message_display_content(
        self, authenticated_client: tuple, test_db_session: AsyncSession
    ):
        """测试消息显示内容"""
        test_client, token = authenticated_client

        # 创建文本消息
        message = Message.create_text_message("测试显示内容", "test_device")
        test_db_session.add(message)
        await test_db_session.commit()
        await test_db_session.refresh(message)

        # 获取消息
        response = await test_client.get(f"/api/messages/{message.id}")

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["display_content"] == "测试显示内容"
