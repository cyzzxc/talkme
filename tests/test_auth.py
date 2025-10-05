"""
认证模块测试
测试认证相关的API功能
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.config import settings


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def valid_token():
    """模拟有效令牌"""
    return "test_token_123"


class TestAuth:
    """认证测试类"""

    def test_auth_status(self, client):
        """测试认证状态接口"""
        response = client.get("/api/auth/status")
        
        assert response.status_code == 200
        data = response.json()
        
        # 验证返回的字段
        assert "auth_required" in data
        assert "active_sessions" in data
        assert "server_time" in data
        
        # 验证数据类型
        assert isinstance(data["auth_required"], bool)
        assert isinstance(data["active_sessions"], int)
        assert isinstance(data["server_time"], str)

    def test_login_with_correct_password(self, client):
        """测试使用正确密码登录"""
        with patch.object(settings, 'APP_SECRET', 'test_password'):
            response = client.post(
                "/api/auth/login",
                json={"password": "test_password"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # 验证返回的字段
            assert "access_token" in data
            assert "token_type" in data
            assert "expires_in" in data
            
            # 验证字段值
            assert data["token_type"] == "bearer"
            assert data["expires_in"] == 3600
            assert len(data["access_token"]) > 0

    def test_login_with_wrong_password(self, client):
        """测试使用错误密码登录"""
        with patch.object(settings, 'APP_SECRET', 'test_password'):
            response = client.post(
                "/api/auth/login",
                json={"password": "wrong_password"}
            )
            
            assert response.status_code == 401
            data = response.json()
            assert "密码错误" in data["message"]

    def test_login_without_password(self, client):
        """测试不提供密码登录"""
        response = client.post("/api/auth/login", json={})
        
        assert response.status_code == 422  # 验证错误

    def test_verify_without_token(self, client):
        """测试不提供令牌验证"""
        response = client.get("/api/auth/verify")
        
        assert response.status_code == 403  # 未授权

    def test_verify_with_invalid_token(self, client):
        """测试使用无效令牌验证"""
        response = client.get(
            "/api/auth/verify",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "无效的访问令牌" in data["message"]

    def test_logout_without_token(self, client):
        """测试不提供令牌登出"""
        response = client.post("/api/auth/logout")
        
        assert response.status_code == 403  # 未授权

    # def test_logout_with_invalid_token(self, client):
    #     """测试使用无效令牌登出"""
    #     response = client.post(
    #         "/api/auth/logout",
    #         headers={"Authorization": "Bearer invalid_token"}
    #     )
    #     assert response.status_code == 401
    #     data = response.json()
    #     assert "无效的访问令牌" in data["message"]

    def test_complete_auth_flow(self, client):
        """测试完整的认证流程：登录 -> 验证 -> 登出"""
        with patch.object(settings, 'APP_SECRET', 'test_password'):
            # 1. 登录
            login_response = client.post(
                "/api/auth/login",
                json={"password": "test_password"}
            )
            
            assert login_response.status_code == 200
            token = login_response.json()["access_token"]
            
            # 2. 验证令牌
            verify_response = client.get(
                "/api/auth/verify",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert verify_response.status_code == 200
            verify_data = verify_response.json()
            assert verify_data["authenticated"] is True
            
            # 3. 登出
            logout_response = client.post(
                "/api/auth/logout",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert logout_response.status_code == 200
            logout_data = logout_response.json()
            assert "登出成功" in logout_data["message"]
            
            # 4. 验证令牌已失效
            verify_after_logout = client.get(
                "/api/auth/verify",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert verify_after_logout.status_code == 401
