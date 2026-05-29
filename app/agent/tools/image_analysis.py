import base64
import json
import re
from pathlib import Path

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from app.core.config import settings


def _parse_json_response(text: str) -> dict:
    """从 LLM 响应中提取 JSON，兼容 markdown 代码块包裹的情况。"""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


_vision_llm = None


def _get_vision_llm():
    global _vision_llm
    if _vision_llm is None:
        _vision_llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            base_url=settings.OPENAI_BASE_URL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0.3,
            model_kwargs={"response_format": {"type": "json_object"}},
        )
    return _vision_llm


@tool
async def analyze_pet_image(
    image_path: str,
    context: str = "",
) -> dict:
    """分析用户上传的宠物照片，识别可见的异常。

    Args:
        image_path: 图片文件路径
        context: 用户描述的症状上下文
    """
    path = Path(image_path)
    if not path.exists():
        return {"error": f"图片文件不存在: {image_path}"}

    with open(path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode()

    ext = path.suffix.lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
    mime_type = mime_map.get(ext, "image/jpeg")

    vision_llm = _get_vision_llm()

    system_prompt = (
        "你是一位兽医影像分析师。仔细查看宠物照片，识别可见的异常发现。"
        "关注皮肤、眼睛、耳朵、口腔、毛发、体态等方面。"
        "必须返回严格的JSON对象，格式如下：\n"
        '{"body_part": "受影响的部位名称",'
        '"findings": "详细发现描述",'
        '"severity": "轻/中/重/无法判断",'
        '"possible_conditions": ["疑似疾病1", "疑似疾病2"],'
        '"needs_vet_attention": true/false}'
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{image_data}"},
                },
                {
                    "type": "text",
                    "text": f"请分析这张宠物照片。用户描述的症状：{context or '未提供'}。请返回JSON。",
                },
            ],
        },
    ]

    response = await vision_llm.ainvoke(messages)
    parsed = _parse_json_response(response.content)

    return {
        "body_part": parsed.get("body_part", ""),
        "findings": parsed.get("findings", response.content),
        "severity": parsed.get("severity", ""),
        "possible_conditions": parsed.get("possible_conditions", []),
        "needs_vet_attention": parsed.get("needs_vet_attention", None),
        "raw_analysis": response.content,
    }
