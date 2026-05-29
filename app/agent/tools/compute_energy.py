"""能量需求计算工具 — 包装引擎 RER/MER 公式。"""
from langchain_core.tools import tool

from app.engine.energy import compute_mer, compute_rer, resolve_life_stage


@tool
async def compute_energy_requirement(
    species: str,
    weight_kg: float,
    age_months: int | None = None,
    neutered: bool = False,
    conditions: list[str] | None = None,
) -> dict:
    """计算宠物的能量需求（静息 RER 与维持 MER），用于判断饮食热量是否合适。

    Args:
        species: "dog" 或 "cat"
        weight_kg: 体重（千克）
        age_months: 月龄（影响幼年/老年判定，可选）
        neutered: 是否绝育
        conditions: 健康状况列表，如 ["obesity"] 会自动切到减脂方案
    """
    profile = {
        "species": species,
        "weight_kg": weight_kg,
        "age_months": age_months,
        "neutered": neutered,
    }
    try:
        rer = compute_rer(weight_kg)
        life_stage = resolve_life_stage(profile, conditions or [])
        mer = compute_mer(weight_kg, species, life_stage)
    except ValueError as e:
        return {"status": "error", "message": str(e)}
    return {
        "status": "ok",
        "rer": round(rer, 1),
        "mer": round(mer, 1),
        "life_stage": life_stage,
        "unit": "kcal/day",
    }
