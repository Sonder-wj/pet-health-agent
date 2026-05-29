from app.agent.tools.final_answer import final_answer
from app.agent.tools.image_analysis import analyze_pet_image
from app.agent.tools.knowledge import search_pet_knowledge
from app.agent.tools.medication import medication_guide
from app.agent.tools.symptom_collect import collect_symptoms
from app.agent.tools.symptom_track import track_symptoms
from app.agent.tools.visit_summary import generate_visit_summary

ALL_TOOLS = [
    collect_symptoms,
    analyze_pet_image,
    search_pet_knowledge,
    medication_guide,
    track_symptoms,
    generate_visit_summary,
    final_answer,
]

TOOL_BY_NAME = {tool.name: tool for tool in ALL_TOOLS}
