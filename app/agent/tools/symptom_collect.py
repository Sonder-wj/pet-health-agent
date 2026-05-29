import json

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from app.core.config import settings

COLLECT_DIMENSIONS = [
    {
        "dimension": "onset",
        "field": "发病时间",
        "keywords": ["什么时候", "几天", "小时", "开始", "发现"],
        "question_template": "从什么时候开始出现这个情况的？已经持续多久了？",
    },
    {
        "dimension": "frequency",
        "field": "症状频率",
        "keywords": ["几次", "频繁", "一直", "偶尔", "反复", "持续"],
        "question_template": "这种情况发生了几次？是持续性的还是时好时坏？",
    },
    {
        "dimension": "character",
        "field": "症状性状",
        "keywords": ["什么样", "颜色", "吐", "拉", "泄", "血", "分泌物",
                     "味道", "臭", "痒", "抓", "舔", "肿块", "红", "肿"],
        "question_template": "能具体描述一下吗？比如颜色、形状、有没有异常分泌物？",
    },
    {
        "dimension": "accompanying",
        "field": "伴随症状",
        "keywords": ["精神", "食欲", "喝水", "尿", "发烧", "排便"],
        "question_template": "除了这个，还有其他不舒服吗？精神、食欲、喝水情况怎么样？",
    },
    {
        "dimension": "context",
        "field": "背景信息",
        "keywords": ["换粮", "出门", "接触", "疫苗", "驱虫", "最近", "环境"],
        "question_template": "最近有没有换过食物、去过新地方、或者接触过其他动物？",
    },
]

DIMENSION_NAMES = [d["dimension"] for d in COLLECT_DIMENSIONS]

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


def _keyword_match(symptoms: str) -> set:
    """关键词兜底：返回症状文本中已覆盖的维度名"""
    symptoms_lower = symptoms.lower()
    covered = set()
    for dim in COLLECT_DIMENSIONS:
        if any(kw in symptoms_lower for kw in dim["keywords"]):
            covered.add(dim["dimension"])
    return covered


async def _llm_detect_dimensions(symptoms: str) -> set:
    """LLM 判断症状文本中已覆盖的维度"""
    llm = _get_llm()
    dim_list = "、".join(f'"{d}"' for d in DIMENSION_NAMES)
    prompt = f"""用户描述的症状："{symptoms}"

请判断用户这段话中已经涉及了以下哪些维度，返回一个JSON数组（仅包含已涉及的维度名）：
可用维度：{dim_list}

维度含义：
- onset：发病时间/什么时候开始的
- frequency：频率/发生次数
- character：症状的具体性状（颜色、形态等）
- accompanying：伴随症状（精神、食欲等）
- context：背景信息（换粮、环境变化等）

仅返回JSON数组，如：["onset", "frequency"]"""

    try:
        response = await llm.ainvoke(prompt)
        text = response.content.strip()
        if text.startswith("```"):
            import re
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        detected = json.loads(text)
        if isinstance(detected, list):
            return set(detected)
    except Exception:
        pass

    # LLM 失败，fallback 到关键词
    return _keyword_match(symptoms)


async def _pick_next_dimension(asked: set, current_symptoms: str) -> dict | None:
    """选择下一个要追问的维度。优先用 LLM 判断已覆盖维度，关键词兜底。"""
    remaining = [d for d in COLLECT_DIMENSIONS if d["dimension"] not in asked]

    if not remaining:
        return None

    # LLM 判断已覆盖维度
    llm_covered = await _llm_detect_dimensions(current_symptoms)
    # 合并关键词结果（兜底）
    kw_covered = _keyword_match(current_symptoms)
    covered = llm_covered | kw_covered | asked

    # 第一个未被覆盖的维度
    for dim in COLLECT_DIMENSIONS:
        if dim["dimension"] not in covered:
            return dim

    # 全部覆盖了
    return None


@tool
async def collect_symptoms(
    collected_dimensions: list[str],
    species: str = "",
    current_symptoms: str = "",
) -> dict:
    """当信息不足时，向用户追问症状细节。每轮只追问一个维度。

    Args:
        collected_dimensions: 已经收集过的维度列表，如 ["onset", "frequency"]
        species: 宠物种类（猫/狗）
        current_symptoms: 用户当前描述的症状
    """
    asked = set(collected_dimensions or [])
    next_dimension = await _pick_next_dimension(asked, current_symptoms)

    if next_dimension is None:
        return {
            "status": "complete",
            "collected_dimensions": list(asked),
            "question": None,
        }

    question = next_dimension["question_template"]

    return {
        "status": "asking",
        "dimension": next_dimension["dimension"],
        "field": next_dimension["field"],
        "question": question,
        "collected_dimensions": list(asked),
    }
