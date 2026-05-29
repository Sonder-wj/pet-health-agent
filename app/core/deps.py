"""FastAPI 依赖注入：获取当前用户"""
from fastapi import Depends
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
    """从请求头提取 token，返回用户对象。无 token 时返回 None（允许匿名使用）。"""
    if credentials is None:
        return None
    user_id = decode_token(credentials.credentials)
    if user_id is None:
        return None
    async with AsyncSessionLocal() as session:
        r = await session.execute(select(User).where(User.id == user_id))
        return r.scalar_one_or_none()
