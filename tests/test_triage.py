"""测试分诊：LLM 判断 + 关键词硬兜底"""
import pytest

from app.agent.tools.triage import _check_hard_flags, run_triage


class TestHardFlags:
    def test_seizure_triggers_er_now(self):
        assert "抽搐" in _check_hard_flags("我家狗突然抽搐倒地")

    def test_bloody_stool_triggers_er_now(self):
        assert "便血" in _check_hard_flags("猫咪拉稀还有便血")

    def test_breathing_difficulty_triggers_er_now(self):
        assert "呼吸困难" in _check_hard_flags("狗呼吸困难喘不上气")

    def test_mild_symptom_no_hard_flag(self):
        assert _check_hard_flags("狗狗今天吐了一次精神还好") == []


class TestLLMTriage:
    @pytest.mark.asyncio
    async def test_mild_symptom_returns_home_care_or_schedule(self):
        result = await run_triage(
            species="狗",
            symptoms="今天吐了一次，精神不错，食欲正常",
        )
        assert result["level"] in ("home_care", "schedule_visit")

    @pytest.mark.asyncio
    async def test_severe_symptom_returns_er_now(self):
        result = await run_triage(
            species="狗",
            symptoms="突然倒地抽搐口吐白沫",
        )
        assert result["level"] == "er_now"
        assert result["source"] == "hard_rule"
        assert "抽搐" in result["matched_red_flags"]

    @pytest.mark.asyncio
    async def test_persistent_vomiting_returns_schedule(self):
        result = await run_triage(
            species="猫",
            symptoms="连续吐了两天",
            duration="两天",
        )
        assert result["level"] in ("schedule_visit", "er_now")

    @pytest.mark.asyncio
    async def test_eating_chocolate_triggers_er_now(self):
        result = await run_triage(
            species="狗",
            symptoms="吃了巧克力",
            additional_info="半小时前吃了一整板黑巧克力",
        )
        assert result["level"] in ("er_now", "schedule_visit")
