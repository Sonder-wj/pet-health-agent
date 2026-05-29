import pytest

from app.engine.evaluate import assess
from app.engine.models import DietTotals, Severity
from app.engine.nutrient_analysis import analyze_homemade, analyze_label


def test_homemade_allmeat_low_calcium_flagged():
    profile = {"species": "dog", "weight_kg": 10, "age_months": 36, "neutered": True}
    diet = analyze_homemade([{"name": "chicken_breast_cooked", "amount_g": 300}])
    result = assess(profile, diet)
    assert any(f.nutrient == "calcium" and f.severity == Severity.CRITICAL for f in result.findings)
    assert any(f.code == "ca_p_ratio_inverted" for f in result.findings)


def test_kidney_cat_high_phosphorus_flagged():
    profile = {"species": "cat", "weight_kg": 4, "age_months": 60, "neutered": True, "conditions": ["kidney"]}
    diet = DietTotals(kcal=240, nutrients={"phosphorus_mg": 720, "calcium_mg": 900,
                                           "taurine_mg": 80, "protein_g": 40}, ingredient_names=[])
    result = assess(profile, diet)
    assert any(f.nutrient == "phosphorus" and f.severity == Severity.CRITICAL for f in result.findings)


def test_homemade_cat_taurine_deficiency_flagged():
    profile = {"species": "cat", "weight_kg": 4, "age_months": 36, "neutered": True}
    diet = DietTotals(kcal=240, nutrients={"taurine_mg": 0.0, "protein_g": 40, "fat_g": 15,
                                           "calcium_mg": 360, "phosphorus_mg": 300}, ingredient_names=[])
    result = assess(profile, diet)
    assert any(f.nutrient == "taurine" for f in result.findings)


def test_balanced_dog_diet_no_critical_findings():
    profile = {"species": "dog", "weight_kg": 10, "age_months": 36, "neutered": True}
    diet = DietTotals(kcal=630, nutrients={
        "protein_g": 50, "fat_g": 20, "carb_g": 30, "fiber_g": 5,
        "calcium_mg": 900, "phosphorus_mg": 700, "sodium_mg": 200,
    }, ingredient_names=["balanced_mix"])
    result = assess(profile, diet)
    assert all(f.severity != Severity.CRITICAL for f in result.findings)


def test_overfeeding_flagged_and_mer_correct():
    profile = {"species": "dog", "weight_kg": 10, "age_months": 36, "neutered": True}
    diet = DietTotals(kcal=1200, nutrients={"calcium_mg": 1800, "phosphorus_mg": 1400}, ingredient_names=[])
    result = assess(profile, diet)
    assert any(f.code == "overfeeding" for f in result.findings)
    assert result.energy.mer == pytest.approx(630, abs=2)
    assert result.energy.intake_kcal == 1200


def test_allergen_conflict_flagged():
    profile = {"species": "dog", "weight_kg": 10, "age_months": 36, "neutered": True, "allergens": ["chicken"]}
    diet = analyze_homemade([{"name": "chicken_breast_cooked", "amount_g": 200}])
    result = assess(profile, diet)
    assert any(f.code == "allergen_conflict" for f in result.findings)


def test_commercial_label_diet_skips_missing_minerals():
    profile = {"species": "cat", "weight_kg": 4, "age_months": 36, "neutered": True}
    label = {"crude_protein_pct": 32, "crude_fat_pct": 14, "crude_fiber_pct": 3,
             "moisture_pct": 10, "kcal_per_kg": 4000}
    diet = analyze_label(label, amount_g=60)
    result = assess(profile, diet)
    nutrient_names = {f.nutrient for f in result.findings}
    assert "calcium" not in nutrient_names
    assert "taurine" not in nutrient_names
