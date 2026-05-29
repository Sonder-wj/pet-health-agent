import pytest

from app.agent.tools.compute_energy import compute_energy_requirement


async def test_neutered_cat_5kg_matches_engine():
    # RER = 70 × 5^0.75 ≈ 234, MER(neutered_adult) = RER × 1.2 ≈ 281
    out = await compute_energy_requirement.ainvoke(
        {"species": "cat", "weight_kg": 5.0, "age_months": 36, "neutered": True}
    )
    assert out["status"] == "ok"
    assert out["rer"] == pytest.approx(234, abs=1)
    assert out["mer"] == pytest.approx(281, abs=2)
    assert out["life_stage"] == "neutered_adult"


async def test_obesity_forces_weight_loss_stage():
    out = await compute_energy_requirement.ainvoke(
        {
            "species": "dog",
            "weight_kg": 10.0,
            "age_months": 36,
            "neutered": True,
            "conditions": ["obesity"],
        }
    )
    assert out["status"] == "ok"
    assert out["life_stage"] == "weight_loss"
    # MER(weight_loss, dog) = RER × 1.0
    assert out["mer"] == pytest.approx(out["rer"], abs=0.5)


async def test_invalid_weight_returns_error():
    out = await compute_energy_requirement.ainvoke({"species": "dog", "weight_kg": 0})
    assert out["status"] == "error"
    assert "weight" in out["message"].lower() or "正数" in out["message"]


async def test_unknown_species_returns_error():
    out = await compute_energy_requirement.ainvoke({"species": "hamster", "weight_kg": 1.0})
    assert out["status"] == "error"
