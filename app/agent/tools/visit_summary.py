from datetime import datetime

from langchain_core.tools import tool


@tool
def generate_visit_summary(
    pet_profile: dict,
    triage_result: dict | None = None,
    knowledge_results: dict | None = None,
    image_results: dict | None = None,
    symptom_collection: list | None = None,
) -> dict:
    """生成结构化的就诊摘要，方便用户出示给兽医。

    Args:
        pet_profile: 宠物信息 {name, species, breed, age, weight_kg}
        triage_result: 紧急分诊结果
        knowledge_results: 知识库检索结果
        image_results: 图片分析结果
        symptom_collection: 收集到的症状列表
    """
    summary_lines = [
        "# 宠物就诊摘要",
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## 宠物信息",
        f"- 名字：{pet_profile.get('name', '未提供')}",
        f"- 种类：{pet_profile.get('species', '未提供')}",
        f"- 品种：{pet_profile.get('breed', '未提供')}",
        f"- 年龄：{pet_profile.get('age', '未提供')}",
        f"- 体重：{pet_profile.get('weight_kg', '未提供')}kg",
        "",
    ]

    if symptom_collection:
        summary_lines.append("## 症状记录")
        summary_lines.append("")
        for item in symptom_collection:
            if isinstance(item, dict):
                summary_lines.append(f"- {item.get('field', '症状')}：{item.get('value', '未记录')}")
        summary_lines.append("")

    if triage_result:
        level_map = {
            "home_care": "🏠 居家护理",
            "schedule_visit": "🏥 建议就诊",
            "er_now": "🚨 立即就医",
        }
        summary_lines.append("## 紧急评估")
        summary_lines.append(f"- 等级：{level_map.get(triage_result.get('level', ''), triage_result.get('level', ''))}")
        summary_lines.append(f"- 判断依据：{triage_result.get('reasoning', '')}")
        if triage_result.get("matched_red_flags"):
            summary_lines.append("- 匹配的危险信号：")
            for flag in triage_result["matched_red_flags"]:
                summary_lines.append(f"  - {flag}")
        summary_lines.append("")

    if image_results and image_results.get("raw_analysis"):
        summary_lines.append("## 图片分析")
        summary_lines.append(image_results["raw_analysis"])
        summary_lines.append("")

    if knowledge_results and knowledge_results.get("general_advice"):
        summary_lines.append("## 参考信息")
        summary_lines.append(knowledge_results["general_advice"])
        summary_lines.append("")

    summary_lines.extend([
        "## 免责声明",
        "本摘要由AI生成，仅供参考，不能替代兽医的专业诊断。",
        "如宠物出现紧急状况，请立即前往最近的宠物医院。",
    ])

    return {
        "summary_markdown": "\n".join(summary_lines),
        "triage_level": triage_result.get("level") if triage_result else None,
        "generated_at": datetime.now().isoformat(),
    }
