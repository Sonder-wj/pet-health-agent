"""认证 API：注册 / 登录"""
from fastapi import APIRouter, Form, HTTPException
from sqlalchemy import select

from app.core.auth import create_access_token, hash_password, verify_password
from app.core.database import AsyncSessionLocal
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(
    username: str = Form(..., min_length=2, max_length=50),
    email: str = Form(..., max_length=100),
    password: str = Form(..., min_length=6, max_length=100),
):
    async with AsyncSessionLocal() as session:
        # 检查用户名/邮箱是否已存在
        r = await session.execute(select(User).where(User.username == username))
        if r.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="用户名已被注册")

        r = await session.execute(select(User).where(User.email == email))
        if r.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="邮箱已被注册")

        user = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        token = create_access_token(user.id)  # type: ignore[arg-type]
        return {
            "token": token,
            "user": {"id": user.id, "username": user.username, "email": user.email},
        }


@router.post("/login")
async def login(
    username: str = Form(...),
    password: str = Form(...),
):
    async with AsyncSessionLocal() as session:
        r = await session.execute(select(User).where(User.username == username))
        user = r.scalar_one_or_none()

        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        token = create_access_token(user.id)  # type: ignore[arg-type]
        return {
            "token": token,
            "user": {"id": user.id, "username": user.username, "email": user.email},
        }
