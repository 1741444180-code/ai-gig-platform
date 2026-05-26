"""支付服务模块 — 微信/支付宝 H5 支付 + Plan B 人工确认

MVP 阶段使用 Plan B：
- 用户下单后生成支付链接/二维码
- 管理员手动确认到账
- 后续替换为微信/支付宝分账 API

架构预留：
- WechatPayService / AlipayService 接口已定义
- 切换正式分账只需实现 call_api 方法
"""

import asyncio
import hashlib
import hmac
import logging
import time
from typing import Optional
import uuid

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


# ==================== Plan B — 人工确认支付 ====================

class ManualPaymentService:
    """Plan B 支付服务 — MVP 阶段使用

    流程：
    1. 用户选择支付方式 → 生成支付链接/二维码提示
    2. 用户扫码/转账 → 管理员手动确认到账
    3. 确认到账后 → 更新订单状态 + 释放资金
    """

    @staticmethod
    async def create_payment_url(
        order_id: str,
        amount: float,
        payment_method: str,
    ) -> dict:
        """生成支付链接/二维码提示

        MVP 阶段：返回模拟支付链接和说明文字。
        生产环境：调用微信/支付宝 H5 支付 API 生成真实支付链接。
        """
        if payment_method == "wechat":
            return {
                "pay_url": f"weixin://pay/mvp/{order_id}",
                "method": "wechat",
                "message": "请使用微信扫描下方二维码或转账",
                "qr_hint": "MVP阶段：请添加客服微信转账，备注订单号",
            }
        elif payment_method == "alipay":
            return {
                "pay_url": f"alipays://pay/mvp/{order_id}",
                "method": "alipay",
                "message": "请使用支付宝扫描下方二维码或转账",
                "qr_hint": "MVP阶段：请添加客服支付宝转账，备注订单号",
            }
        elif payment_method == "manual":
            return {
                "pay_url": None,
                "method": "manual",
                "message": "人工确认支付",
                "qr_hint": "请联系客服确认支付",
            }
        else:
            raise ValueError(f"不支持的支付方式: {payment_method}")

    @staticmethod
    async def confirm_payment(
        payment_id: str,
        transaction_id: str,
        raw_response: Optional[dict] = None,
    ) -> bool:
        """管理员手动确认支付到账"""
        logger.info(
            f"手动确认支付到账: payment_id={payment_id}, "
            f"transaction_id={transaction_id}"
        )
        return True

    @staticmethod
    async def refund(
        payment_id: str,
        amount: float,
        reason: str,
    ) -> dict:
        """退款处理

        MVP 阶段：记录退款请求，等待管理员手动处理。
        生产环境：调用微信/支付宝退款 API。
        """
        logger.info(
            f"退款请求: payment_id={payment_id}, amount={amount}, reason={reason}"
        )
        return {
            "status": "pending",
            "message": "退款请求已提交，等待处理",
            "refund_id": f"rf_{payment_id[:8]}",
        }


# ==================== 微信支付 ====================

class WechatPayService:
    """微信支付服务

    支持 APIv2 MD5 签名沙箱模式
    USE_MOCK_PAYMENT=true 时返回假链接
    """

    BASE_URL = "https://api.mch.weixin.qq.com"
    SANDBOX_URL = "https://api.mch.weixin.qq.com/sandboxnew"

    def __init__(self):
        self.app_id = settings.WECHAT_APP_ID
        self.app_secret = settings.WECHAT_APP_SECRET
        self.mch_id = settings.WECHAT_MCH_ID
        self.mch_key = settings.WECHAT_MCH_KEY
        self.use_mock = settings.USE_MOCK_PAYMENT

    def _sign_v2(self, params: dict) -> str:
        """APIv2 MD5 签名"""
        # 签名参数按字典序排列
        sorted_params = sorted(
            [(k, v) for k, v in params.items() if k not in ("sign", "sign_type") and v]
        )
        sign_str = "&".join([f"{k}={v}" for k, v in sorted_params])
        sign_str += f"&key={self.mch_key}"
        return hashlib.md5(sign_str.encode("utf-8")).hexdigest().upper()

    def _build_nonce_str(self) -> str:
        return uuid.uuid4().hex

    async def create_h5_payment(
        self,
        order_id: str,
        amount: float,
        description: str,
    ) -> dict:
        """创建微信 H5 支付 / 二维码支付

        沙箱模式 USE_MOCK_PAYMENT=true 返回假 mweb_url / code_url
        正式模式调用微信支付统一下单 API
        """
        if self.use_mock or not self.mch_id or not self.mch_key:
            logger.info(f"[WechatPay MOCK] order_id={order_id}, amount={amount}")
            return {
                "pay_url": f"weixin://pay/mvp/{order_id}",
                "code_url": f"weixin://qr/{order_id}",
                "mweb_url": f"https://wx.tenpay.com/mock/{order_id}",
                "method": "wechat",
                "message": "沙箱模式：模拟微信支付",
                "trade_type": "MWEB",
                "prepay_id": f"mock_{order_id[:8]}",
            }

        # 真实调用微信支付统一下单 API
        nonce_str = self._build_nonce_str()
        out_trade_no = f"ord_{order_id[:12]}_{int(time.time())}"

        params = {
            "appid": self.app_id,
            "mch_id": self.mch_id,
            "nonce_str": nonce_str,
            "body": description[:64],
            "out_trade_no": out_trade_no,
            "total_fee": int(amount * 100),  # 单位：分
            "spbill_create_ip": "127.0.0.1",
            "notify_url": f"{settings.WECHAT_NOTIFY_URL or 'http://localhost/callback'}",
            "trade_type": "NATIVE",  # 二维码支付
        }
        params["sign"] = self._sign_v2(params)

        import httpx
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self.BASE_URL}/pay/unifiedorder",
                data=params,
                headers={"Content-Type": "application/xml"},
            )
            result = resp.text

        logger.info(f"[WechatPay] unifiedorder response: {result}")

        # 简单解析 XML 响应
        code_url = self._extract_xml(result, "code_url")
        mweb_url = self._extract_xml(result, "mweb_url")
        prepay_id = self._extract_xml(result, "prepay_id")

        return {
            "pay_url": code_url or mweb_url,
            "code_url": code_url,
            "mweb_url": mweb_url,
            "prepay_id": prepay_id,
            "method": "wechat",
            "out_trade_no": out_trade_no,
        }

    def _extract_xml(self, xml_str: str, key: str) -> Optional[str]:
        """简单 XML 解析"""
        start = xml_str.find(f"<{key}>")
        if start == -1:
            return None
        start += len(f"<{key}>")
        end = xml_str.find(f"</{key}>", start)
        if end == -1:
            return None
        return xml_str[start:end]

    @staticmethod
    async def verify_callback(
        body: str,
        signature: str,
        serial: str,
        nonce: str,
        timestamp: str,
    ) -> dict:
        """验证微信支付回调签名（APIv3）

        TODO: 使用微信支付 APIv3 证书验证签名
        """
        raise NotImplementedError("微信支付回调验证未接入")

    @staticmethod
    async def refund(
        payment_id: str,
        amount: float,
        reason: str,
    ) -> dict:
        """微信退款

        TODO: 对接微信退款 API
        """
        raise NotImplementedError("微信支付退款未接入")


# ==================== 支付宝 ====================

class AlipayService:
    """支付宝服务

    支持手机网站支付（WapPayment）
    USE_MOCK_PAYMENT=true 时返回假链接
    """

    def __init__(self):
        self.app_id = settings.ALIPAY_APP_ID
        self.private_key = settings.ALIPAY_PRIVATE_KEY
        self.public_key = settings.ALIPAY_PUBLIC_KEY
        self.use_mock = settings.USE_MOCK_PAYMENT
        self.gateway = "https://openapi.alipaydev.com/gateway.do"  # 沙箱网关

    def _rsa_sign(self, params: dict) -> str:
        """RSA2 签名（预留）"""
        # 使用 cryptography 库签名，正式接入时实现
        return "mock_signature"

    async def create_wap_payment(
        self,
        order_id: str,
        amount: float,
        subject: str,
    ) -> dict:
        """创建支付宝 WAP 支付

        沙箱模式 USE_MOCK_PAYMENT=true 返回假跳转链接
        正式模式生成 alipay.trade.wap.pay 请求
        """
        if self.use_mock or not self.app_id or not self.private_key:
            logger.info(f"[Alipay MOCK] order_id={order_id}, amount={amount}")
            return {
                "pay_url": f"https://openapi.alipaydev.com/gateway.do?mock_order={order_id}",
                "method": "alipay",
                "message": "沙箱模式：模拟支付宝支付",
                "trade_no": f"mock_{order_id[:8]}_{int(time.time())}",
            }

        # 真实调用支付宝手机网站支付
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        out_trade_no = f"ord_{order_id[:12]}_{int(time.time())}"

        params = {
            "app_id": self.app_id,
            "method": "alipay.trade.wap.pay",
            "format": "JSON",
            "charset": "utf-8",
            "sign_type": "RSA2",
            "timestamp": timestamp,
            "version": "1.0",
            "notify_url": settings.ALIPAY_NOTIFY_URL or "http://localhost/callback",
            "biz_content": {
                "out_trade_no": out_trade_no,
                "total_amount": str(amount),
                "subject": subject[:100],
                "product_code": "QUICK_WAP_WAY",
            },
        }

        # 构建签名（简化版，实际用 alipay-sdk-python）
        sign_str = "&".join([f"{k}={v}" for k, v in params.items() if k != "biz_content"])
        sign_str += f"&biz_content={params['biz_content']}"

        import json
        params["biz_content"] = json.dumps(params["biz_content"])
        params["sign"] = self._rsa_sign(params)

        pay_url = f"{self.gateway}?" + "&".join([f"{k}={_quote(str(v))}" for k, v in params.items()])

        return {
            "pay_url": pay_url,
            "method": "alipay",
            "out_trade_no": out_trade_no,
        }

    @staticmethod
    async def refund(
        payment_id: str,
        amount: float,
        reason: str,
    ) -> dict:
        """支付宝退款

        TODO: 对接支付宝退款 API
        """
        raise NotImplementedError("支付宝退款未接入")


def _quote(s: str) -> str:
    import urllib.parse
    return urllib.parse.quote(s, safe="")


# ==================== 服务工厂 ====================

_wechat_service: Optional[WechatPayService] = None
_alipay_service: Optional[AlipayService] = None


def get_wechat_service() -> WechatPayService:
    global _wechat_service
    if _wechat_service is None:
        _wechat_service = WechatPayService()
    return _wechat_service


def get_alipay_service() -> AlipayService:
    global _alipay_service
    if _alipay_service is None:
        _alipay_service = AlipayService()
    return _alipay_service


def get_payment_service() -> ManualPaymentService:
    """获取当前支付服务实例

    MVP 阶段返回 ManualPaymentService。
    企业主体确定后根据配置返回 WechatPayService / AlipayService。
    """
    return ManualPaymentService()


# ==================== 独立支付函数（供 payments.py 调用） ====================

async def create_wechat_payment(
    order_id: str,
    amount: float,
    description: str = "AI订单支付",
) -> dict:
    """创建微信支付

    Returns:
        dict: 包含 pay_url, code_url, mweb_url 等
    """
    svc = get_wechat_service()
    return await svc.create_h5_payment(order_id, amount, description)


async def create_alipay_payment(
    order_id: str,
    amount: float,
    subject: str = "AI订单支付",
) -> dict:
    """创建支付宝支付

    Returns:
        dict: 包含 pay_url 等
    """
    svc = get_alipay_service()
    return await svc.create_wap_payment(order_id, amount, subject)