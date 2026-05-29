from app.engine.data_loader import load_allergens


def check_allergens(ingredient_names: list[str], pet_allergens: list[str], db: dict | None = None) -> list[str]:
    """比对饮食成分名 vs 宠物已知过敏原,返回命中的过敏原码(去重、保序)。"""
    data = db if db is not None else load_allergens()
    haystack = " ".join(ingredient_names).lower()
    conflicts: list[str] = []
    for allergen in pet_allergens:
        aliases = data.get(allergen)
        if not aliases:
            continue
        if any(alias.lower() in haystack for alias in aliases):
            if allergen not in conflicts:
                conflicts.append(allergen)
    return conflicts
