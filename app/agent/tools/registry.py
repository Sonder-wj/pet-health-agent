"""绑定到 agent_node 的工具集合 — 宠物营养评估方向。"""
from app.agent.tools.assess_nutrition import assess_nutrition
from app.agent.tools.compute_energy import compute_energy_requirement
from app.agent.tools.extract_label import extract_label_nutrition
from app.agent.tools.final_answer import final_answer
from app.agent.tools.list_pets import list_pets
from app.agent.tools.lookup_ingredient import lookup_ingredient
from app.agent.tools.remember import remember
from app.agent.tools.save_pet_profile import save_pet_profile

ALL_TOOLS = [
    extract_label_nutrition,
    lookup_ingredient,
    compute_energy_requirement,
    assess_nutrition,
    save_pet_profile,
    list_pets,
    remember,
    final_answer,
]

TOOL_BY_NAME = {tool.name: tool for tool in ALL_TOOLS}
