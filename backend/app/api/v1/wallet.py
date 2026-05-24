"""Wallet API endpoints — 收益钱包+提现 (wallet-01~05)."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_db
from app.models.agent import Agent
from app.models.order import Order
from app.models.withdraw import Withdraw
from app.core.security import get_current_user
from app.models.user import User
from app.services.agent_key_service import get_current_agent

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────

class WalletInfoResponse(BaseModel):
    balance: float
    frozen_balance: float
    total_earned: float
    agent_id: str

class WithdrawRequest(BaseModel):
    amount: float
    payment_method: str  # alipay | wechat | bank
    account_info: Optional[str] = None

class WithdrawResponse(BaseModel):
    id: str
    agent_id: str
    amount: float
    payment_method: str
    account_info: Optional[str]
    status: str
    admin_note: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class WithdrawListResponse(BaseModel):
    items: list[WithdrawResponse]
    total: int
    page: int
    page_size: int

class TransactionResponse(BaseModel):
    id: str
    order_id: Optional[str]
    type: str  # income | withdraw_freeze | withdraw_release | withdraw_complete
    amount: float
    before_balance: float
    after_balance: float
    created_at: datetime

class TransactionListResponse(BaseModel):
    items: list[TransactionResponse]
    total: int
    page: int
    page_size: int


# ── wallet-01: 查询钱包信息 ──────────────────────────────────────

@router.get("/my", response_model=WalletInfoResponse)
async def get_wallet_info(
    agent: Agent = Depends(get_current_agent),
):
    """查询Agent钱包信息 (wallet-01)."""
    return WalletInfoResponse(
        balance=agent.balance,
        frozen_balance=agent.frozen_balance,
        total_earned=agent.total_earned,
        agent_id=agent.id,
    )


# ── wallet-02: 收益计算 ──────────────────────────────────────────

async def credit_agent_earnings(order_id: str, db: AsyncSession):
    """订单完成后自动计算收益 (wallet-02).
    
    订单completed → 计算Agent收入(balance += price - platform_fee) → 记录收入日志。
    自有Agent(platform_fee=0)全额入账。
    """
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order or order.status != "completed":
        return
    
    agent_result = await db.execute(select(Agent).where(Agent.id == order.agent_id))
    agent = agent_result.scalar_one_or_none()
    if not agent:
        return
    
    earnings = order.price - order.platform_fee
    agent.balance += earnings
    agent.total_earned += earnings
    await db.commit()


# ── wallet-03: 提现申请 ──────────────────────────────────────────

@router.post("/withdraw", response_model=WithdrawResponse)
async def request_withdraw(
    req: WithdrawRequest,
    db: AsyncSession = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    """Agent提交提现申请 (wallet-03).
    
    检查余额 → 冻结金额 → 创建提现申请。
    """
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="提现金额必须大于0")
    if req.amount > agent.balance:
        raise HTTPException(
            status_code=400,
            detail=f"余额不足。当前余额: {agent.balance}, 申请: {req.amount}",
        )
    
    # 冻结余额
    agent.balance -= req.amount
    agent.frozen_balance += req.amount
    
    # 创建提现记录
    withdraw = Withdraw(
        agent_id=agent.id,
        amount=req.amount,
        payment_method=req.payment_method,
        account_info=req.account_info,
        status="pending",
    )
    db.add(withdraw)
    await db.commit()
    await db.refresh(withdraw)
    
    return withdraw


# ── wallet-04: 管理员提现审核 ────────────────────────────────────

@router.get("/withdraws/admin", response_model=WithdrawListResponse)
async def admin_list_withdraws(
    status_filter: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """管理员查看提现申请列表 (wallet-04)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    query = select(Withdraw)
    if status_filter:
        query = query.where(Withdraw.status == status_filter)
    
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    query = query.order_by(Withdraw.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()
    
    return WithdrawListResponse(
        items=list(items),
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/withdraws/{withdraw_id}/approve", response_model=WithdrawResponse)
async def admin_approve_withdraw(
    withdraw_id: str,
    req_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """管理员审核通过提现 (wallet-04)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    result = await db.execute(select(Withdraw).where(Withdraw.id == withdraw_id))
    withdraw = result.scalar_one_or_none()
    if not withdraw:
        raise HTTPException(status_code=404, detail="提现申请不存在")
    if withdraw.status != "pending":
        raise HTTPException(status_code=400, detail="仅待审核的提现可处理")
    
    admin_note = req_data.get("admin_note", "") if req_data else ""
    
    withdraw.status = "approved"
    withdraw.admin_id = current_user.id
    withdraw.admin_note = admin_note
    withdraw.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(withdraw)
    
    return withdraw


@router.post("/withdraws/{withdraw_id}/reject", response_model=WithdrawResponse)
async def admin_reject_withdraw(
    withdraw_id: str,
    req_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """管理员拒绝提现 → 解冻余额 (wallet-04)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    result = await db.execute(select(Withdraw).where(Withdraw.id == withdraw_id))
    withdraw = result.scalar_one_or_none()
    if not withdraw:
        raise HTTPException(status_code=404, detail="提现申请不存在")
    if withdraw.status != "pending":
        raise HTTPException(status_code=400, detail="仅待审核的提现可处理")
    
    admin_note = req_data.get("admin_note", "") if req_data else ""
    
    # 解冻余额
    agent_result = await db.execute(select(Agent).where(Agent.id == withdraw.agent_id))
    agent = agent_result.scalar_one_or_none()
    if agent:
        agent.frozen_balance -= withdraw.amount
        agent.balance += withdraw.amount
    
    withdraw.status = "rejected"
    withdraw.admin_id = current_user.id
    withdraw.admin_note = admin_note
    withdraw.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(withdraw)
    
    return withdraw


# ── wallet-05: 收益明细查询 ──────────────────────────────────────

@router.get("/transactions", response_model=TransactionListResponse)
async def get_transactions(
    type_filter: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    """收益明细分页列表 (wallet-05).
    
    返回收入/提现明细。
    """
    query = select(Withdraw).where(Withdraw.agent_id == agent.id)
    if type_filter == "income":
        query = query.where(Withdraw.status == "completed")
    
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    query = query.order_by(Withdraw.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()
    
    transactions = []
    for item in items:
        transactions.append(TransactionResponse(
            id=item.id,
            order_id=None,
            type="withdraw_freeze" if item.status == "pending" else "withdraw_complete",
            amount=item.amount,
            before_balance=0,
            after_balance=0,
            created_at=item.created_at,
        ))
    
    return TransactionListResponse(
        items=transactions,
        total=total,
        page=page,
        page_size=page_size,
    )
