from app.engine.data_loader import load_ingredients
from app.engine.models import DietTotals

_NUTRIENT_KEYS = (
    "protein_g", "fat_g", "carb_g",
    "calcium_mg", "phosphorus_mg", "taurine_mg", "sodium_mg", "fiber_g",
)


def to_dmb(value_pct: float, moisture_pct: float) -> float:
    """湿重百分比 → 干物质百分比(DMB)。"""
    if moisture_pct >= 100 or moisture_pct < 0:
        raise ValueError("moisture_pct 必须在 [0, 100)")
    return value_pct / (100 - moisture_pct) * 100


def atwater_kcal(protein_g: float, fat_g: float, carb_g: float) -> float:
    """修正 Atwater(宠物食品):蛋白 3.5、脂肪 8.5、碳水(NFE) 3.5 kcal/g。"""
    return 3.5 * protein_g + 8.5 * fat_g + 3.5 * carb_g


def analyze_homemade(items: list[dict], ingredient_db: dict | None = None) -> DietTotals:
    """自制饮食:逐食材查表 → 按份量缩放 → 跨食材加总。"""
    db = ingredient_db if ingredient_db is not None else load_ingredients()
    totals = {k: 0.0 for k in _NUTRIENT_KEYS}
    kcal = 0.0
    names: list[str] = []
    for item in items:
        name = item["name"]
        if name not in db:
            raise KeyError(f"食材库无此项: {name}")
        entry = db[name]
        scale = item["amount_g"] / 100.0
        kcal += entry.get("kcal", 0.0) * scale
        for k in _NUTRIENT_KEYS:
            totals[k] += entry.get(k, 0.0) * scale
        names.append(name)
    return DietTotals(kcal=kcal, nutrients=totals, ingredient_names=names)


def analyze_label(label: dict, amount_g: float, ash_pct: float = 8.0) -> DietTotals:
    """商品粮:从保证成分分析换算每份摄入;无 kcal 时用 Atwater 反推。"""
    scale = amount_g / 100.0
    protein_pct = label.get("crude_protein_pct", 0.0)
    fat_pct = label.get("crude_fat_pct", 0.0)
    fiber_pct = label.get("crude_fiber_pct", 0.0)
    moisture_pct = label.get("moisture_pct", 0.0)
    carb_pct = max(0.0, 100 - protein_pct - fat_pct - fiber_pct - moisture_pct - ash_pct)

    protein_g = protein_pct * scale
    fat_g = fat_pct * scale
    fiber_g = fiber_pct * scale
    carb_g = carb_pct * scale

    kcal_per_kg = label.get("kcal_per_kg")
    if kcal_per_kg is not None:
        kcal = kcal_per_kg / 1000.0 * amount_g
    else:
        kcal = atwater_kcal(protein_g, fat_g, carb_g)

    nutrients = {"protein_g": protein_g, "fat_g": fat_g, "carb_g": carb_g, "fiber_g": fiber_g}
    return DietTotals(kcal=kcal, nutrients=nutrients, ingredient_names=[])
