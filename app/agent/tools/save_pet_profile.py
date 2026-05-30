"""save_pet_profile 工具 — 把 Agent 收集到的宠物档案落库,跨 thread 复用。

调用契约:
- 同一个用户下按 name 唯一,重复 save 走 upsert(覆盖字段)
- user_id 通过 RunnableConfig 从 thread_config.configurable 注入,
  LLM 看不到该参数,也不需要自己组装
"""
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.logger import get_logger
from app.models.pet import Pet

logger = get_logger(service="tool.save_pet_profile")


@tool
async def save_pet_profile(
    name: str,
    species: str,
    weight_kg: float,
    age_months: int | None = None,
    breed: str | None = None,
    neutered: bool | None = None,
    conditions: list[str] | None = None,
    allergens: list[str] | None = None,
    config: RunnableConfig = None,
) -> dict:
    """保存或更新一只宠物的档案到数据库,以后新对话能直接复用。

    用户首次提供宠物档案,或档案有变化(体重、疾病、过敏)时,**主动**调用此工具,
    不必等用户问"能不能保存"。同一个名字会覆盖,不会重复创建。

    Args:
        name: 宠物的名字(如 旺财、喵喵),必填且在同一用户下唯一
        species: "dog" 或 "cat"
        weight_kg: 体重 kg
        age_months: 月龄(可选)
        breed: 品种(可选,如 金毛、英短)
        neutered: 是否绝育
        conditions: 健康状况列表,如 ["kidney", "obesity"]
        allergens: 已知过敏原列表,如 ["chicken", "beef"]
    """
    user_id = (config or {}).get("configurable", {}).get("user_id")
    if not user_id:
        return {"status": "error", "message": "未登录,无法持久化档案"}

    try:
        async with AsyncSessionLocal() as session:
            r = await session.execute(
                select(Pet).where(Pet.user_id == user_id, Pet.name == name)
            )
            pet = r.scalar_one_or_none()

            if pet is None:
                pet = Pet(user_id=user_id, name=name, species=species, weight_kg=weight_kg)
                session.add(pet)
                action = "created"
            else:
                pet.species = species
                pet.weight_kg = weight_kg
                action = "updated"

            # 其他字段:只在传入时更新(不传 = 保留旧值)
            if breed is not None:
                pet.breed = breed
            if age_months is not None:
                pet.age_months = age_months
            if neutered is not None:
                pet.neutered = neutered
            if conditions is not None:
                pet.conditions = conditions
            if allergens is not None:
                pet.allergens = allergens

            await session.commit()
            await session.refresh(pet)
            logger.info(f"Pet {action}: user_id={user_id}, name={name}, id={pet.id}")
            return {"status": "ok", "action": action, "pet": pet.to_dict()}
    except Exception as e:
        logger.error(f"save_pet_profile failed: {e}")
        return {"status": "error", "message": f"档案保存失败: {e}"}
