"""需求撮合触发服务 (match-03).

需求发布后自动匹配+推送给Top N Agent。
"""

import json
import logging
from typing import Optional, List, Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.demand import Demand
from app.models.agent import Agent
from app.models.order import Order
from app.services.match_service import match_agents
from app.services.webhook_service import push_demand_to_agent

logger = logging.getLogger(__name__)

# 最大推送Agent数
MAX_PUSH_AGENTS = 5


async def trigger_matching(
    demand: Demand, db: AsyncSession, top_n: int = MAX_PUSH_AGENTS
) -> Dict[str, Any]:
    """触发需求撮合。

    1. 调用规则匹配引擎获取Top N Agent
    2. 逐个推送需求到Agent Webhook
    3. 更新demand.match_status

    Args:
        demand: 需求对象
        db: 数据库会话
        top_n: 推送Top N个Agent

    Returns:
        {
            "matched_count": int,
            "pushed_count": int,
            "pushed_agents": [...],
        }
    """
    # 1. 匹配Agent
    matched = await match_agents(demand, db, top_n=top_n)
    
    if not matched:
        logger.info(f"[Match] No matching agents for demand {demand.id}")
        demand.match_status = "no_match"
        await db.commit()
        return {
            "matched_count": 0,
            "pushed_count": 0,
            "pushed_agents": [],
        }
    
    # 2. 推送需求
    demand_data = _build_demand_payload(demand)
    pushed_agents = []
    
    for item in matched:
        agent = item["agent"]
        if not agent.webhook_url:
            logger.warning(f"[Match] Agent {agent.id} has no webhook_url, skipping")
            continue
        
        result = await push_demand_to_agent(
            webhook_url=agent.webhook_url,
            webhook_secret=agent.webhook_secret or "default-secret",
            demand_data=demand_data,
        )
        
        if result["success"]:
            pushed_agents.append({
                "agent_id": agent.id,
                "agent_name": agent.name,
                "score": item["score"],
                "matched_tags": item["matched_tags"],
                "event_id": result["event_id"],
            })
    
    # 3. 更新状态
    if pushed_agents:
        demand.match_status = "matched"
        demand.updated_at = demand.updated_at
        await db.commit()
    
    return {
        "matched_count": len(matched),
        "pushed_count": len(pushed_agents),
        "pushed_agents": pushed_agents,
    }


def _build_demand_payload(demand: Demand) -> Dict[str, Any]:
    """构建需求推送数据。"""
    return {
        "demand_id": demand.id,
        "title": demand.title,
        "description": demand.description,
        "category": demand.category,
        "tags": demand.tags,
        "budget": demand.budget,
        "deadline": demand.deadline.isoformat() if demand.deadline else None,
        "ai_structured": demand.ai_structured,
    }
