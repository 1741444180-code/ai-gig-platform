"""Agent 能力管理 API — 3步注册 + API Key 管理 + 沙箱 + 接单工作台

3步注册流程：
1. 创建用户账号（复用认证模块）
2. 创建 Agent 能力卡（本模块）
3. 生成 API Key（支持多Key、Scope权限、沙箱环境）

外部 Agent 调用：
- 通过 API Key 认证（SHA-256 验证）
- 接单 / 提交交付物 / 查询订单
"""

import hashlib
import uuid as _uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import get_current_active_user
from app.db.database import get_db
from app.models.models import AgentProfile, AgentApiKey, Order, Requirement, User
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
from app.schemas.api_key import (
    ApiKeyCreateRequest,
    ApiKeyResponse,
    ApiKeyFullResponse,
    ApiKeyListResponse,
)
from app.services.ai_service import generate_agent_embedding
from app.services.api_key_service import generate_api_key, hash_api_key, check_scope_permission

router = APIRouter()
settings = get_settings()


# ==================== 工具函数 ====================


def _redact_api_key(full_key: str) -> str:
    """遮蔽 API Key，只显示前8位和后4位"""
    if len(full_key) < 12:
        return "***"
    return f"{full_key[:8]}...{full_key[-4:]}"


async def _verify_api_key_by_hash(
    api_key: str, db: AsyncSession, require_scope: str = "full"
) -> tuple[AgentProfile, AgentApiKey]:
    """通过 API Key 明文查找并验证（SHA-256 比对）

    Args:
        api_key: Agent 传入的 API Key 明文
        db: 数据库会话
        require_scope: 需要的最小权限级别

    Returns:
        (AgentProfile, AgentApiKey) 元组

    Raises:
        HTTPException: API Key 无效、未启用或权限不足
    """
    key_hash = hash_api_key(api_key)

    result = await db.execute(
        select(AgentApiKey).where(
            AgentApiKey.key_hash == key_hash,
            AgentApiKey.is_active == True,
        )
    )
    key_record = result.scalar_one_or_none()

    if key_record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 API Key",
        )

    # 更新最后使用时间
    key_record.last_used_at = datetime.now(timezone.utc)

    # 查找关联的 Agent Profile
    profile_result = await db.execute(
        select(AgentProfile).where(AgentProfile.user_id == key_record.agent_id)
    )
    profile = profile_result.scalar_one_or_none()

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key 关联的 Agent 不存在",
        )

    if profile.status != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent 状态异常，无法操作",
        )

    # 检查权限范围
    if not check_scope_permission(key_record.scope, "accept_order") and require_scope == "full":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="此 API Key 权限不足，需要 full 权限",
        )

    await db.flush()
    return profile, key_record


async def _get_agent_profile_for_user(
    user_id: _uuid.UUID, db: AsyncSession
) -> AgentProfile | None:
    """获取指定用户的 Agent Profile"""
    result = await db.execute(
        select(AgentProfile).where(AgentProfile.user_id == user_id)
    )
    return result.scalar_one_or_none()


# ==================== 第一步：注册 Agent 能力卡 ====================


@router.post("/register", response_model=AgentProfileResponse, summary="注册 Agent 能力卡")
async def register_agent(
    request: AgentRegisterRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """注册 Agent 能力卡（3步注册的第2步）

    - 每个用户只能注册一个 Agent Profile
    - 不生成 API Key（需要第3步单独创建）
    - 初始状态为「待审核」(status=0)
    - 自动生成能力描述向量（用于语义匹配）
    """
    # 检查是否已注册
    existing = await _get_agent_profile_for_user(current_user.id, db)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="您已注册过 Agent 能力卡，请使用更新接口或前往创建 API Key",
        )

    # 创建 Agent Profile
    profile = AgentProfile(
        user_id=current_user.id,
        name=request.agent.name,
        description=request.agent.description,
        tags=request.agent.tags,
        capabilities=request.agent.capabilities,
        base_price=request.agent.base_price,
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


# ==================== 第二步：更新 Agent 能力卡 ====================


@router.get("/me", response_model=AgentProfileResponse, summary="获取我的 Agent 信息")
async def get_my_agent(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的 Agent 能力卡信息"""
    profile = await _get_agent_profile_for_user(current_user.id, db)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="您尚未注册 Agent 能力卡",
        )
    return profile


@router.put("/me", response_model=AgentProfileResponse, summary="更新 Agent 能力卡")
async def update_my_agent(
    update_data: AgentProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """更新当前用户的 Agent 能力卡"""
    profile = await _get_agent_profile_for_user(current_user.id, db)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="您尚未注册 Agent 能力卡",
        )

    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(profile, key, value)

    # 如果描述或标签变更，重新生成向量
    if "description" in update_dict or "tags" in update_dict:
        embedding = await generate_agent_embedding(
            description=update_dict.get("description", profile.description),
            tags=update_dict.get("tags", profile.tags),
        )
        if embedding:
            profile.description_vec = embedding

    await db.flush()
    return profile


@router.post("/me/toggle_auto_accept", response_model=AgentProfileResponse, summary="切换自动接单开关")
async def toggle_auto_accept(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """切换 Agent 的自动接单开关"""
    profile = await _get_agent_profile_for_user(current_user.id, db)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="您尚未注册 Agent 能力卡",
        )

    profile.auto_accept = not profile.auto_accept
    await db.flush()
    return profile


# ==================== 第三步：API Key 管理 ====================


@router.post("/api-keys", response_model=ApiKeyFullResponse, summary="创建 API Key")
async def create_api_key(
    req: ApiKeyCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """创建新的 API Key（3步注册的第3步）

    - 每个 Agent 最多创建 10 个 Key
    - 支持 full（完整权限）和 sandbox（沙箱测试）两种 Scope
    - 完整 Key 仅在创建时返回一次，数据库只存 SHA-256 哈希
    """
    profile = await _get_agent_profile_for_user(current_user.id, db)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="您尚未注册 Agent 能力卡，请先注册能力卡",
        )

    # 检查 Key 数量限制
    key_count_result = await db.execute(
        select(func.count()).select_from(AgentApiKey).where(
            AgentApiKey.agent_id == current_user.id,
            AgentApiKey.is_active == True,
        )
    )
    key_count = key_count_result.scalar() or 0
    if key_count >= 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="每个 Agent 最多创建 10 个 API Key，请先吊销不用的 Key",
        )

    # 生成 Key
    full_key, key_prefix, key_hash = generate_api_key()

    # 存储到数据库（只存哈希）
    key_record = AgentApiKey(
        agent_id=current_user.id,
        key_name=req.key_name,
        key_prefix=key_prefix,
        key_hash=key_hash,
        scope=req.scope,
        is_sandbox=req.is_sandbox,
        is_active=True,
    )
    db.add(key_record)
    await db.flush()

    return ApiKeyFullResponse(
        id=key_record.id,
        full_key=full_key,  # 仅创建时返回
        key_name=key_record.key_name,
        key_prefix=key_record.key_prefix,
        scope=key_record.scope,
        is_sandbox=key_record.is_sandbox,
        created_at=key_record.created_at,
    )


@router.get("/api-keys", response_model=ApiKeyListResponse, summary="获取我的 API Key 列表")
async def list_api_keys(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的 API Key 列表（Key 明文已遮蔽）"""
    result = await db.execute(
        select(AgentApiKey)
        .where(AgentApiKey.agent_id == current_user.id)
        .order_by(AgentApiKey.created_at.desc())
    )
    keys = result.scalars().all()

    return ApiKeyListResponse(
        keys=[ApiKeyResponse.model_validate(k) for k in keys],
        total=len(keys),
    )


@router.delete("/api-keys/{key_id}", summary="吊销 API Key")
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """吊销指定的 API Key

    - 吊销后该 Key 立即失效
    - 不可恢复，需要重新创建
    """
    try:
        kid = _uuid.UUID(key_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的 Key ID 格式")

    result = await db.execute(
        select(AgentApiKey).where(
            AgentApiKey.id == kid,
            AgentApiKey.agent_id == current_user.id,
        )
    )
    key_record = result.scalar_one_or_none()

    if key_record is None:
        raise HTTPException(status_code=404, detail="API Key 不存在")

    if not key_record.is_active:
        raise HTTPException(status_code=400, detail="该 Key 已被吊销")

    key_record.is_active = False
    await db.flush()

    return {"message": "API Key 已吊销", "key_prefix": key_record.key_prefix}


# ==================== 接单工作台 ====================


@router.get("/orders", response_model=AgentOrderListResponse, summary="Agent 接单工作台")
async def get_agent_workbench(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status_filter: str | None = Query(None, description="按订单状态过滤"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Agent 接单工作台 — 查看分配给我的订单"""
    profile = await _get_agent_profile_for_user(current_user.id, db)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="您尚未注册 Agent 能力卡",
        )

    query = select(Order).where(Order.agent_id == current_user.id)
    count_query = select(func.count()).select_from(Order).where(
        Order.agent_id == current_user.id
    )
    if status_filter:
        query = query.where(Order.status == status_filter)
        count_query = count_query.where(Order.status == status_filter)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(Order.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    orders_result = await db.execute(query)
    orders = orders_result.scalars().all()

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


# ==================== 外部 Agent API（API Key 认证） ====================


@router.post("/api/accept_order", summary="外部 Agent 通过 API Key 接单")
async def accept_order(
    request: AcceptOrderRequest,
    db: AsyncSession = Depends(get_db),
):
    """外部 Agent 通过 API Key 接单

    1. 验证 API Key（SHA-256 比对）
    2. 检查需求状态是否为 open（可接单）
    3. 检查 Agent 每日接单上限
    4. 创建订单记录
    5. 更新需求状态为 accepted
    """
    # 1. 验证 API Key
    profile, key_record = await _verify_api_key_by_hash(request.api_key, db)

    # 2. 检查需求
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
            detail="无法确定订单金额（需求无预算且 Agent 无基础报价）",
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
        status="paid",  # MVP-Minimal 无支付，直接 paid
    )
    db.add(order)

    # 6. 更新需求状态
    requirement.status = "accepted"

    # 7. 更新 Agent 今日接单数
    profile.today_orders += 1

    await db.flush()

    return {
        "message": "接单成功",
        "order_id": str(order.id),
        "amount": amount,
        "platform_fee": platform_fee,
        "agent_income": agent_income,
    }


@router.post("/api/submit_delivery", summary="外部 Agent 提交交付物")
async def submit_delivery(
    request: SubmitDeliveryRequest,
    db: AsyncSession = Depends(get_db),
):
    """外部 Agent 提交交付物

    1. 验证 API Key
    2. 验证订单归属
    3. 更新交付物和状态
    """
    profile, key_record = await _verify_api_key_by_hash(request.api_key, db)

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
            detail="您不是该订单的 Agent，无权提交交付物",
        )
    if order.status not in ("paid", "processing"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"当前订单状态为「{order.status}」，无法提交交付物",
        )

    order.deliverables = request.deliverables
    order.delivery_message = request.delivery_message
    order.status = "delivered"

    await db.flush()

    return {
        "message": "交付物提交成功",
        "order_id": str(order.id),
        "status": "delivered",
    }


@router.get("/api/orders/{order_id}", summary="外部 Agent 查询订单")
async def api_get_order(
    order_id: str,
    api_key: str = Query(..., description="API Key"),
    db: AsyncSession = Depends(get_db),
):
    """外部 Agent 查询订单状态（轮询用）"""
    profile, key_record = await _verify_api_key_by_hash(api_key, db)

    import uuid as _uuid_mod
    try:
        oid = _uuid_mod.UUID(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的订单 ID 格式")

    result = await db.execute(select(Order).where(Order.id == oid))
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.agent_id != profile.user_id:
        raise HTTPException(status_code=403, detail="无权访问此订单")

    return {
        "order_id": str(order.id),
        "status": order.status,
        "amount": order.amount,
        "deliverables": order.deliverables or [],
        "created_at": order.created_at.isoformat() if order.created_at else None,
    }
