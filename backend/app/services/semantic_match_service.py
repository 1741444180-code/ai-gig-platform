"""语义匹配引擎 (vector-05).

使用 pgvector 的 cosine_similarity 进行需求↔Agent语义匹配。
混合权重：语义相似度×0.6 + 信用分×0.2 + 成交率×0.2
"""

import logging
from typing import List, Dict, Any, Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.demand import Demand
from app.services.embedding_service import get_embedding

logger = logging.getLogger(__name__)

# 混合匹配权重
WEIGHT_SIMILARITY = 0.6
WEIGHT_CREDIT = 0.2
WEIGHT_COMPLETION = 0.2


async def semantic_match_agents(
    demand: Demand, db: AsyncSession, top_n: int = 10
) -> List[Dict[str, Any]]:
    """语义匹配Agent。
    
    1. 如果需求没有向量，先生成
    2. 用 cosine_similarity 查询匹配的Agent
    3. 混合评分：相似度×0.6 + 信用分×0.2 + 成交率×0.2
    
    Returns:
        [{"agent": Agent, "score": float, "similarity": float}]
    """
    # 确保需求有向量
    if not demand.demand_vec:
        vec = await get_embedding(_demand_text(demand))
        if vec:
            demand.demand_vec = vec
            await db.commit()
    
    if not demand.demand_vec:
        logger.warning("Demand has no embedding vector")
        return []
    
    # 用 pgvector 查询 — 只查询必要字段
    vec_str = f"[{','.join(str(v) for v in demand.demand_vec)}]"
    
    query = text(f"""
        SELECT 
            a.id, a.name, a.description, a.capabilities, a.credit_score,
            a.completed_count, a.failed_count, a.status,
            (a.description_vec <=> CAST(:vec_str AS vector)) as distance
        FROM agents a
        WHERE a.status = 'active'
          AND a.description_vec IS NOT NULL
        ORDER BY a.description_vec <=> CAST(:vec_str AS vector)
        LIMIT :top_n
    """)
    
    result = await db.execute(query, {"vec_str": vec_str, "top_n": top_n})
    rows = result.fetchall()
    
    matched = []
    for row in rows:
        # cosine distance → similarity (1 - distance)
        distance = float(row.distance) if row.distance else 1.0
        similarity = max(0.0, 1.0 - distance)
        
        # 信用分归一化 (0-1000 → 0-1)
        credit_norm = row.credit_score / 1000.0
        
        # 成交率归一化
        total_orders = max(1, row.completed_count + row.failed_count)
        completion_rate = row.completed_count / total_orders
        
        # 混合评分
        score = (
            similarity * WEIGHT_SIMILARITY
            + credit_norm * WEIGHT_CREDIT
            + completion_rate * WEIGHT_COMPLETION
        )
        
        # 查询完整Agent对象
        agent_result = await db.execute(select(Agent).where(Agent.id == row.id))
        agent = agent_result.scalar_one_or_none()
        
        if agent:
            matched.append({
                "agent": agent,
                "score": round(score * 100, 2),
                "similarity": round(similarity, 4),
            })
    
    return matched


def _demand_text(demand: Demand) -> str:
    """拼接需求文本用于embedding。"""
    parts = [demand.title or "", demand.description or ""]
    if demand.category:
        parts.append(demand.category)
    if demand.tags:
        parts.append(demand.tags)
    return " ".join(p for p in parts if p)


async def vectorize_agent(agent: Agent, db: AsyncSession):
    """Agent能力向量化 (vector-03)."""
    text = f"{agent.name or ''} {agent.description or ''} {agent.capabilities or ''}"
    vec = await get_embedding(text)
    if vec:
        agent.description_vec = vec
        await db.commit()


async def vectorize_demand(demand: Demand, db: AsyncSession):
    """需求向量化 (vector-04)."""
    text = _demand_text(demand)
    vec = await get_embedding(text)
    if vec:
        demand.demand_vec = vec
        await db.commit()
