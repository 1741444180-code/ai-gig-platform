"""需求撮合规则匹配引擎 (match-01).

输入demand → 提取category+tags → 查询匹配的Agent → 按信用分排序 → 返回Top N

匹配规则：
1. category完全匹配（必须）
2. tags包含匹配（至少1个标签）
3. 信用分降序
4. 排除已接单/低质量Agent
"""

import json
import logging
from typing import List, Dict, Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.demand import Demand

logger = logging.getLogger(__name__)


async def match_agents(
    demand: Demand, db: AsyncSession, top_n: int = 5
) -> List[Dict[str, Any]]:
    """规则匹配Agent。

    Args:
        demand: 需求对象
        db: 数据库会话
        top_n: 返回Top N个Agent

    Returns:
        [{"agent": Agent, "score": int, "matched_tags": [...]}]
    """
    # 解析需求的tags
    demand_tags = _parse_tags(demand)
    category = demand.category
    
    # 查询所有活跃的Agent
    result = await db.execute(
        select(Agent).where(
            Agent.status == "active",
            Agent.is_owner_agent == False,  # 排除自有Agent（自有Agent走兜底逻辑）
        )
    )
    agents = result.scalars().all()
    
    matched = []
    for agent in agents:
        score, matched_tags = _calc_match_score(agent, category, demand_tags)
        if score > 0:
            matched.append({
                "agent": agent,
                "score": score,
                "matched_tags": matched_tags,
            })
    
    # 按匹配分数排序（高分优先），同分按信用分排序
    matched.sort(key=lambda x: (x["score"], x["agent"].credit_score), reverse=True)
    
    return matched[:top_n]


def _parse_tags(demand: Demand) -> List[str]:
    """解析需求标签。"""
    if demand.tags:
        try:
            return json.loads(demand.tags)
        except (json.JSONDecodeError, TypeError):
            return []
    return []


def _calc_match_score(
    agent: Agent, category: Optional[str], demand_tags: List[str]
) -> tuple[int, List[str]]:
    """计算Agent与需求的匹配分数。
    
    Returns:
        (score, matched_tags)
    """
    if not category or not demand_tags:
        return 0, []
    
    # 解析Agent capabilities
    try:
        agent_caps = json.loads(agent.capabilities) if agent.capabilities else []
    except (json.JSONDecodeError, TypeError):
        return 0, []
    
    # category不匹配直接排除
    if category not in agent_caps:
        return 0, []
    
    # 计算tag匹配
    matched_tags = [t for t in demand_tags if t in agent_caps]
    
    # 基础分数：category匹配(100分) + 每个tag匹配(30分)
    score = 100 + len(matched_tags) * 30
    
    # 信用分加权：每100分加10分
    score += (agent.credit_score // 100) * 10
    
    # 成交率加权：每完成1单加5分
    score += agent.completed_count * 5
    
    return score, matched_tags
