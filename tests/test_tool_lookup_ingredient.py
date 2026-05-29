from app.agent.tools.lookup_ingredient import lookup_ingredient


async def test_english_key_hit():
    out = await lookup_ingredient.ainvoke({"query": "chicken_breast"})
    assert out["status"] == "ok"
    assert out["total"] >= 1
    assert any(h["name"] == "chicken_breast_cooked" for h in out["hits"])
    # 数据完整性: 命中项必须含 phosphorus_mg
    assert out["hits"][0]["phosphorus_mg"] > 0


async def test_chinese_alias_hit():
    out = await lookup_ingredient.ainvoke({"query": "鸡胸"})
    assert out["status"] == "ok"
    assert any("chicken" in h["name"] for h in out["hits"])


async def test_unknown_query_no_match():
    out = await lookup_ingredient.ainvoke({"query": "unicorn_meat"})
    assert out["status"] == "no_match"
    assert out["total"] == 0
    assert out["hits"] == []


async def test_empty_query_error():
    out = await lookup_ingredient.ainvoke({"query": "   "})
    assert out["status"] == "error"


async def test_max_results_cap():
    # 多关键词类的 "cooked" 命中很多项,但 max_results=2 应只返回 2 条
    out = await lookup_ingredient.ainvoke({"query": "cooked", "max_results": 2})
    assert out["total"] == 2
