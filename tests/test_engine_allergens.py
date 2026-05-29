from app.engine.allergens import check_allergens


def test_detects_conflict_via_alias():
    # 宠物对鸡过敏,饮食含 chicken_breast_cooked → 命中
    conflicts = check_allergens(["chicken_breast_cooked", "rice_white_cooked"], ["chicken"])
    assert "chicken" in conflicts


def test_no_conflict_when_clean():
    conflicts = check_allergens(["rice_white_cooked", "pumpkin_cooked"], ["chicken", "beef"])
    assert conflicts == []


def test_case_insensitive_and_chinese_alias():
    conflicts = check_allergens(["鸡胸肉"], ["chicken"])
    assert "chicken" in conflicts


def test_multiple_allergens():
    conflicts = check_allergens(["beef_liver_cooked", "egg_whole_cooked"], ["beef", "egg", "chicken"])
    assert set(conflicts) == {"beef", "egg"}


def test_unknown_allergen_label_ignored():
    conflicts = check_allergens(["chicken_breast_cooked"], ["plutonium"])
    assert conflicts == []
