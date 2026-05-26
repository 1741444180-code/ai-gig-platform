"""Embedding service — 文本向量化 (vector-02).

使用通义千问 text-embedding-v2 生成 1536 维向量。
MVP阶段使用 mock 模式（基于文本hash生成伪向量）。
"""

import hashlib
import logging
from typing import List, Optional

from app.core.config import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)

# 向量维度
EMBEDDING_DIM = 1536


async def get_embedding(text: str) -> Optional[List[float]]:
    """获取文本的 embedding 向量。
    
    Args:
        text: 输入文本
        
    Returns:
        1536维浮点向量，或None（失败时）
    """
    if not text or not text.strip():
        return None
    
    if settings.app_env == "development":
        # 开发模式：使用 mock 向量（基于文本hash生成伪向量）
        return _mock_embedding(text)
    
    # 生产模式：调用通义千问 API
    return await _dashscope_embedding(text)


def _mock_embedding(text: str) -> List[float]:
    """生成 mock embedding（基于文本hash的伪向量）。
    
    用于开发/测试，确保相同文本产生相同向量。
    """
    # 用hash生成种子
    seed = int(hashlib.md5(text.encode()).hexdigest(), 16)
    
    # 基于种子生成伪随机向量
    import random
    rng = random.Random(seed)
    return [rng.gauss(0, 1) for _ in range(EMBEDDING_DIM)]


async def _dashscope_embedding(text: str) -> Optional[List[float]]:
    """调用通义千问 text-embedding-v2 API (OpenAI 兼容协议)。"""
    try:
        import httpx
        
        api_key = settings.QWEN_API_KEY
        base_url = getattr(settings, 'dashscope_base_url', 'https://coding.dashscope.aliyuncs.com/v1')
        
        if not api_key:
            logger.warning("API_KEY not set, using mock embedding")
            return _mock_embedding(text)
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": "text-embedding-v2",
            "input": text,
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{base_url}/embeddings", json=payload, headers=headers)
            
            if resp.status_code != 200:
                logger.error(f"Embedding API error: {resp.status_code} {resp.text}")
                return _mock_embedding(text)
            
            data = resp.json()
            embeddings = data.get("data", [])
            if embeddings:
                return embeddings[0].get("embedding", [])
            
            return _mock_embedding(text)
            
    except Exception as e:
        logger.error(f"Embedding API failed: {e}")
        return _mock_embedding(text)


async def get_embeddings_batch(texts: List[str]) -> List[Optional[List[float]]]:
    """批量获取 embedding 向量。"""
    return [await get_embedding(t) for t in texts]
