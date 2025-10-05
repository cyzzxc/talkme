"""
认证相关API
提供简单的密码验证功能
"""

from datetime import datetime, UTC
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from ..config import settings

router = APIRouter(prefix="/api/auth", tags=["认证"])
security = HTTPBearer()


class LoginRequest(BaseModel):
    """登录请求模型"""
    password: str


class LoginResponse(BaseModel):
    """登录响应模型"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600  # 1小时


class TokenData(BaseModel):
    """令牌数据模型"""
    password: Optional[str] = None
    exp: Optional[datetime] = None


# 简单的令牌存储（生产环境应使用更安全的方式）
_valid_tokens = set()


def create_access_token(password: str) -> str:
    """
    创建访问令牌
    """
    import secrets

    # 生成随机令牌
    token = secrets.token_urlsafe(32)

    # 将令牌加入有效令牌集合
    _valid_tokens.add(token)

    return token


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> bool:
    """
    验证访问令牌
    """
    token = credentials.credentials

    if token not in _valid_tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的访问令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return True


def verify_password(password: str) -> bool:
    """
    验证密码
    """
    return password == settings.APP_SECRET


@router.post("/login", response_model=LoginResponse, summary="用户登录")
async def login(request: LoginRequest):
    """
    用户登录
    验证密码并返回访问令牌
    """
    if not verify_password(request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 创建访问令牌
    access_token = create_access_token(request.password)

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=3600
    )


@router.post("/logout", summary="用户登出")
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    用户登出
    使令牌失效
    """
    token = credentials.credentials

    # 从有效令牌集合中移除
    _valid_tokens.discard(token)

    return {"message": "登出成功"}


@router.get("/verify", summary="验证令牌")
async def verify_auth(authenticated: bool = Depends(verify_token)):
    """
    验证当前令牌是否有效
    """
    return {"authenticated": True, "message": "令牌有效"}


@router.get("/status", summary="认证状态")
async def auth_status():
    """
    获取认证状态信息
    不需要认证即可访问
    """
    return {
        "auth_required": settings.APP_SECRET != "changeme",
        "active_sessions": len(_valid_tokens),
        "server_time": datetime.now(UTC).isoformat()
    }


# 依赖项：需要认证的路由使用
def require_auth(authenticated: bool = Depends(verify_token)) -> bool:
    """
    认证依赖项
    在需要认证的路由中使用
    """
    return authenticated


# 可选认证依赖项：某些接口可能需要
def optional_auth(credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))) -> Optional[bool]:
    """
    可选认证依赖项
    如果提供了令牌则验证，否则返回None
    """
    if credentials is None:
        return None

    try:
        token = credentials.credentials
        return token in _valid_tokens
    except Exception:
        return False