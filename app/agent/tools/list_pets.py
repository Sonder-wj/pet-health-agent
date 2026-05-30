"""list_pets 工具 — 查询当前用户已有的宠物档案。

通常不必让 LLM 显式调用 —— API 层在新 chat 启动时已经把档案预注入到 system message。
但保留这个工具供 LLM 在多轮中复查(例如用户说"我家旺财怎么样"时,从工具拿权威数据)。
"""
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.pet import Pet


@tool
async def list_pets(config: RunnableConfig = None) -> dict:
    """列出当前用户已保存的所有宠物档案。

    用户提到"我家狗" / "我家猫" / 具体名字但你不确定时调用,从权威数据源(DB)读档案,
    避免重复追问用户已经告诉过你的信息。
    """
    user_id = (config or {}).get("configurable", {}).get("user_id")
    if not user_id:
        return {"status": "error", "pets": [], "message": "未登录"}

    try:
        async with AsyncSessionLocal() as session:
            r = await session.execute(
                select(Pet).where(Pet.user_id == user_id).order_by(Pet.created_at)
            )
            pets = r.scalars().all()
            return {"status": "ok", "pets": [p.to_dict() for p in pets], "total": len(pets)}
    except Exception as e:
        return {"status": "error", "pets": [], "message": str(e)}
