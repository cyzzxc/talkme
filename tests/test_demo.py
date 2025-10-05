import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from unittest.mock import patch

@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)

@pytest.fixture
def authenticated_client():
    """创建已认证的测试客户端"""
    client = TestClient(app)
    
    # 先登录获取token
    with patch.object(settings, 'APP_SECRET', 'test_password'):
        login_response = client.post(
            "/api/auth/login",
            json={"password": "test_password"}
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # 设置认证头
        client.headers.update({"Authorization": f"Bearer {token}"})
        
        return client

class TestMessages:
    def test_send_text_message_success(self, authenticated_client: TestClient):
        """测试成功发送文本消息"""
        message_data = {
            "content": "这是一条测试消息",
            "device_id": "test_device_001"
        }
        response = authenticated_client.post("/api/messages/text", json=message_data)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["content"] == "这是一条测试消息"