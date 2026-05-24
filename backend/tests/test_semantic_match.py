"""Semantic match integration tests (vector-01~06).

Coverage: embedding mock/vectorize/demand-agent semantic match pipeline.
"""

import pytest
from app.services.embedding_service import get_embedding, EMBEDDING_DIM
from app.services.semantic_match_service import _demand_text


@pytest.mark.asyncio
async def test_mock_embedding_returns_correct_dimension():
    """Mock embedding must return EMBEDDING_DIM floats."""
    vec = await get_embedding("测试文案Agent，擅长写广告文案和营销内容")
    assert vec is not None
    assert len(vec) == EMBEDDING_DIM
    assert all(isinstance(v, float) for v in vec)


@pytest.mark.asyncio
async def test_mock_embedding_deterministic():
    """Same text must produce same vector (deterministic hash)."""
    text = "Python开发，FastAPI后端，API接口设计"
    v1 = await get_embedding(text)
    v2 = await get_embedding(text)
    assert v1 == v2


@pytest.mark.asyncio
async def test_mock_embedding_different_texts():
    """Different texts should produce different vectors."""
    v1 = await get_embedding("文案写作")
    v2 = await get_embedding("图片生成")
    assert v1 != v2


@pytest.mark.asyncio
async def test_empty_text_returns_none():
    """Empty or whitespace text should return None."""
    assert await get_embedding("") is None
    assert await get_embedding("   ") is None


def test_demand_text_concatenation():
    """_demand_text should concatenate title, description, category, tags."""
    from unittest.mock import MagicMock
    d = MagicMock()
    d.title = "需要一篇广告文案"
    d.description = "产品介绍，200字以内"
    d.category = "文案"
    d.tags = '["广告","营销"]'
    result = _demand_text(d)
    assert "需要一篇广告文案" in result
    assert "产品介绍" in result
    assert "文案" in result
    assert '["广告","营销"]' in result


def test_demand_text_missing_fields():
    """_demand_text should handle None/missing fields gracefully."""
    from unittest.mock import MagicMock
    d = MagicMock()
    d.title = None
    d.description = "只要描述"
    d.category = None
    d.tags = None
    result = _demand_text(d)
    assert result == "只要描述"


def test_demand_text_only_title():
    from unittest.mock import MagicMock
    d = MagicMock()
    d.title = "标题"
    d.description = ""
    d.category = None
    d.tags = None
    result = _demand_text(d)
    assert result == "标题"


@pytest.mark.asyncio
async def test_embedding_batch():
    """Batch embedding should return list of vectors."""
    from app.services.embedding_service import get_embeddings_batch
    texts = ["文案", "图片生成", "数据分析"]
    results = await get_embeddings_batch(texts)
    assert len(results) == 3
    assert all(len(v) == EMBEDDING_DIM for v in results if v is not None)


@pytest.mark.asyncio
async def test_embedding_empty_string_in_batch():
    from app.services.embedding_service import get_embeddings_batch
    results = await get_embeddings_batch(["valid text", ""])
    assert results[0] is not None
    assert results[1] is None
