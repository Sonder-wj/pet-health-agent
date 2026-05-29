import pytest

from app.engine.data_loader import load_dataset, load_mer_factors
from app.engine.models import Finding, Severity


def test_load_dataset_returns_data_section():
    data = load_dataset("mer_factors")
    assert "dog" in data
    assert "cat" in data
    assert data["cat"]["neutered_adult"] == 1.2


def test_load_dataset_requires_provenance(tmp_path, monkeypatch):
    bad = tmp_path / "bad.json"
    bad.write_text('{"data": {"x": 1}}', encoding="utf-8")
    monkeypatch.setattr("app.engine.data_loader.DATA_DIR", tmp_path)
    with pytest.raises(ValueError, match="provenance"):
        load_dataset("bad")


def test_load_mer_factors_helper():
    factors = load_mer_factors()
    assert factors["dog"]["weight_loss"] == 1.0


def test_finding_dataclass_defaults():
    f = Finding(code="x", nutrient="calcium", severity=Severity.CRITICAL, message="m")
    assert f.actual is None
    assert f.severity == "critical"
