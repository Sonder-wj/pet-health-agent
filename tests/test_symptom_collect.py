"""测试症状追问：5 维度轮询"""
import pytest

from app.agent.tools.symptom_collect import (
    COLLECT_DIMENSIONS,
    _keyword_match,
    _pick_next_dimension,
    collect_symptoms,
)


class TestKeywordMatch:
    def test_detects_onset(self):
        assert "onset" in _keyword_match("狗从昨天开始吐")

    def test_detects_frequency(self):
        assert "frequency" in _keyword_match("吐了好几次了")

    def test_detects_character(self):
        assert "character" in _keyword_match("吐的是黄色液体")

    def test_detects_accompanying(self):
        assert "accompanying" in _keyword_match("没精神，也不吃东西")

    def test_detects_multiple(self):
        covered = _keyword_match("昨天开始吐了好几次，没精神")
        assert "onset" in covered
        assert "frequency" in covered
        assert "accompanying" in covered


class TestNextDimension:
    @pytest.mark.asyncio
    async def test_first_dimension(self):
        dim = await _pick_next_dimension(set(), "狗吐了")
        assert dim is not None

    @pytest.mark.asyncio
    async def test_skips_already_asked(self):
        dim = await _pick_next_dimension({"onset"}, "狗吐了")
        assert dim is not None
        assert dim["dimension"] != "onset"

    @pytest.mark.asyncio
    async def test_no_more_dimensions(self):
        asked = {d["dimension"] for d in COLLECT_DIMENSIONS}
        dim = await _pick_next_dimension(asked, "狗吐了")
        assert dim is None


class TestCollectSymptoms:
    @pytest.mark.asyncio
    async def test_first_call_asks_onset(self):
        result = await collect_symptoms.ainvoke({
            "collected_dimensions": [],
            "species": "狗",
            "current_symptoms": "吐了",
        })
        assert result["status"] == "asking"
        assert result["dimension"] == "onset"

    @pytest.mark.asyncio
    async def test_all_collected_returns_complete(self):
        result = await collect_symptoms.ainvoke({
            "collected_dimensions": ["onset", "frequency", "character", "accompanying", "context"],
            "species": "狗",
            "current_symptoms": "吐了",
        })
        assert result["status"] == "complete"

    @pytest.mark.asyncio
    async def test_asks_one_at_a_time(self):
        result = await collect_symptoms.ainvoke({
            "collected_dimensions": ["onset"],
            "species": "猫",
            "current_symptoms": "不吃东西",
        })
        assert result["status"] == "asking"
        assert isinstance(result["question"], str)
        assert len(result["question"]) > 0
