from app.agent.tools.assess_nutrition import assess_nutrition


async def test_homemade_allmeat_flags_calcium_critical():
    # 300g 鸡胸 → 钙严重不足 + Ca:P 倒置
    out = await assess_nutrition.ainvoke({
        "profile": {"species": "dog", "weight_kg": 10, "age_months": 36, "neutered": True},
        "diet_input": {"items": [{"name": "chicken_breast_cooked", "amount_g": 300}]},
    })
    assert out["status"] == "ok"
    findings = out["findings"]
    assert any(f["nutrient"] == "calcium" and f["severity"] == "critical" for f in findings)
    assert any(f["code"] == "ca_p_ratio_inverted" for f in findings)


async def test_pre_aggregated_diet_with_kidney_constraint():
    out = await assess_nutrition.ainvoke({
        "profile": {
            "species": "cat", "weight_kg": 4, "age_months": 60,
            "neutered": True, "conditions": ["kidney"],
        },
        "diet_input": {
            "kcal": 240,
            "nutrients": {"phosphorus_mg": 720, "calcium_mg": 900,
                          "taurine_mg": 80, "protein_g": 40},
        },
    })
    assert out["status"] == "ok"
    assert any(
        f["nutrient"] == "phosphorus" and f["severity"] == "critical"
        for f in out["findings"]
    )


async def test_commercial_label_passes_through():
    out = await assess_nutrition.ainvoke({
        "profile": {"species": "cat", "weight_kg": 4, "age_months": 36, "neutered": True},
        "diet_input": {
            "label": {
                "crude_protein_pct": 32, "crude_fat_pct": 14,
                "crude_fiber_pct": 3, "moisture_pct": 10, "kcal_per_kg": 4000,
            },
            "amount_g": 60,
        },
    })
    assert out["status"] == "ok"
    assert out["energy"]["intake_kcal"] > 0
    # label-only diet 缺矿物质,不应触发 calcium/taurine finding
    nutrient_names = {f["nutrient"] for f in out["findings"]}
    assert "calcium" not in nutrient_names
    assert "taurine" not in nutrient_names


async def test_allergen_conflict_flagged():
    out = await assess_nutrition.ainvoke({
        "profile": {
            "species": "dog", "weight_kg": 10, "age_months": 36,
            "neutered": True, "allergens": ["chicken"],
        },
        "diet_input": {"items": [{"name": "chicken_breast_cooked", "amount_g": 200}]},
    })
    assert out["status"] == "ok"
    assert any(f["code"] == "allergen_conflict" for f in out["findings"])


async def test_malformed_diet_input_returns_error():
    out = await assess_nutrition.ainvoke({
        "profile": {"species": "dog", "weight_kg": 10},
        "diet_input": {"random_key": 42},
    })
    assert out["status"] == "error"
    assert "diet_input" in out["message"]


async def test_unknown_ingredient_returns_error():
    out = await assess_nutrition.ainvoke({
        "profile": {"species": "dog", "weight_kg": 10},
        "diet_input": {"items": [{"name": "unicorn_meat", "amount_g": 100}]},
    })
    assert out["status"] == "error"


async def test_assessment_structure():
    out = await assess_nutrition.ainvoke({
        "profile": {"species": "dog", "weight_kg": 10, "age_months": 36, "neutered": True},
        "diet_input": {
            "kcal": 630,
            "nutrients": {"protein_g": 50, "fat_g": 20, "calcium_mg": 900,
                          "phosphorus_mg": 700, "sodium_mg": 200},
        },
    })
    assert out["status"] == "ok"
    # 序列化结构: energy 是 dict, nutrients/findings 是 list[dict]
    assert isinstance(out["energy"], dict)
    assert "rer" in out["energy"] and "mer" in out["energy"]
    assert isinstance(out["nutrients"], list)
    assert isinstance(out["findings"], list)
