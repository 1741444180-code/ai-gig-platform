"""支付模块 — 创建支付、回调、查询、退款"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_active_user
from app.db.database import get_db
from app.models.models import Payment, User, Order
from app.schemas.payment import (
    PaymentCallbackRequest,
    PaymentCreateRequest,
    PaymentCreateResponse,
    PaymentListResponse,
    PaymentResponse,
    RefundRequest,
)
from app.services.payment_service import (
    get_payment_service,
    create_wechat_payment,
    create_alipay_payment,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== 创建支付 ====================

@router.post(
    "/create",
    response_model=PaymentCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建支付订单",
)
async def create_payment(
    req: PaymentCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """创建支付订单

    1. 验证订单归属（仅需求方可支付）
    2. 验证订单金额
    3. 创建支付记录
    4. 返回支付链接/二维码提示
    """
    payment_service = get_payment_service()

    # 1. 查找订单
    order_result = await db.execute(select(Order).where(Order.id == req.order_id))
    order = order_result.scalar_one_or_none()
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订单不存在",
        )

    # 2. 权限校验：仅需求方可支付
    if str(order.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅需求方可支付此订单",
        )

    # 3. 状态校验：只有 pending 状态的订单可以支付
    if order.status not in ("pending", "matched"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"订单当前状态为「{order.status}」，无法支付",
        )

    # 4. 检查是否已有待支付的支付记录
    existing = await db.execute(
        select(Payment).where(
            Payment.order_id == order.id,
            Payment.status == "pending",
            Payment.type == "payment",
        )
    )
    existing_payment = existing.scalar_one_or_none()

    if existing_payment:
        # 已有待支付记录，返回原记录
        pay_info = await payment_service.create_payment_url(
            order_id=str(order.id),
            amount=order.amount,
            payment_method=req.payment_method,
        )
        return PaymentCreateResponse(
            payment_id=existing_payment.id,
            order_id=existing_payment.order_id,
            amount=existing_payment.amount,
            payment_method=existing_payment.payment_method,
            status=existing_payment.status,
            pay_url=pay_info.get("pay_url"),
            created_at=existing_payment.created_at,
        )

    # 5. 创建支付记录
    payment = Payment(
        order_id=order.id,
        user_id=current_user.id,
        amount=order.amount,
        payment_method=req.payment_method,
        status="pending",
        type="payment",
    )
    db.add(payment)
    await db.flush()
    await db.refresh(payment)

    # 6. 根据支付方式生成支付链接
    if req.payment_method == "wechat":
        pay_info = await create_wechat_payment(
            order_id=str(order.id),
            amount=order.amount,
            description=f"AI订单-{order.id}",
        )
    elif req.payment_method == "alipay":
        pay_info = await create_alipay_payment(
            order_id=str(order.id),
            amount=order.amount,
            subject=f"AI订单-{order.id}",
        )
    else:
        # fallback: manual / 其他
        pay_info = await get_payment_service().create_payment_url(
            order_id=str(order.id),
            amount=order.amount,
            payment_method=req.payment_method,
        )

    logger.info(f"用户 {current_user.id} 创建支付: order_id={order.id}, amount={order.amount}")

    return PaymentCreateResponse(
        payment_id=payment.id,
        order_id=payment.order_id,
        amount=payment.amount,
        payment_method=payment.payment_method,
        status=payment.status,
        pay_url=pay_info.get("pay_url"),
        created_at=payment.created_at,
    )


# ==================== 支付回调 ====================

@router.post(
    "/callback",
    summary="支付平台回调（微信/支付宝）",
)
async def payment_callback(
    req: PaymentCallbackRequest,
    db: AsyncSession = Depends(get_db),
):
    """支付平台回调接口

    MVP 阶段：此接口由管理员手动调用确认到账。
    生产环境：由微信/支付宝异步回调触发。

    1. 查找支付记录
    2. 更新支付状态为 paid
    3. 更新订单状态为 paid
    """
    # 1. 查找支付记录
    payment_result = await db.execute(
        select(Payment).where(Payment.order_id == req.order_id, Payment.type == "payment")
    )
    payment = payment_result.scalar_one_or_none()
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到对应的支付记录",
        )

    # 2. 更新支付记录
    payment.status = "paid"
    payment.transaction_id = req.transaction_id
    if req.raw_data:
        payment.raw_response = req.raw_data

    # 3. 更新订单状态
    order_result = await db.execute(select(Order).where(Order.id == req.order_id))
    order = order_result.scalar_one_or_none()
    if order:
        order.status = "paid"
        order.payment_method = payment.payment_method
        order.payment_id = req.transaction_id

    await db.flush()

    logger.info(
        f"支付回调处理成功: order_id={req.order_id}, "
        f"transaction_id={req.transaction_id}"
    )

    return {
        "message": "支付确认成功",
        "order_id": str(req.order_id),
        "status": "paid",
    }


# ==================== 手动确认支付（管理员） ====================

@router.post(
    "/admin/confirm/{payment_id}",
    summary="管理员手动确认支付",
)
async def admin_confirm_payment(
    payment_id: str,
    transaction_id: str = Query(..., description="交易流水号"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """管理员手动确认支付到账（MVP Plan B）

    仅管理员可操作。
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")

    import uuid as _uuid
    try:
        pid = _uuid.UUID(payment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的支付ID格式")

    # 查找支付记录
    result = await db.execute(select(Payment).where(Payment.id == pid))
    payment = result.scalar_one_or_none()
    if payment is None:
        raise HTTPException(status_code=404, detail="支付记录不存在")

    if payment.status == "paid":
        raise HTTPException(status_code=400, detail="该支付已确认")

    # 更新支付状态
    payment.status = "paid"
    payment.transaction_id = transaction_id

    # 更新关联订单状态
    order_result = await db.execute(select(Order).where(Order.id == payment.order_id))
    order = order_result.scalar_one_or_none()
    if order:
        order.status = "paid"
        order.payment_method = payment.payment_method
        order.payment_id = transaction_id

    await db.flush()

    logger.info(f"管理员手动确认支付: payment_id={payment_id}")

    return {
        "message": "支付确认成功",
        "payment_id": str(payment.id),
        "order_id": str(payment.order_id),
        "status": "paid",
    }


# ==================== 查询支付 ====================

@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
    summary="查询支付记录",
)
async def get_payment(
    payment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """查询支付记录详情

    仅支付记录关联用户或管理员可查看。
    """
    import uuid as _uuid
    try:
        pid = _uuid.UUID(payment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的支付ID格式")

    result = await db.execute(select(Payment).where(Payment.id == pid))
    payment = result.scalar_one_or_none()
    if payment is None:
        raise HTTPException(status_code=404, detail="支付记录不存在")

    # 权限校验
    if (
        str(payment.user_id) != str(current_user.id)
        and current_user.role != "admin"
    ):
        raise HTTPException(status_code=403, detail="无权查看此支付记录")

    return PaymentResponse.model_validate(payment)


@router.get(
    "/mine",
    response_model=PaymentListResponse,
    summary="我的支付记录",
)
async def list_my_payments(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取当前用户的支付记录列表"""
    offset = (page - 1) * page_size

    # 总数
    count_result = await db.execute(
        select(func.count()).select_from(Payment).where(Payment.user_id == current_user.id)
    )
    total = count_result.scalar() or 0

    # 分页查询
    result = await db.execute(
        select(Payment)
        .where(Payment.user_id == current_user.id)
        .order_by(Payment.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    payments = result.scalars().all()

    return PaymentListResponse(
        payments=[PaymentResponse.model_validate(p) for p in payments],
        total=total,
        page=page,
        page_size=page_size,
    )


# ==================== 退款 ====================

@router.post(
    "/refund",
    summary="申请退款",
)
async def request_refund(
    req: RefundRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """申请退款

    1. 验证订单归属
    2. 创建退款支付记录
    3. MVP 阶段：记录退款请求，等待管理员手动处理
    """
    payment_service = get_payment_service()

    # 1. 查找订单
    order_result = await db.execute(select(Order).where(Order.id == req.order_id))
    order = order_result.scalar_one_or_none()
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订单不存在",
        )

    # 2. 权限校验：仅需求方可退款
    if str(order.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅需求方可退款此订单",
        )

    # 3. 状态校验：已支付的订单才能退款
    if order.status not in ("paid", "processing", "delivered"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"订单当前状态为「{order.status}」，无法退款",
        )

    # 4. 查找已支付的支付记录
    payment_result = await db.execute(
        select(Payment).where(
            Payment.order_id == order.id,
            Payment.status == "paid",
            Payment.type == "payment",
        )
    )
    original_payment = payment_result.scalar_one_or_none()
    if original_payment is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="未找到已支付的支付记录",
        )

    # 5. 创建退款记录
    refund_payment = Payment(
        order_id=order.id,
        user_id=current_user.id,
        amount=order.amount,
        payment_method=original_payment.payment_method,
        status="pending",
        type="refund",
        raw_response={"reason": req.reason},
    )
    db.add(refund_payment)

    # 6. 调用退款服务
    refund_info = await payment_service.refund(
        payment_id=str(original_payment.id),
        amount=order.amount,
        reason=req.reason,
    )

    await db.flush()

    logger.info(f"用户 {current_user.id} 申请退款: order_id={order.id}, amount={order.amount}")

    return {
        "message": "退款申请已提交",
        "refund_id": str(refund_payment.id),
        "order_id": str(order.id),
        "amount": order.amount,
        "status": refund_info.get("status", "pending"),
    }
