from app.engine.data_loader import load_mer_factors

JUVENILE_MAX_MONTHS = 12
SENIOR_MIN_MONTHS = 84  # ~7 岁起按老年处理(Demo 简化,WSAVA 生命阶段)


def compute_rer(weight_kg: float) -> float:
    """静息能量需求 RER = 70 × (体重kg)^0.75。"""
    if weight_kg <= 0:
        raise ValueError("weight_kg 必须为正数")
    return 70 * (weight_kg ** 0.75)


def compute_mer(weight_kg: float, species: str, life_stage: str, factors: dict | None = None) -> float:
    """维持能量需求 MER = RER × 系数。factors 可注入,默认从数据加载。"""
    factors = factors if factors is not None else load_mer_factors()
    try:
        factor = factors[species][life_stage]
    except KeyError as e:
        raise ValueError(f"无 {species}/{life_stage} 的 MER 系数") from e
    return compute_rer(weight_kg) * factor


def resolve_life_stage(profile: dict, conditions: list[str] | None = None) -> str:
    """决定能量系数所用生理阶段(优先级:肥胖→幼年→老年→是否绝育)。"""
    conditions = conditions or []
    if "obesity" in conditions:
        return "weight_loss"
    age = profile.get("age_months")
    if age is not None:
        if age < JUVENILE_MAX_MONTHS:
            return "juvenile"
        if age >= SENIOR_MIN_MONTHS:
            return "senior"
    return "neutered_adult" if profile.get("neutered") else "intact_adult"
