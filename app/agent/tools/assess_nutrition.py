"""营养评估主工具 — 唯一调用引擎 assess() 的入口。"""
from dataclasses import asdict

from langchain_core.tools import tool

from app.engine import assess
from app.engine.models import DietTotals
from app.engine.nutrient_analysis import analyze_homemade, analyze_label


def _build_diet(diet_input: dict) -> DietTotals:
    """根据 diet_input 的形态分派到引擎对应的聚合函数。

    支持三种形态:
      - 自制:   {"items": [{"name": ..., "amount_g": ...}, ...]}
      - 商品粮: {"label": {"crude_protein_pct": ..., ...}, "amount_g": 100}
      - 已聚合: {"kcal": ..., "nutrients": {...}, "ingredient_names": [...]}
    """
    if "items" in diet_input:
        return analyze_homemade(diet_input["items"])
    if "label" in diet_input:
        return analyze_label(diet_input["label"], diet_input.get("amount_g", 100.0))
    if "kcal" in diet_input and "nutrients" in diet_input:
        return DietTotals(
            kcal=diet_input["kcal"],
            nutrients=diet_input["nutrients"],
            ingredient_names=diet_input.get("ingredient_names", []),
        )
    raise ValueError("diet_input 必须含 items / label / kcal+nutrients 之一")


@tool
async def assess_nutrition(profile: dict, diet_input: dict) -> dict:
    """评估饮食是否满足宠物需求 — 完整调用引擎，包含能量、营养素、Ca:P、过敏原检查。

    Args:
        profile: 宠物档案；必填 species/weight_kg；可选 age_months/neutered/conditions/allergens
        diet_input: 饮食描述，三选一：
            - 自制：{"items": [{"name": "chicken_breast_cooked", "amount_g": 200}, ...]}
            - 商品粮：{"label": {"crude_protein_pct": 30, ...}, "amount_g": 100}
            - 已聚合：{"kcal": ..., "nutrients": {...}, "ingredient_names": [...]}
    """
    try:
        diet = _build_diet(diet_input)
    except (ValueError, KeyError) as e:
        return {"status": "error", "message": f"diet_input 解析失败: {e}"}

    try:
        result = assess(profile, diet)
    except (ValueError, KeyError) as e:
        return {"status": "error", "message": f"评估失败: {e}"}

    return {
        "status": "ok",
        "energy": asdict(result.energy),
        "nutrients": [asdict(n) for n in result.nutrients],
        "findings": [
            {**asdict(f), "severity": f.severity.value}
            for f in result.findings
        ],
    }
