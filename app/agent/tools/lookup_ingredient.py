"""食材查表工具 — 在 USDA 子集中按英文键或中文片段匹配。"""
from langchain_core.tools import tool

from app.engine.data_loader import load_ingredients


@tool
async def lookup_ingredient(query: str, max_results: int = 5) -> dict:
    """查询食材的每 100g 营养数据（来源 USDA 子集）。

    支持英文键名（"chicken_breast"）或中文片段（"鸡胸"）模糊匹配，
    用于让 Agent 在分析自制饮食前先确认食材匹配。

    Args:
        query: 食材名称（英文或中文片段）
        max_results: 最多返回多少条候选，默认 5
    """
    if not query or not query.strip():
        return {"status": "error", "message": "查询不能为空"}

    try:
        db = load_ingredients()
    except Exception as e:  # 数据文件缺失 / 格式错误
        return {"status": "error", "message": f"食材库加载失败: {e}"}

    needle = query.strip().lower()
    hits: list[dict] = []
    for key, entry in db.items():
        zh = (entry.get("name_zh") or "").lower()
        if needle in key.lower() or needle in zh:
            hits.append({"name": key, **entry})
            if len(hits) >= max_results:
                break

    return {
        "status": "ok" if hits else "no_match",
        "query": query,
        "total": len(hits),
        "hits": hits,
    }
