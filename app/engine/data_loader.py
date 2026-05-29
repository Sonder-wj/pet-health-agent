import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

_REQUIRED_PROVENANCE = ("source", "version", "review_date")
_cache: dict[str, dict] = {}


def load_dataset(name: str) -> dict:
    """读取 data/<name>.json,校验 provenance,返回其 data 段。"""
    if name in _cache:
        return _cache[name]
    path = DATA_DIR / f"{name}.json"
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    missing = [k for k in _REQUIRED_PROVENANCE if k not in raw]
    if missing:
        raise ValueError(f"{name}.json 缺少 provenance 元信息: {missing}")
    data = raw.get("data")
    if data is None:
        raise ValueError(f"{name}.json 缺少 data 段")
    _cache[name] = data
    return data


def _clear_cache() -> None:
    _cache.clear()


def load_mer_factors() -> dict:
    return load_dataset("mer_factors")


def load_ingredients() -> dict:
    return load_dataset("ingredients")


def load_requirements() -> dict:
    return load_dataset("nutrient_requirements")


def load_disease_constraints() -> dict:
    return load_dataset("disease_constraints")


def load_allergens() -> dict:
    return load_dataset("allergens")
