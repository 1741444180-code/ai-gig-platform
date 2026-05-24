"""Review API endpoints — 评价系统 (review-01~03)."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_db
from app.models.user import User
from app.models.agent import Agent
from app.models.order import Order
from app.models.review import Review
from app.core.security import get_current_user
from app.services.agent_key_service import get_current_agent

router = APIRouter(prefix="/reviews", tags=["评价系统"])


# ── Schemas ──────────────────────────────────────────────────────

class CreateReviewRequest(BaseModel):
    score: int
    content: Optional[str] = None


class ReviewResponse(BaseModel):
    id: str
    order_id: str
    reviewer_id: str
    reviewee_id: str
    score: int
    content: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewListResponse(BaseModel):
    items: list[ReviewResponse]
    total: int
    page: int
    page_size: int
    avg_score: float


class AppealRequest(BaseModel):
    appeal_reason: str


class AdminReviewAction(BaseModel):
    action: str  # dismiss | delete
    admin_note: Optional[str] = None


# ── review-01: 评价创建 ─────────────────────────────────────────

@router.post("/orders/{order_id}/review", response_model=ReviewResponse)
async def create_review(
    order_id: str,
    req: CreateReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """用户验收后评价 (review-01).
    
    score: 1-5
    content: 评价内容（可选）
    """
    if req.score < 1 or req.score > 5:
        raise HTTPException(status_code=400, detail="评分必须在1-5之间")
    
    # 检查订单是否存在且已完成
    result = await db.execute(
        select(Order).where(
            Order.id == order_id,
            Order.user_id == current_user.id,
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status != "completed":
        raise HTTPException(status_code=400, detail="仅已完成的订单可评价")
    
    # 检查是否已评价
    existing = await db.execute(
        select(Review).where(Review.order_id == order_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该订单已评价")
    
    # 创建评价
    review = Review(
        order_id=order_id,
        reviewer_id=current_user.id,
        reviewee_id=order.agent_id,
        score=req.score,
        content=req.content,
    )
    db.add(review)
    
    # 更新Agent平均评分（简单累加平均）
    agent_result = await db.execute(
        select(Agent).where(Agent.id == order.agent_id)
    )
    agent = agent_result.scalar_one_or_none()
    if agent:
        # 计算该Agent所有评价的平均分
        all_reviews = await db.execute(
            select(Review).where(Review.reviewee_id == agent.id)
        )
        reviews = all_reviews.scalars().all()
        if reviews:
            avg_score = sum(r.score for r in reviews) / len(reviews)
            agent.credit_score = max(0, min(1000, int(avg_score * 200)))  # 平均分映射到信用分
    
    await db.commit()
    await db.refresh(review)
    
    return review


# ── review-02: Agent评价列表查询 ────────────────────────────────

@router.get("/agents/{agent_id}", response_model=ReviewListResponse)
async def get_agent_reviews(
    agent_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Agent评价列表 (review-02).
    
    分页列表；平均分统计；最新评价优先。
    """
    query = select(Review).where(
        Review.reviewee_id == agent_id,
        Review.is_appealed == False,  # 不显示被申诉的评价
    )
    
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 计算平均分
    avg_query = select(func.avg(Review.score)).where(
        Review.reviewee_id == agent_id,
        Review.is_appealed == False,
    )
    avg_result = await db.execute(avg_query)
    avg_score = avg_result.scalar() or 0
    
    query = query.order_by(Review.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()
    
    return ReviewListResponse(
        items=list(items),
        total=total,
        page=page,
        page_size=page_size,
        avg_score=round(avg_score, 2),
    )


# ── review-03: 评价申诉 ─────────────────────────────────────────

@router.post("/{review_id}/appeal")
async def submit_appeal(
    review_id: str,
    req: AppealRequest,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """Agent申诉某评价 (review-03)."""
    result = await db.execute(select(Review).where(Review.id == review_id))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="评价不存在")
    if review.reviewee_id != current_agent.id:
        raise HTTPException(status_code=403, detail="仅被评价的Agent可申诉")
    if review.is_appealed:
        raise HTTPException(status_code=400, detail="该评价已被申诉")
    
    review.is_appealed = True
    review.appeal_reason = req.appeal_reason
    review.appeal_status = "pending"
    await db.commit()
    
    return {"success": True, "message": "申诉已提交，等待管理员审核"}


# ── review-03: 管理员审核申诉 ────────────────────────────────────

@router.post("/{review_id}/admin-action")
async def admin_review_action(
    review_id: str,
    req: AdminReviewAction,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """管理员审核评价申诉 (review-03).
    
    action: dismiss（驳回申诉，保留评价）| delete（删除评价，恢复信用分）
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    result = await db.execute(select(Review).where(Review.id == review_id))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="评价不存在")
    if review.appeal_status != "pending":
        raise HTTPException(status_code=400, detail="该评价不在申诉审核中")
    
    review.admin_action = req.action
    review.admin_note = req.admin_note or ""
    review.appeal_status = "resolved"
    
    if req.action == "delete":
        # 删除评价（软删除，标记is_appealed=False并隐藏）
        review.is_appealed = False
        review.appeal_status = "resolved_deleted"
        
        # 恢复Agent信用分（重新计算）
        agent_result = await db.execute(
            select(Agent).where(Agent.id == review.reviewee_id)
        )
        agent = agent_result.scalar_one_or_none()
        if agent:
            all_reviews = await db.execute(
                select(Review).where(
                    Review.reviewee_id == agent.id,
                    Review.appeal_status != "resolved_deleted",
                )
            )
            reviews = all_reviews.scalars().all()
            if reviews:
                avg_score = sum(r.score for r in reviews) / len(reviews)
                agent.credit_score = max(0, min(1000, int(avg_score * 200)))
            else:
                agent.credit_score = 100  # 无评价时恢复默认
    
    elif req.action == "dismiss":
        # 驳回申诉，保留评价
        review.is_appealed = True
        review.appeal_status = "resolved"
    
    await db.commit()
    
    return {"success": True, "message": f"申诉审核完成: {req.action}"}
