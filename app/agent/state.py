"""LangGraph Agent 状态 — 宠物营养评估方向。

字段职责:
- messages:          LangGraph 消息历史(必填)
- pet_profile:       宠物档案,Agent 在对话中收集
- diet_input:        用户提供的饮食描述(items / label / 已聚合三选一)
- label_image_path:  用户上传的包装照,extract_label_nutrition 工具消费
- assessment:        engine.assess() 返回的序列化结果
- tool_results:      工具调用的临时缓存(给前端/调试用)
- iteration_count:   ReAct 循环计数,防止无限调工具
- final_response:    final_answer 工具生成的最终回复,设置后终结循环
- report_md:         最终 Markdown 报告(可选,与 final_response 镜像)
"""
from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class PetProfile(TypedDict, total=False):
    """宠物档案 — 字段全 optional,Agent 渐进式收集。"""
    species: str           # "dog" | "cat"
    weight_kg: float
    age_months: int
    neutered: bool
    conditions: list[str]  # ["kidney", "obesity", ...]
    allergens: list[str]   # ["chicken", "beef", ...]
    name: str              # 仅显示用
    breed: str             # 仅显示用


class AgentState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    pet_profile: PetProfile
    diet_input: dict | None         # {items?: [...], label?: {...}, amount_g?, kcal?, nutrients?, ingredient_names?}
    label_image_path: str | None
    assessment: dict | None         # engine.NutritionAssessment 序列化结果
    tool_results: dict
    iteration_count: int
    final_response: str | None
    report_md: str | None
