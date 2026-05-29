from app.engine.constraints import apply_constraints


def _base_cat_reqs():
    return {
        "protein_g": {"min": 65},
        "phosphorus_mg": {"min": 1250},
        "sodium_mg": {"min": 200},
        "taurine_mg": {"min": 250},
        "ca_p_ratio": {"min": 1.0, "max": 2.0},
    }


def test_no_conditions_returns_unchanged():
    reqs = _base_cat_reqs()
    out, triggered = apply_constraints(reqs, [])
    assert out == reqs
    assert triggered == []


def test_kidney_adds_phosphorus_max_and_lowers_min():
    out, triggered = apply_constraints(_base_cat_reqs(), ["kidney"])
    assert out["phosphorus_mg"]["max"] == 1200
    assert out["phosphorus_mg"]["min"] == 500
    assert out["sodium_mg"]["max"] == 1000
    assert "kidney" in triggered


def test_apply_constraints_does_not_mutate_input():
    reqs = _base_cat_reqs()
    apply_constraints(reqs, ["kidney"])
    assert "max" not in reqs["phosphorus_mg"]


def test_obesity_sets_fat_max_and_fiber_min():
    out, triggered = apply_constraints({"fat_g": {"min": 22.5}}, ["obesity"])
    assert out["fat_g"]["max"] == 30
    assert out["fiber_g"]["min"] == 15
    assert "obesity" in triggered


def test_unknown_condition_ignored():
    out, triggered = apply_constraints(_base_cat_reqs(), ["lycanthropy"])
    assert triggered == []
