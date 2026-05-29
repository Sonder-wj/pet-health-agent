from app.agent.tools.knowledge import _fallback


class TestKnowledgeFallback:
    def test_vomit_keywords(self):
        for kw in ["吐", "呕吐"]:
            result = _fallback(kw, "狗")
            assert "呕吐" in result["general_advice"]
            assert result["source"] == "fallback"
            assert result["species"] == "狗"

    def test_diarrhea_keywords(self):
        for kw in ["腹泻", "拉稀"]:
            result = _fallback(kw, "猫")
            assert "腹泻" in result["general_advice"]

    def test_skin_keywords(self):
        for kw in ["皮肤", "痒", "掉毛", "红疹"]:
            result = _fallback(kw, "狗")
            assert "皮肤问题" in result["general_advice"]

    def test_appetite_loss_keywords(self):
        for kw in ["不吃", "拒食"]:
            result = _fallback(kw, "猫")
            assert "拒食" in result["general_advice"]

    def test_respiratory_keywords(self):
        for kw in ["咳嗽", "喷嚏", "呼吸"]:
            result = _fallback(kw, "狗")
            assert "呼吸道" in result["general_advice"]

    def test_unknown_symptom_returns_general_advice(self):
        result = _fallback("腿有点瘸", "狗")
        assert "建议密切观察" in result["general_advice"]
        assert result["source"] == "fallback"

    def test_species_in_general_advice(self):
        result = _fallback("不吃东西了", "猫")
        adv = result["general_advice"]
        assert "猫" in adv

    def test_species_in_unknown_advice(self):
        result = _fallback("something weird", "狗")
        assert "狗" in result["general_advice"]

    def test_case_insensitive_match(self):
        result = _fallback("我家狗吐了", "狗")
        assert result["source"] == "fallback"
        assert "呕吐" in result["general_advice"]

    def test_message_field_indicates_unavailable_kb(self):
        result = _fallback("咳嗽", "猫")
        assert "知识库不可用" in result["message"]
        assert "通用护理建议" in result["message"]
