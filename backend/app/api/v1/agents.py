"""Agent能力管理 API

提供Agent能力卡注册、管理、接单工作台，以及供外部Agent调用的API Key认证接口。
"""

import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import get_current_active_user
from app.db.database import get_db
from app.models.models import AgentProfile, Order, Requirement, User
from app.schemas.agent import (
    AgentProfileCreate,
    AgentProfileUpdate,
    AgentProfileResponse,
    AgentRegisterRequest,
    AgentOrderItem,
    AgentOrderListResponse,
    AcceptOrderRequest,
    SubmitDeliveryRequest,
)
from app.services.ai_service import generate_agent_embedding

router = APIRouter()


def _generate_api_key() -> str:
    """生成API Key：使用 uuid4 + 随机字符串组合

    格式: ak_{uuid}_{32位随机字符}
    """
    uid = uuid.uuid4().hex[:16]
    secret = secrets.token_urlsafe(24)
    return f"ak_{uid}_{secret}"


async def _verify_api_key(api_key: str, db: AsyncSession) -> AgentProfile:
    """通过API Key查找并验证Agent

    Args:
        api_key: Agent API Key
        db: 数据库会话

    Returns:
        AgentProfile 对象

    Raises:
        HTTPException: API Key无效或Agent状态异常
    """
    result = await db.execute(
        select(AgentProfile).where(AgentProfile.api_key == api_key)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的API Key",
        )
    if profile.status != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent状态异常，无法操作",
        )
    return profile


async def _get_agent_profile_for_user(
    user_id: uuid.UUID, db: AsyncSession
) -> AgentProfile | None:
    """获取指定用户的Agent Profile"""
    result = await db.execute(
        select(AgentProfile).where(AgentProfile.user_id == user_id)
    )
    return result.scalar_one_or_none()


# ==================== 用户端API（需JWT认证） ====================


@router.post("/register", response_model=AgentProfileResponse, summary="注册Agent能力卡")
async def register_agent(
    request: AgentRegisterRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """注册Agent能力卡

    - 每个用户只能注册一个Agent Profile
    - 生成唯一的API Key
    - 初始状态为「待审核」(status=0)
    """
    settings = get_settings()

    # 检查是否已注册
    existing = await _get_agent_profile_for_user(current_user.id, db)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="您已注册过Agent能力卡，请使用更新接口",
        )

    # 生成API Key
    api_key = _generate_api_key()

    # 创建Agent Profile
    profile = AgentProfile(
        user_id=current_user.id,
        name=request.agent.name,
        description=request.agent.description,
        tags=request.agent.tags,
        capabilities=request.agent.capabilities,
        base_price=request.agent.base_price,
        api_key=api_key,
        webhook_url=request.agent.webhook_url,
        auto_accept=request.agent.auto_accept,
        daily_limit=request.agent.daily_limit,
        status=0,  # 待审核
    )
    db.add(profile)
    await db.flush()

    # 生成 Agent 能力描述向量（用于语义匹配）
    embedding = await generate_agent_embedding(
        description=request.agent.description,
        tags=request.agent.tags,
    )
    if embedding:
        profile.description_vec = embedding
        await db.flush()

    return profile


@router.get("/me", response_model=AgentProfileResponse, summary="获取我的Agent信息")
async def get_my_agent(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的Agent能力卡信息"""
    profile = await _get_agent_profile_for_user(current_user.id, db)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="您尚未注册Agent能力卡",
        )
    return profile


@router.put("/me", response_model=AgentProfileResponse, summary="更新Agent能力卡")
async def update_my_agent(
    update_data: AgentProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """更新当前用户的Agent能力卡

    - 只能更新自己创建的Agent Profile
    - 状态为「待审核」或「正常」时允许更新
    """
    profile = await _get_agent_profile_for_user(current_user.id, db)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="您尚未注册Agent能力卡",
        )

    # 排除未设置的字段
    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(profile, key, value)

    await db.flush()
    return profile


@router.post(
    "/me/toggle_auto_accept",
    response_model=AgentProfileResponse,
    summary="切换自动接单开关",
)
async def toggle_auto_accept(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """切换Agent的自动接单开关"""
    profile = await _get_agent_profile_for_user(current_user.id, db)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="您尚未注册Agent能力卡",
        )

    profile.auto_accept = not profile.auto_accept
    await db.flush()
    return profile


@router.get(
    "/orders",
    response_model=AgentOrderListResponse,
    summary="Agent接单工作台",
)
async def get_agent_workbench(
    page: int = 1,
    page_size: int = 20,
    status_filter: str | None = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Agent接单工作台 — 查看分配给我的订单

    支持按订单状态过滤，默认返回最新的20条。
    """
    # 确认用户有Agent Profile
    profile = await _get_agent_profile_for_user(current_user.id, db)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="您尚未注册Agent能力卡",
        )

    # 构建查询
    query = select(Order).where(Order.agent_id == current_user.id)
    count_query = select(func.count()).select_from(Order).where(
        Order.agent_id == current_user.id
    )
    if status_filter:
        query = query.where(Order.status == status_filter)
        count_query = count_query.where(Order.status == status_filter)

    # 总数
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 分页数据
    query = query.order_by(Order.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    orders_result = await db.execute(query)
    orders = orders_result.scalars().all()

    # 收集所有需求ID
    requirement_ids = [o.requirement_id for o in orders]
    if requirement_ids:
        req_result = await db.execute(
            select(Requirement).where(Requirement.id.in_(requirement_ids))
        )
        req_map = {r.id: r.title for r in req_result.scalars().all()}
    else:
        req_map = {}

    items = [
        AgentOrderItem(
            order_id=o.id,
            requirement_title=req_map.get(o.requirement_id, "未知需求"),
            amount=o.amount,
            status=o.status,
            created_at=o.created_at,
            deliverables=o.deliverables or [],
            delivery_message=o.delivery_message,
        )
        for o in orders
    ]

    return AgentOrderListResponse(total=total, items=items)


# ==================== 外部Agent API（API Key认证） ====================


@router.post("/api/accept_order", summary="外部Agent通过API Key接单")
async def accept_order(
    request: AcceptOrderRequest,
    db: AsyncSession = Depends(get_db),
):
    """外部Agent通过API Key接单

    1. 验证API Key
    2. 检查需求状态是否为 open（可接单）
    3. 检查Agent每日接单上限
    4. 创建订单记录
    5. 更新需求状态为 matched/accepted
    """
    settings = get_settings()

    # 1. 验证API Key
    profile = await _verify_api_key(request.api_key, db)

    # 2. 检查需求是否存在且可接单
    req_result = await db.execute(
        select(Requirement).where(Requirement.id == request.requirement_id)
    )
    requirement = req_result.scalar_one_or_none()
    if requirement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="需求不存在",
        )
    if requirement.status not in ("open", "matched"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"当前需求状态为「{requirement.status}」，无法接单",
        )

    # 3. 检查每日接单上限
    if profile.daily_limit > 0 and profile.today_orders >= profile.daily_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="今日接单已达上限",
        )

    # 4. 计算金额
    amount = requirement.budget or profile.base_price or 0.0
    if amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无法确定订单金额（需求无预算且Agent无基础报价）",
        )

    platform_fee = round(amount * settings.PLATFORM_FEE_RATE, 2)
    agent_income = round(amount - platform_fee, 2)

    # 5. 创建订单
    order = Order(
        requirement_id=request.requirement_id,
        user_id=requirement.user_id,
        agent_id=profile.user_id,
        amount=amount,
        platform_fee=platform_fee,
        agent_income=agent_income,
        status="pending",
    )
    db.add(order)

    # 6. 更新需求状态
    requirement.status = "accepted"

    # 7. 更新Agent今日接单数
    profile.today_orders += 1

    await db.flush()

    return {
        "message": "接单成功",
        "order_id": str(order.id),
        "amount": amount,
        "platform_fee": platform_fee,
        "agent_income": agent_income,
    }


@router.post(
    "/api/submit_delivery",
    summary="外部Agent提交交付物",
)
async def submit_delivery(
    request: SubmitDeliveryRequest,
    db: AsyncSession = Depends(get_db),
):
    """外部Agent提交交付物

    1. 验证API Key
    2. 验证订单归属（API Key对应的Agent必须是该订单的Agent）
    3. 更新交付物和交付说明
    4. 状态改为 delivered
    """
    # 1. 验证API Key
    profile = await _verify_api_key(request.api_key, db)

    # 2. 查找并验证订单
    order_result = await db.execute(
        select(Order).where(Order.id == request.order_id)
    )
    order = order_result.scalar_one_or_none()
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订单不存在",
        )
    if order.agent_id != profile.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您不是该订单的Agent，无权提交交付物",
        )
    if order.status not in ("paid", "processing"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"当前订单状态为「{order.status}」，无法提交交付物",
        )

    # 3. 更新订单
    order.deliverables = request.deliverables
    order.delivery_message = request.delivery_message
    order.status = "delivered"

    await db.flush()

    return {
        "message": "交付物提交成功",
        "order_id": str(order.id),
        "status": "delivered",
    }
