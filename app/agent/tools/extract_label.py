"""多模态标签提取工具 — 从包装照片识别保证成分分析（Guaranteed Analysis）。"""
import base64
import json
import re
from pathlib import Path

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from app.core.config import settings


def _parse_json(text: str) -> dict:
    """剥离 markdown 代码块后 JSON 解析。"""
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
        # 走独立的视觉模型配置(Qwen3-VL-Flash);与主对话(DeepSeek)解耦
        _vision_llm = ChatOpenAI(
            model=settings.VISION_MODEL,
            base_url=settings.VISION_BASE_URL,
            api_key=settings.VISION_API_KEY,
            temperature=0.1,
            model_kwargs={"response_format": {"type": "json_object"}},
        )
    return _vision_llm


_SYSTEM_PROMPT = (
    "你是宠物食品标签解析器。识别图片中的'保证成分分析(Guaranteed Analysis)'区域，"
    "提取以下数值并返回严格 JSON 对象：\n"
    "{"
    '"crude_protein_pct": <粗蛋白百分比，纯数字>, '
    '"crude_fat_pct": <粗脂肪百分比，纯数字>, '
    '"crude_fiber_pct": <粗纤维百分比，纯数字>, '
    '"moisture_pct": <水分百分比，纯数字>, '
    '"kcal_per_kg": <代谢能 kcal/kg，纯数字 或 null>'
    "}\n"
    "找不到的字段填 null。不要解释、不要添加其他字段。"
)


@tool
async def extract_label_nutrition(image_path: str) -> dict:
    """从商品宠物粮包装照片中提取保证成分分析（粗蛋白/脂肪/纤维/水分/kcal/kg）。

    当用户上传包装照时使用；解析失败时调用方应改请用户文字输入。

    Args:
        image_path: 图片文件路径（支持 jpg/png/webp）
    """
    path = Path(image_path)
    if not path.exists():
        return {"status": "error", "message": f"图片不存在: {image_path}"}

    ext = path.suffix.lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    mime_type = mime_map.get(ext, "image/jpeg")

    with open(path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode()

    llm = _get_vision_llm()
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_b64}"}},
                {"type": "text", "text": "请提取保证成分分析数值，按指定 JSON 格式返回。"},
            ],
        },
    ]

    try:
        response = await llm.ainvoke(messages)
    except Exception as e:
        return {"status": "error", "message": f"LLM 调用失败: {e}"}

    parsed = _parse_json(response.content)
    if not parsed:
        return {
            "status": "error",
            "message": "标签解析失败，请用文字输入营养成分",
            "raw": response.content,
        }

    label = {
        "crude_protein_pct": parsed.get("crude_protein_pct"),
        "crude_fat_pct": parsed.get("crude_fat_pct"),
        "crude_fiber_pct": parsed.get("crude_fiber_pct"),
        "moisture_pct": parsed.get("moisture_pct"),
        "kcal_per_kg": parsed.get("kcal_per_kg"),
    }
    return {"status": "ok", "label": label}
