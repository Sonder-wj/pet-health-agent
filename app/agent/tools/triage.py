"""紧急分诊 — LLM 判断 + 关键词硬兜底"""
from langchain_openai import ChatOpenAI

from app.core.config import settings

# 硬兜底关键词：命中任一条直接锁定 er_now，不经过 LLM
HARD_RED_FLAGS = [
    "抽搐", "便血", "大出血", "中毒", "意识模糊", "昏迷",
    "呼吸困难", "无法站立", "眼球震颤", "吐血", "误食",
]

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            base_url=settings.OPENAI_BASE_URL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0.1,
        )
    return _llm


def _check_hard_flags(text: str) -> list[str]:
    return [f for f in HARD_RED_FLAGS if f in text]


async def run_triage(
    species: str,
    symptoms: str,
    duration: str = "",
    additional_info: str = "",
) -> dict:
    """LLM 分诊：判断紧急程度。

    先用硬关键词兜底（抽搐/便血等直接 er_now），
    否则让 LLM 根据症状描述判断。
    """
    full_text = f"{symptoms} {duration} {additional_info}".lower()
    hard_matches = _check_hard_flags(full_text)
    if hard_matches:
        return {
            "level": "er_now",
            "reasoning": f"命中危险信号：{'、'.join(hard_matches)}",
            "matched_red_flags": hard_matches,
            "watch_signs": [
                "精神变差或萎靡不振",
                "症状加重或出现新的症状",
                "完全不吃不喝超过12小时",
            ],
            "source": "hard_rule",
        }

    llm = _get_llm()
    prompt = f"""你是一位急诊兽医分诊助手。根据以下信息判断就诊紧急程度。

物种：{species}
症状：{symptoms}
持续时间：{duration or '未提供'}
补充信息：{additional_info or '无'}

请判断紧急等级，仅回复一个JSON对象：
{{"level": "home_care|schedule_visit|er_now", "reasoning": "判断依据(中文，一句话)"}}

分级标准：
- er_now：危及生命的紧急情况，需立即就医（如呼吸困难、大出血、中毒、抽搐、意识丧失等）
- schedule_visit：需要就诊但不需急诊（如持续呕吐/腹泻>24h、拒食、明显疼痛但生命体征稳定等）
- home_care：轻症可居家观察护理

只回复JSON，不要其他内容。"""

    try:
        response = await llm.ainvoke(prompt)
        import json
        result = json.loads(response.content.strip())
        level = result.get("level", "schedule_visit")
        reasoning = result.get("reasoning", "LLM 判断完成")
    except Exception:
        # LLM 解析失败，保守处理
        level = "schedule_visit"
        reasoning = "分诊模型异常，保守建议就诊"

    watch_signs = [
        "精神变差或萎靡不振",
        "症状加重或出现新的症状",
        "完全不吃不喝超过12小时",
        "出现任何危险信号（呼吸困难、抽搐、便血等）",
    ]

    return {
        "level": level,
        "reasoning": reasoning,
        "matched_red_flags": [],
        "watch_signs": watch_signs,
        "source": "llm",
    }
