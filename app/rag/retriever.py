"""Milvus 向量存储 — 连接、建集合、搜索"""
from typing import Any, Dict, List, Optional

from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(service="milvus")

COLLECTION_NAME = settings.MILVUS_COLLECTION
DIM = 1024  # bge-m3 dimension

_connected = False


def connect():
    global _connected
    if _connected:
        return True
    try:
        connections.connect(
            host=settings.MILVUS_HOST,
            port=settings.MILVUS_PORT,
            timeout=5,
        )
        _connected = True
        logger.info(f"Milvus connected: {settings.MILVUS_HOST}:{settings.MILVUS_PORT}")
        return True
    except Exception as e:
        logger.warning(f"Milvus unavailable: {e}")
        return False


def ensure_collection() -> Optional[Collection]:
    if not connect():
        return None

    if utility.has_collection(COLLECTION_NAME):
        return Collection(COLLECTION_NAME)

    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=4096),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=DIM),
        FieldSchema(name="meta", dtype=DataType.JSON),
    ]
    schema = CollectionSchema(fields, description="Pet health knowledge base")
    collection = Collection(COLLECTION_NAME, schema)

    index_params = {
        "metric_type": "IP",
        "index_type": "IVF_FLAT",
        "params": {"nlist": 128},
    }
    collection.create_index("embedding", index_params)
    collection.load()
    logger.info(f"Collection '{COLLECTION_NAME}' created and indexed")
    return collection


def search(embedding: List[float], top_k: int = 3) -> List[Dict[str, Any]]:
    collection = ensure_collection()
    if collection is None:
        return []

    search_params = {"metric_type": "IP", "params": {"nprobe": 16}}
    results = collection.search(
        data=[embedding],
        anns_field="embedding",
        param=search_params,
        limit=top_k,
        output_fields=["text", "meta"],
    )

    hits = []
    for hit in results[0]:
        hits.append({
            "text": hit.entity.get("text"),
            "meta": hit.entity.get("meta"),
            "score": float(hit.distance),
        })
    return hits


def insert(texts: List[str], embeddings: List[List[float]], metas: List[dict]) -> int:
    collection = ensure_collection()
    if collection is None:
        return 0

    data = [texts, embeddings, metas]
    result = collection.insert(data)
    collection.flush()
    return result.insert_count
