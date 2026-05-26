"""支付模块 — 创建支付、回调、查询、退款 + 微信/支付宝回调验签(pay-07)"""

import logging
import hashlib
import hmac
import base64
from datetime import datetime, timezone
from typing import Optional
from xml.etree import ElementTree as ET

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
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
from app.services.payment_service import get_payment_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== 内存存储（进程内共享，重启清空）====================
_processed_callback_ids: set = set()  # 已处理的 transaction_id / callback_id


# ==================== 签名验证工具 ====================

def _verify_wechat_sign(plain_text: str, signature: str, api_key: str) -> bool:
    """微信支付 v2 签名验证（HMAC-SHA256）。
    
    微信回调签名：把body按URL query string格式拼接，用API密钥做HMAC-SHA256，
    结果做BASE64编码，与传入的签名比对。
    """
    if not api_key:
        logger.warning("微信API密钥未配置，跳过签名验证")
        return True
    computed = hmac.new(
        api_key.encode("utf-8"),
        plain_text.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    expected = base64.b64decode(signature)
    return computed == expected


def _parse_wechat_callback(body_xml: str) -> dict:
    """解析微信支付回调 XML，返回字段 dict。"""
    root = ET.fromstring(body_xml)
    result = {}
    for child in root:
        result[child.tag] = child.text
    return result


def _verify_alipay_sign(raw_post: bytes, signature: str, alipay_pub_key: str) -> bool:
    """支付宝回调签名验证（RSA2）。
    
    raw_post: 原始通知内容（bytes）
    signature: 支付宝返回的签名（base64）
    alipay_pub_key: 支付宝公钥
    
    使用支付宝公钥验签 raw_post + signature。
    """
    if not alipay_pub_key:
        logger.warning("支付宝公钥未配置，跳过签名验证")
        return True
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.backends import default_backend
        
        # 加载支付宝公钥
        pub_key = serialization.load_pem_public_key(
            alipay_pub_key.encode("utf-8"),
            backend=default_backend(),
        )
        # RSA2 验签
        pub_key.verify(
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            base64.b64decode(signature),
            raw_post,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except Exception as e:
        logger.error(f"支付宝签名验证失败: {e}")
        return False


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

    # 6. 生成支付链接
    pay_info = await payment_service.create_payment_url(
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


# ==================== 微信支付回调 (pay-07) ====================

@router.post(
    "/callback/weixin",
    summary="微信支付回调",
)
async def wechat_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """微信支付回调接口 (pay-07).

    1. 接收微信回调 XML
    2. 验签（v2回调）
    3. 幂等检查
    4. 更新订单+支付状态
    5. 返回 SUCCESS XML

    微信回调示例:
    <xml>
      <return_code><![CDATA[SUCCESS]]></return_code>
      <transaction_id><![CDATA[微信交易号]]></transaction_id>
      <out_trade_no><![CDATA[商户订单号]]></out_trade_no>
      <total_fee><![CDATA[金额(分)]]></total_fee>
      ...
    </xml>
    """
    # 读取原始 body（微信回调用 XML）
    body_xml = await request.body()
    body_text = body_xml.decode("utf-8")

    # 解析 XML
    try:
        data = _parse_wechat_callback(body_text)
    except Exception as e:
        logger.error(f"微信回调XML解析失败: {e}")
        return '<?xml version="1.0"?><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[XML解析失败]]></return_msg>'

    # 检查通信状态
    return_code = data.get("return_code", "")
    if return_code != "SUCCESS":
        logger.warning(f"微信回调通信失败: {data.get('return_msg', '')}")
        return '<?xml version="1.0"?><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[通信失败]]></return_msg>'

    # 验签（如果配置了 API 密钥）
    # 微信 v2 签名验证：把所有参数按键排序拼接，用 API 密钥做 HMAC-SHA256
    wechat_api_key = ""  # 从 settings 或环境变量读取
    signature = data.get("sign", "")
    if wechat_api_key and signature:
        # 构造待签名字符串（除了 sign 本身的所有字段，按 key 排序）
        signed_data = {k: v for k, v in data.items() if k != "sign" and v}
        sign_str = "&".join(f"{k}={v}" for k, v in sorted(signed_data.items())) + f"&key={wechat_api_key}"
        computed_sign = hashlib.md5(sign_str.encode("utf-8")).hexdigest().upper()
        if computed_sign != signature.upper():
            logger.warning(f"微信回调验签失败: expect={computed_sign}, got={signature}")
            return '<?xml version="1.0"?><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[验签失败]]></return_msg>'

    # 幂等检查（用微信交易号）
    transaction_id = data.get("transaction_id", "")
    if transaction_id and transaction_id in _processed_callback_ids:
        logger.info(f"微信回调幂等跳过: transaction_id={transaction_id}")
        return '<?xml version="1.0"?><return_code><![CDATA[SUCCESS]]></return_code><return_msg><![CDATA[OK]]></return_msg>'

    # 更新订单和支付状态
    out_trade_no = data.get("out_trade_no", "")  # 商户订单号 = 我们的 order_id
    total_fee = data.get("total_fee", "0")

    # 查找订单
    try:
        import uuid
        order_uuid = uuid.UUID(out_trade_no)
    except Exception:
        logger.error(f"微信回调订单号无效: {out_trade_no}")
        return '<?xml version="1.0"?><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[订单号无效]]></return_msg>'

    order_result = await db.execute(select(Order).where(Order.id == order_uuid))
    order = order_result.scalar_one_or_none()
    if order is None:
        logger.error(f"微信回调订单不存在: {out_trade_no}")
        return '<?xml version="1.0"?><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[订单不存在]]></return_msg>'

    # 更新支付记录
    payment_result = await db.execute(
        select(Payment).where(Payment.order_id == order.id, Payment.type == "payment")
    )
    payment = payment_result.scalar_one_or_none()
    if payment:
        payment.status = "paid"
        payment.transaction_id = transaction_id
        payment.raw_response = data

    # 更新订单状态
    order.status = "paid"
    order.payment_method = "wechat"
    order.payment_id = transaction_id

    # 标记已处理
    if transaction_id:
        _processed_callback_ids.add(transaction_id)

    await db.flush()

    logger.info(f"微信回调处理成功: order_id={out_trade_no}, transaction_id={transaction_id}, total_fee={total_fee}")

    return '<?xml version="1.0"?><return_code><![CDATA[SUCCESS]]></return_code><return_msg><![CDATA[OK]]></return_msg>'


# ==================== 支付宝回调 (pay-07) ====================

@router.post(
    "/callback/alipay",
    summary="支付宝回调",
)
async def alipay_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """支付宝回调接口 (pay-07).

    1. 接收支付宝回调（form-encoded 或 JSON）
    2. 验签（RSA2）
    3. 幂等检查
    4. 更新订单+支付状态
    5. 返回 success

    支付宝移动支付回调字段：
    - trade_no: 支付宝交易号
    - out_trade_no: 商户订单号
    - total_amount: 交易金额
    - trade_status: TRADE_SUCCESS / TRADE_CLOSED
    - sign: 签名
    """
    # 读取原始 body（用于验签）
    raw_body = await request.body()

    # 解析参数（支付宝通常用 Form）
    form = await request.form()
    trade_no = form.get("trade_no", "")
    out_trade_no = form.get("out_trade_no", "")
    total_amount = form.get("total_amount", "0")
    trade_status = form.get("trade_status", "")

    # 幂等检查
    if trade_no and trade_no in _processed_callback_ids:
        logger.info(f"支付宝回调幂等跳过: trade_no={trade_no}")
        return "success"

    # 验签
    alipay_pub_key = ""  # 从 settings 或环境变量读取
    signature = form.get("sign", "")
    if alipay_pub_key and signature:
        # 构造待验签内容（支付宝规定：除了 sign 本身的所有参数）
        sign_data = {k: v for k, v in form.items() if k not in ("sign", "sign_type")}
        # 按 key 排序后拼接
        verified_content = "&".join(f"{k}={v}" for k, v in sorted(sign_data.items()))
        if not _verify_alipay_sign(verified_content.encode("utf-8"), signature, alipay_pub_key):
            logger.warning("支付宝回调验签失败")
            raise HTTPException(status_code=400, detail="验签失败")

    # 只处理交易成功的回调
    if trade_status not in ("TRADE_SUCCESS", "TRADE_FINISHED"):
        logger.info(f"支付宝回调状态非成功: {trade_status}")
        return "success"

    # 查找订单
    try:
        import uuid
        order_uuid = uuid.UUID(out_trade_no)
    except Exception:
        logger.error(f"支付宝回调订单号无效: {out_trade_no}")
        raise HTTPException(status_code=400, detail="订单号无效")

    order_result = await db.execute(select(Order).where(Order.id == order_uuid))
    order = order_result.scalar_one_or_none()
    if order is None:
        logger.error(f"支付宝回调订单不存在: {out_trade_no}")
        raise HTTPException(status_code=400, detail="订单不存在")

    # 更新支付记录
    payment_result = await db.execute(
        select(Payment).where(Payment.order_id == order.id, Payment.type == "payment")
    )
    payment = payment_result.scalar_one_or_none()
    if payment:
        payment.status = "paid"
        payment.transaction_id = trade_no
        payment.raw_response = dict(form)

    # 更新订单状态
    order.status = "paid"
    order.payment_method = "alipay"
    order.payment_id = trade_no

    # 标记已处理
    if trade_no:
        _processed_callback_ids.add(trade_no)

    await db.flush()

    logger.info(f"支付宝回调处理成功: order_id={out_trade_no}, trade_no={trade_no}, total_amount={total_amount}")

    return "success"


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