import pytest

from app.engine.requirements import get_requirements, resolve_stage


def test_resolve_stage_growth_when_young():
    assert resolve_stage({"species": "dog", "age_months": 6}) == "growth"


def test_resolve_stage_adult_when_mature():
    assert resolve_stage({"species": "cat", "age_months": 36}) == "adult"


def test_resolve_stage_defaults_adult_when_age_unknown():
    assert resolve_stage({"species": "dog"}) == "adult"


def test_get_requirements_adult_dog_has_calcium_min():
    reqs = get_requirements("dog", "adult")
    assert reqs["calcium_mg"]["min"] == 1250
    assert reqs["phosphorus_mg"]["min"] == 1000
    assert reqs["ca_p_ratio"]["min"] == 1.0
    assert reqs["ca_p_ratio"]["max"] == 2.0


def test_get_requirements_adult_cat_has_taurine():
    reqs = get_requirements("cat", "adult")
    assert reqs["taurine_mg"]["min"] == 250
    assert reqs["protein_g"]["min"] == 65


def test_get_requirements_returns_copy_not_shared_reference():
    a = get_requirements("dog", "adult")
    a["calcium_mg"]["min"] = 999
    b = get_requirements("dog", "adult")
    assert b["calcium_mg"]["min"] == 1250


def test_get_requirements_unknown_raises():
    with pytest.raises(ValueError):
        get_requirements("hamster", "adult")
