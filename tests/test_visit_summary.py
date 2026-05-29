from app.agent.tools.visit_summary import generate_visit_summary


class TestVisitSummary:
    def test_basic_summary_with_pet_profile(self):
        result = generate_visit_summary.invoke({
            "pet_profile": {"name": "旺财", "species": "狗", "breed": "金毛", "age": "3岁", "weight_kg": 28.0},
        })
        summary = result["summary_markdown"]
        assert "# 宠物就诊摘要" in summary
        assert "旺财" in summary
        assert "金毛" in summary
        assert "## 宠物信息" in summary
        assert "## 免责声明" in summary

    def test_summary_with_triage(self):
        result = generate_visit_summary.invoke({
            "pet_profile": {"name": "咪咪", "species": "猫", "breed": "英短", "age": "2岁", "weight_kg": 4.5},
            "triage_result": {"level": "schedule_visit", "reasoning": "持续呕吐超过24小时", "matched_red_flags": []},
        })
        summary = result["summary_markdown"]
        assert "建议就诊" in summary
        assert "持续呕吐超过24小时" in summary

    def test_summary_with_er_triage_and_red_flags(self):
        result = generate_visit_summary.invoke({
            "pet_profile": {"name": "豆豆", "species": "狗", "breed": "泰迪", "age": "5岁", "weight_kg": 6.0},
            "triage_result": {"level": "er_now", "reasoning": "呼吸困难", "matched_red_flags": ["呼吸困难", "吐血"]},
        })
        summary = result["summary_markdown"]
        assert "立即就医" in summary
        assert "呼吸困难" in summary
        assert "吐血" in summary

    def test_summary_with_symptoms(self):
        result = generate_visit_summary.invoke({
            "pet_profile": {"name": "小白", "species": "猫", "breed": "布偶", "age": "1岁", "weight_kg": 3.5},
            "symptom_collection": [
                {"field": "发病时间", "value": "昨天开始"},
                {"field": "症状频率", "value": "吐了3次"},
                {"field": "症状性状", "value": "黄色液体"},
            ],
        })
        summary = result["summary_markdown"]
        assert "## 症状记录" in summary
        assert "发病时间" in summary
        assert "昨天开始" in summary
        assert "黄色液体" in summary

    def test_summary_with_knowledge_fallback(self):
        result = generate_visit_summary.invoke({
            "pet_profile": {"name": "大黄", "species": "狗", "breed": "中华田园犬", "age": "4岁", "weight_kg": 15.0},
            "knowledge_results": {"general_advice": "禁食4-6小时后少量喂易消化食物"},
        })
        summary = result["summary_markdown"]
        assert "## 参考信息" in summary
        assert "禁食4-6小时" in summary

    def test_summary_with_image_analysis(self):
        result = generate_visit_summary.invoke({
            "pet_profile": {"name": ""},
            "image_results": {"raw_analysis": "左眼结膜充血，疑似结膜炎"},
        })
        summary = result["summary_markdown"]
        assert "## 图片分析" in summary
        assert "结膜炎" in summary

    def test_defaults_for_missing_pet_fields(self):
        result = generate_visit_summary.invoke({
            "pet_profile": {},
        })
        summary = result["summary_markdown"]
        assert "未提供" in summary

    def test_returns_triage_level_in_result(self):
        result = generate_visit_summary.invoke({
            "pet_profile": {},
            "triage_result": {"level": "home_care"},
        })
        assert result["triage_level"] == "home_care"

    def test_returns_none_triage_when_not_provided(self):
        result = generate_visit_summary.invoke({
            "pet_profile": {},
        })
        assert result["triage_level"] is None

    def test_has_generated_at_timestamp(self):
        result = generate_visit_summary.invoke({
            "pet_profile": {},
        })
        assert "generated_at" in result
        assert "T" in result["generated_at"]
