"""搜索宠物疾病知识库"""
from langchain_core.tools import tool

from app.rag.embeddings import embed_text
from app.rag.retriever import search


@tool
async def search_pet_knowledge(
    query: str,
    species: str = "",
    condition: str = "",
) -> dict:
    """搜索宠物疾病知识库，获取相关的疾病、护理和治疗信息。

    Args:
        query: 搜索关键词
        species: 宠物种类（可选，用于过滤）
        condition: 具体症状或疾病名（可选）
    """
    try:
        embedding = await embed_text(query)
        hits = search(embedding, top_k=3)

        if not hits:
            return _fallback(query, species)

        results = []
        for h in hits:
            results.append({
                "content": h["text"],
                "meta": h["meta"],
                "score": round(h["score"], 4),
            })

        return {
            "query": query,
            "species": species,
            "source": "milvus_vector_search",
            "total_hits": len(results),
            "results": results,
        }
    except Exception:
        return _fallback(query, species)


def _fallback(query: str, species: str) -> dict:
    animal = species or "宠物"
    keywords = query.lower()

    if any(kw in keywords for kw in ["吐", "呕吐", "vomit"]):
        advice = f"{animal}呕吐常见原因：饮食不当、毛球（猫）、肠胃炎、寄生虫、感染。禁食4-6小时后少量喂易消化食物。持续超过24小时、含血丝、精神萎靡需立即就医。"
    elif any(kw in keywords for kw in ["腹泻", "拉稀"]):
        advice = f"{animal}腹泻可能由换食过快、寄生虫、细菌感染或应激引起。暂禁食6-12小时，确保饮水。超过48小时或含血需就医。"
    elif any(kw in keywords for kw in ["皮肤", "痒", "掉毛", "红疹"]):
        advice = f"{animal}皮肤问题可能原因：过敏、寄生虫、真菌感染、内分泌失调。检查有无跳蚤排泄物，定期驱虫。范围扩大或出现脓疱需就医。"
    elif any(kw in keywords for kw in ["不吃", "拒食"]):
        advice = f"{animal}拒食可能由口腔问题、消化疾病、感染、应激引起。完全不吃超过24小时（猫）或48小时（狗）需就医。"
    elif any(kw in keywords for kw in ["咳嗽", "喷嚏", "呼吸"]):
        advice = f"{animal}呼吸道症状可能原因：上呼吸道感染、过敏、异物、心力衰竭。伴呼吸困难、张口呼吸、牙龈发紫需立即就医。"
    else:
        advice = f"建议密切观察{animal}精神、食欲和排便。症状持续或加重请及时就诊。"

    return {
        "query": query,
        "species": species,
        "source": "fallback",
        "message": "知识库不可用，以下为通用护理建议",
        "general_advice": advice,
    }
