"""知识库数据加载与灌入"""
import json
from pathlib import Path

from app.core.logger import get_logger
from app.rag.embeddings import embed_batch
from app.rag.retriever import insert

logger = get_logger(service="loader")

ROOT_DIR = Path(__file__).parent.parent.parent
DATA_DIR = ROOT_DIR / "data"


def _format_disease_doc(disease: dict) -> str:
    parts = [
        f"【疾病】{disease['name']}",
        f"别名：{'、'.join(disease.get('aliases', []))}" if disease.get('aliases') else "",
        f"适用物种：{'、'.join(disease['species'])}",
        f"分类：{disease['category']}",
        f"病因：{disease['etiology']}",
        f"典型症状：{'；'.join(disease['typical_symptoms'])}",
        f"危险信号：{'；'.join(disease.get('danger_signals', []))}",
        f"鉴别诊断：{'；'.join(disease.get('differential_diagnosis', []))}",
        f"居家护理：{'；'.join(disease.get('home_care', []))}" if disease.get('home_care') else "",
        f"需就医指征：{'；'.join(disease.get('vet_indicators', []))}",
        f"治疗概述：{disease.get('treatment_overview', '')}",
        f"预防措施：{disease.get('prevention', '')}",
    ]
    return "\n".join(p for p in parts if p)


async def load_diseases(file_path: str | None = None) -> int:
    if file_path is None:
        file_path = str(DATA_DIR / "pet_diseases.json")

    with open(file_path, "r", encoding="utf-8") as f:
        diseases = json.load(f)

    texts = [_format_disease_doc(d) for d in diseases]
    metas = [{"name": d["name"], "category": d["category"], "species": d.get("species", [])} for d in diseases]

    logger.info(f"Embedding {len(texts)} disease documents...")
    embeddings = await embed_batch(texts)

    logger.info(f"Inserting {len(embeddings)} vectors into Milvus...")
    count = insert(texts, embeddings, metas)

    logger.info(f"Loaded {count} documents into knowledge base")
    return count
