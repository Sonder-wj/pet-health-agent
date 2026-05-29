import pytest

from app.engine.models import DietTotals
from app.engine.nutrient_analysis import analyze_homemade, analyze_label, atwater_kcal, to_dmb


def test_dmb_conversion():
    # 粗蛋白 10% as-fed,水分 78% → 干物质蛋白 45.5%
    assert to_dmb(10.0, moisture_pct=78.0) == pytest.approx(45.5, abs=0.1)


def test_dmb_dry_food_unchanged_when_zero_moisture():
    assert to_dmb(30.0, moisture_pct=0.0) == pytest.approx(30.0, abs=0.001)


def test_dmb_rejects_full_moisture():
    with pytest.raises(ValueError):
        to_dmb(10.0, moisture_pct=100.0)


def test_atwater_modified_factors():
    # 修正 Atwater:蛋白 3.5、脂肪 8.5、碳水 3.5 kcal/g
    assert atwater_kcal(protein_g=30, fat_g=10, carb_g=5) == pytest.approx(207.5, abs=0.01)


def test_analyze_homemade_scales_and_sums():
    db = {
        "chicken_breast_cooked": {
            "kcal": 165, "protein_g": 31.0, "fat_g": 3.6, "carb_g": 0.0,
            "calcium_mg": 15, "phosphorus_mg": 228, "taurine_mg": 18,
            "sodium_mg": 74, "fiber_g": 0.0,
        }
    }
    diet = analyze_homemade([{"name": "chicken_breast_cooked", "amount_g": 300}], db)
    assert isinstance(diet, DietTotals)
    assert diet.kcal == pytest.approx(495, abs=0.5)
    assert diet.nutrients["calcium_mg"] == pytest.approx(45, abs=0.5)
    assert diet.nutrients["phosphorus_mg"] == pytest.approx(684, abs=0.5)
    assert diet.ingredient_names == ["chicken_breast_cooked"]


def test_analyze_homemade_unknown_ingredient_raises():
    with pytest.raises(KeyError):
        analyze_homemade([{"name": "unicorn_meat", "amount_g": 100}], {})


def test_analyze_homemade_uses_real_data_default():
    # 不传 db → 走 data/ingredients.json,鸡胸肉必须存在
    diet = analyze_homemade([{"name": "chicken_breast_cooked", "amount_g": 100}])
    assert diet.kcal > 0
    assert diet.nutrients["phosphorus_mg"] > 0


def test_analyze_label_with_kcal():
    label = {"crude_protein_pct": 30, "crude_fat_pct": 12, "crude_fiber_pct": 4,
             "moisture_pct": 10, "kcal_per_kg": 3800}
    diet = analyze_label(label, amount_g=100)
    assert diet.kcal == pytest.approx(380, abs=0.5)
    assert diet.nutrients["protein_g"] == pytest.approx(30, abs=0.5)
    # NFE 碳水 = 100 - 30 - 12 - 4 - 10 - 8(默认灰分) = 36 → 36g/100g
    assert diet.nutrients["carb_g"] == pytest.approx(36, abs=0.5)


def test_analyze_label_without_kcal_uses_atwater():
    label = {"crude_protein_pct": 30, "crude_fat_pct": 12, "crude_fiber_pct": 4, "moisture_pct": 10}
    diet = analyze_label(label, amount_g=100)
    # Atwater: 3.5*30 + 8.5*12 + 3.5*36 = 333
    assert diet.kcal == pytest.approx(333, abs=0.5)
