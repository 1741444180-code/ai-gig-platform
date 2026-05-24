"""ai-review-02/03 API endpoints — AI验收评分 + 仲裁分析."""

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.engine import get_db
from app.models.order import Order
from app.models.demand import Demand
from app.models.user import User
from app.core.security import get_current_user
from app.services.ai_review_service import (
    ai_review_delivery,
    ai_arbitration_review,
)

router = APIRouter(prefix="/orders", tags=["AI辅助验收"])


class AIReviewResponse(BaseModel):
    order_id: str
    score: int
    reason: str
    strengths: List[str]
    improvements: List[str]
    completion_percent: int


class AIReviewRequest(BaseModel):
    delivery_content: Optional[str] = None


@router.post("/{order_id}/ai-review", response_model=AIReviewResponse)
async def ai_review_order(
    order_id: str,
    req: AIReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """AI验收评分 (ai-review-02).
    
    对已交付的订单进行AI质量评分，仅completed/delivered/rejected状态可评。
    评分结果存入 order.ai_quality_score 字段。
    """
    # 查找订单
    result = await db.execute(
        select(Order).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    # 检查权限：仅订单相关方可用
    is_owner = order.user_id == current_user.id
    is_admin = hasattr(current_user, "is_admin") and current_user.is_admin
    if not is_owner and not is_admin:
        raise HTTPException(status_code=403, detail="无权访问此订单")
    
    # 检查状态
    if order.status not in ["delivered", "completed", "rejected"]:
        raise HTTPException(status_code=400, detail="仅已交付/已完成/已拒绝的订单可进行AI评分")
    
    # 获取需求信息
    demand_result = await db.execute(
        select(Demand).where(Demand.id == order.demand_id)
    )
    demand = demand_result.scalar_one_or_none()
    if not demand:
        raise HTTPException(status_code=404, detail="关联需求不存在")
    
    # 调用AI评分
    review_result = await ai_review_delivery(
        demand_title=demand.title,
        demand_description=demand.description,
        delivery_content=req.delivery_content or order.delivery_note,
        delivery_url=order.delivery_url,
        category=demand.category,
        tags=demand.tags,
    )
    
    # 存入订单
    order.ai_quality_score = review_result["score"]
    await db.commit()
    
    return AIReviewResponse(
        order_id=order.id,
        score=review_result["score"],
        reason=review_result["reason"],
        strengths=review_result["strengths"],
        improvements=review_result["improvements"],
        completion_percent=review_result["completion_percent"],
    )


class AIArbitrationRequest(BaseModel):
    delivery_content: Optional[str] = None


class AIArbitrationResponse(BaseModel):
    order_id: str
    suggested_refund_percent: int
    suggested_resolution: str
    reason: str
    match_score: int


@router.post("/{order_id}/ai-arbitration", response_model=AIArbitrationResponse)
async def ai_arbitration(
    order_id: str,
    req: AIArbitrationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """AI辅助仲裁初裁 (ai-review-03).
    
    在仲裁流程中自动触发AI分析，给出建议退款比例+理由。
    管理员最终裁决时参考。
    """
    # 查找订单
    result = await db.execute(
        select(Order).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    # 仅仲裁中订单可触发
    if order.status != "disputed":
        raise HTTPException(status_code=400, detail="仅仲裁中订单可进行AI仲裁分析")
    
    # 获取需求信息
    demand_result = await db.execute(
        select(Demand).where(Demand.id == order.demand_id)
    )
    demand = demand_result.scalar_one_or_none()
    if not demand:
        raise HTTPException(status_code=404, detail="关联需求不存在")
    
    # 调用AI仲裁分析
    result = await ai_arbitration_review(
        demand_title=demand.title,
        demand_description=demand.description,
        delivery_content=req.delivery_content or order.delivery_note,
        delivery_url=order.delivery_url,
        reject_reason=order.reject_reason,
        category=demand.category,
    )
    
    return AIArbitrationResponse(
        order_id=order.id,
        suggested_refund_percent=result["suggested_refund_percent"],
        suggested_resolution=result["suggested_resolution"],
        reason=result["reason"],
        match_score=result["match_score"],
    )
