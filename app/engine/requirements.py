import copy

from app.engine.data_loader import load_requirements

GROWTH_MAX_MONTHS = 12


def resolve_stage(profile: dict) -> str:
    """需求阶段:幼年(<12 月)按 growth,否则 adult;年龄未知默认 adult。"""
    age = profile.get("age_months")
    if age is not None and age < GROWTH_MAX_MONTHS:
        return "growth"
    return "adult"


def get_requirements(species: str, stage: str, db: dict | None = None) -> dict:
    """返回该物种×阶段的营养需求(深拷贝,避免调用方污染数据)。"""
    data = db if db is not None else load_requirements()
    try:
        reqs = data[species][stage]
    except KeyError as e:
        raise ValueError(f"无 {species}/{stage} 的营养需求") from e
    return copy.deepcopy(reqs)
