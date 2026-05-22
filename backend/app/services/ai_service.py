"""AI服务模块 - 通义千问API调用（需求结构化、Embedding、智能撮合）"""

import json
import logging
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


# ==================== 需求结构化 ====================

_STRUCTURE_PROMPT = """你是一个需求分析专家。请将用户的需求描述进行结构化分析，返回JSON格式。

要求返回以下字段：
- category: 需求类别（如 "内容生成"、"数据分析"、"图像设计"、"代码开发"、"翻译"、"其他"）
- tags: 需求标签列表（最多5个）
- suggested_budget: 预算建议（数字，单位：元）
- urgency: 紧急程度（1=普通，2=加急，3=特急）

只返回JSON，不要其他解释。

用户需求：
{text}
"""


async def structure_requirement(text: str) -> dict:
    """调用通义千问结构化需求

    将用户输入的自由文本需求进行AI结构化分析，
    提取类别、标签、预算建议、紧急度。

    Args:
        text: 需求描述文本

    Returns:
        结构化数据 dict，包含 category, tags, suggested_budget, urgency
        AI调用失败时返回默认值
    """
    default_result = {
        "category": "其他",
        "tags": [],
        "suggested_budget": 0,
        "urgency": 1,
    }

    if not settings.QWEN_API_KEY:
        logger.warning("未配置QWEN_API_KEY，使用默认结构化结果")
        return default_result

    try:
        import dashscope
        from dashscope import Generation

        prompt = _STRUCTURE_PROMPT.format(text=text)

        response = Generation.call(
            api_key=settings.QWEN_API_KEY,
            model=settings.QWEN_MODEL,
            prompt=prompt,
            result_format="message",
        )

        if response.status_code != 200:
            logger.warning(f"通义千问结构化请求失败: {response.code} {response.message}")
            return default_result

        content = response.output.choices[0].message.content.strip()

        # 尝试解析JSON（处理可能的markdown代码块包裹）
        if content.startswith("```"):
            # 去掉 ```json 和 ```
            content = content.strip("`").strip()
            if content.startswith("json"):
                content = content[4:].strip()

        structured = json.loads(content)
        logger.info(f"需求结构化成功: {structured}")
        return structured

    except Exception as e:
        logger.error(f"需求结构化异常: {e}")
        return default_result


# ==================== Embedding 生成 ====================

async def generate_embedding(text: str) -> Optional[list[float]]:
    """调用通义千问 text-embedding-v3 生成文本向量

    Args:
        text: 要生成向量的文本

    Returns:
        1536维向量列表，AI调用失败时返回 None
    """
    if not settings.QWEN_API_KEY:
        logger.warning("未配置QWEN_API_KEY，跳过embedding生成")
        return None

    try:
        import dashscope
        from dashscope import TextEmbedding

        response = TextEmbedding.call(
            api_key=settings.QWEN_API_KEY,
            model="text-embedding-v3",
            input=text,
            text_type="query",
        )

        if response.status_code != 200:
            logger.warning(f"通义千问embedding请求失败: {response.code} {response.message}")
            return None

        embedding = response.output["embeddings"][0]["embedding"]
        logger.info(f"Embedding生成成功，维度: {len(embedding)}")
        return embedding

    except Exception as e:
        logger.error(f"Embedding生成异常: {e}")
        return None


# ==================== 智能撮合（pgvector） ====================

async def match_agents(
    db: AsyncSession,
    embedding: list[float],
    limit: int = 10,
) -> list[dict]:
    """使用pgvector cosine similarity查找最匹配的Agent

    在 agent_profiles 表中搜索 description + tags 与需求向量最接近的Agent。

    Args:
        db: 数据库会话
        embedding: 需求向量（1536维）
        limit: 返回结果数量

    Returns:
        匹配结果列表，每个元素包含 agent_id, name, score 等
    """
    # 将 embedding 列表格式化为 PostgreSQL 数组字面量
    embedding_literal = "[" + ",".join(str(v) for v in embedding) + "]"

    # 使用 bind 参数避免字符串拼接
    query = text("""
        SELECT
            ap.user_id AS agent_id,
            ap.name AS agent_name,
            ap.description,
            ap.tags,
            ap.base_price,
            u.nickname AS agent_nickname,
            u.credit_score,
            (ap.description_vec <=> CAST(:embedding AS vector(1536))) AS similarity
        FROM agent_profiles ap
        JOIN users u ON ap.user_id = u.id
        WHERE ap.status = 1
        ORDER BY ap.description_vec <=> CAST(:embedding AS vector(1536))
        LIMIT :limit
    """)

    result = await db.execute(query, {"embedding": embedding_literal, "limit": limit})
    rows = result.fetchall()

    matches = []
    for row in rows:
        matches.append({
            "agent_id": str(row.agent_id),
            "agent_name": row.agent_name,
            "agent_nickname": row.agent_nickname,
            "description": row.description,
            "tags": row.tags,
            "base_price": row.base_price,
            "credit_score": row.credit_score,
            "similarity": round(float(row.similarity), 4),
        })

    logger.info(f"智能撮合完成，找到 {len(matches)} 个匹配Agent")
    return matches
