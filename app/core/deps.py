"""FastAPI 依赖注入：获取当前用户"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from app.core.auth import decode_token
from app.core.database import AsyncSessionLocal
from app.models.user import User

security = HTTPBearer(auto_error=False)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> User | None:
    """可选认证：返回用户对象或 None（用于既允许匿名又允许登录的端点，如健康检查等）。"""
    if credentials is None:
        return None
    user_id = decode_token(credentials.credentials)
    if user_id is None:
        return None
    async with AsyncSessionLocal() as session:
        r = await session.execute(select(User).where(User.id == user_id))
        return r.scalar_one_or_none()


async def require_user(
    user: User | None = Depends(get_current_user),
) -> User:
    """强制认证：未登录 / token 无效直接 401。

    所有涉及个人数据(聊天、历史)的端点必须用这个,不能用 get_current_user。
    否则匿名请求会 fallback 到某个默认 user_id,导致多账号数据混淆。
    """
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
