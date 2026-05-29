from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class PetProfile(TypedDict, total=False):
    name: str
    species: str          # 猫 / 狗 / 其他
    breed: str
    age: str
    weight_kg: float


class ToolResult(TypedDict, total=False):
    tool_name: str
    result: dict
    timestamp: str


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    pet_profile: PetProfile
    collected_symptoms: list       # [{symptom, onset, duration, severity, ...}]
    tool_results: dict            # {tool_name: result}
    triage_level: str | None      # home_care / schedule_visit / er_now
    pending_question: str | None  # 追问内容，前端展示
    awaiting_user_input: bool
    visit_summary: str | None
    image_path: str | None        # 用户上传的图片路径，供 analyze_pet_image 工具使用
    iteration_count: int
    final_response: str | None
    already_triaged: bool         # 是否已执行过分诊（避免 resume 时重复分诊）
    symptom_history: list         # 跨天症状追踪记录
