import copy

from app.engine.data_loader import load_disease_constraints


def apply_constraints(reqs: dict, conditions: list[str], db: dict | None = None) -> tuple[dict, list[str]]:
    """按疾病覆盖需求目标(min/max 逐键合并)。返回(调整后需求, 触发的疾病码)。"""
    data = db if db is not None else load_disease_constraints()
    out = copy.deepcopy(reqs)
    triggered: list[str] = []
    for cond in conditions:
        overrides = data.get(cond)
        if not overrides:
            continue
        triggered.append(cond)
        for nutrient, bounds in overrides.items():
            target = out.setdefault(nutrient, {})
            for bound_key, value in bounds.items():
                target[bound_key] = value
    return out, triggered
