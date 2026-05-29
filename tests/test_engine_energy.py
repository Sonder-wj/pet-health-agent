import pytest

from app.engine.energy import compute_mer, compute_rer, resolve_life_stage


def test_rer_neutered_cat_5kg():
    # RER = 70 × 5^0.75 ≈ 234
    assert compute_rer(5.0) == pytest.approx(234, abs=1)


def test_mer_neutered_cat_5kg():
    # MER = RER × 1.2 ≈ 281
    assert compute_mer(5.0, "cat", "neutered_adult") == pytest.approx(281, abs=2)


def test_rer_dog_10kg():
    # RER = 70 × 10^0.75 ≈ 394
    assert compute_rer(10.0) == pytest.approx(394, abs=1)


def test_mer_dog_10kg_neutered():
    assert compute_mer(10.0, "dog", "neutered_adult") == pytest.approx(630, abs=2)


def test_compute_mer_accepts_injected_factors():
    factors = {"dog": {"neutered_adult": 2.0}}
    assert compute_mer(10.0, "dog", "neutered_adult", factors) == pytest.approx(
        compute_rer(10.0) * 2.0, abs=0.01
    )


def test_resolve_life_stage_obesity_forces_weight_loss():
    profile = {"species": "dog", "age_months": 36, "neutered": True}
    assert resolve_life_stage(profile, ["obesity"]) == "weight_loss"


def test_resolve_life_stage_juvenile():
    profile = {"species": "cat", "age_months": 6, "neutered": False}
    assert resolve_life_stage(profile) == "juvenile"


def test_resolve_life_stage_senior():
    profile = {"species": "dog", "age_months": 96, "neutered": True}
    assert resolve_life_stage(profile) == "senior"


def test_resolve_life_stage_intact_vs_neutered_adult():
    assert resolve_life_stage({"species": "dog", "age_months": 36, "neutered": False}) == "intact_adult"
    assert resolve_life_stage({"species": "dog", "age_months": 36, "neutered": True}) == "neutered_adult"
