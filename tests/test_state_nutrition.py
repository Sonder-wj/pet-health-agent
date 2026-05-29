"""AgentState / PetProfile 结构契约测试。"""
from app.agent.state import AgentState, PetProfile


def test_pet_profile_accepts_nutrition_fields():
    p: PetProfile = {
        "species": "dog",
        "weight_kg": 10.0,
        "age_months": 36,
        "neutered": True,
        "conditions": ["kidney"],
        "allergens": ["chicken"],
    }
    assert p["species"] == "dog"
    assert p["conditions"] == ["kidney"]


def test_pet_profile_total_false_allows_partial():
    # total=False → 字段全 optional,空 dict 也合法
    partial: PetProfile = {"species": "cat"}
    assert partial["species"] == "cat"


def test_agent_state_has_nutrition_fields():
    ann = AgentState.__annotations__
    expected = {
        "messages", "pet_profile", "diet_input", "label_image_path",
        "assessment", "tool_results", "iteration_count",
        "final_response", "report_md",
    }
    missing = expected - set(ann.keys())
    assert not missing, f"AgentState 缺字段: {missing}"


def test_agent_state_no_legacy_medical_fields():
    """旧医疗向字段必须全部移除,Plan 2 重构的关键防回归。"""
    ann = AgentState.__annotations__
    forbidden = {
        "triage_level", "pending_question", "awaiting_user_input",
        "visit_summary", "image_path", "already_triaged",
        "symptom_history", "collected_symptoms",
    }
    leaked = forbidden & set(ann.keys())
    assert not leaked, f"旧医疗字段未删: {leaked}"


def test_agent_state_runtime_construction():
    """运行时按新字段构造 state — 防止 TypedDict 注解与实际使用脱节。"""
    state: AgentState = {
        "messages": [],
        "pet_profile": {"species": "dog", "weight_kg": 10.0},
        "diet_input": {"items": [{"name": "chicken_breast_cooked", "amount_g": 200}]},
        "tool_results": {},
        "iteration_count": 0,
        "final_response": None,
        "assessment": None,
        "report_md": None,
        "label_image_path": None,
    }
    assert state["pet_profile"]["weight_kg"] == 10.0
    assert state["diet_input"]["items"][0]["amount_g"] == 200
