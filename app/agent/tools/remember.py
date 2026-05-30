"""remember 工具 — Agent 把跨 thread 值得记住的事实写入 UserMemory。

什么该记?
- 用户偏好:"主人偏好天然/进口品牌"
- 硬约束:"主人每月猫粮预算 500 元"
- 兽医指示:"兽医叮嘱不要给糖尿病猫吃高 GI 食物"
- 历史:"旺财之前吃 XX 牌过敏过"

什么不该记?
- 单次评估结果(已在 assessment 里)
- 客观体重 / 月龄(放 Pet 表,不要复制)
- 临时计算结果
"""
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from app.core.database import AsyncSessionLocal
from app.core.logger import get_logger
from app.models.user_memory import UserMemory

logger = get_logger(service="tool.remember")


@tool
async def remember(
    content: str,
    category: str = "general",
    pet_id: int | None = None,
    config: RunnableConfig = None,
) -> dict:
    """把一条值得跨对话记住的事实写入用户长期记忆。

    Args:
        content: 要记住的事实,1 句话内,中文。例如:"主人每月猫粮预算 500 元"
        category: 类别,在 [preference, constraint, history, veterinary, general] 中选
        pet_id: 如果这条事实只跟某只宠物相关,传它的 id(可从系统提示里的 user_pets 取)
    """
    user_id = (config or {}).get("configurable", {}).get("user_id")
    if not user_id:
        return {"status": "error", "message": "未登录,无法保存记忆"}
    if not content or not content.strip():
        return {"status": "error", "message": "content 不能为空"}

    try:
        async with AsyncSessionLocal() as session:
            mem = UserMemory(
                user_id=user_id,
                pet_id=pet_id,
                content=content.strip(),
                category=category or "general",
            )
            session.add(mem)
            await session.commit()
            await session.refresh(mem)
            logger.info(f"Memory saved: user_id={user_id}, category={category}, id={mem.id}")
            return {"status": "ok", "memory_id": mem.id}
    except Exception as e:
        logger.error(f"remember failed: {e}")
        return {"status": "error", "message": f"记忆保存失败: {e}"}
