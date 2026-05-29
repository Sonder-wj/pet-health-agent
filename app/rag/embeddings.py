"""Ollama bge-m3 embedding 封装"""
import asyncio
from typing import List

import httpx

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(service="embedding")


async def embed_text(text: str) -> List[float]:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.OLLAMA_BASE_URL}/api/embeddings",
            json={"model": settings.OLLAMA_EMBEDDING_MODEL, "prompt": text},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["embedding"]


async def embed_batch(texts: List[str]) -> List[List[float]]:
    return await asyncio.gather(*[embed_text(t) for t in texts])
