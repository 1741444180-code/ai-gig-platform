"""支付服务模块 — 微信/支付宝 H5 支付 + Plan B 人工确认

MVP 阶段使用 Plan B：
- 用户下单后生成支付链接/二维码
- 管理员手动确认到账
- 后续替换为微信/支付宝分账 API

架构预留：
- WechatPayService / AlipayService 接口已定义
- 切换正式分账只需实现 call_api 方法
"""

import logging
from typing import Optional

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
                "pay_url": f"weixin://pay/mvp/{order_id}",  # MVP 模拟链接
                "method": "wechat",
                "message": "请使用微信扫描下方二维码或转账",
                "qr_hint": "MVP阶段：请添加客服微信转账，备注订单号",
            }
        elif payment_method == "alipay":
            return {
                "pay_url": f"alipays://pay/mvp/{order_id}",  # MVP 模拟链接
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
        """管理员手动确认支付到账

        Args:
            payment_id: 支付记录 ID
            transaction_id: 交易流水号
            raw_response: 原始响应数据

        Returns:
            True 表示确认成功
        """
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


# ==================== 微信支付（预留） ====================

class WechatPayService:
    """微信支付服务 — 企业主体确定后实现"""

    @staticmethod
    async def create_h5_payment(
        order_id: str,
        amount: float,
        description: str,
    ) -> dict:
        """创建微信 H5 支付

        TODO: 对接微信支付 H5 下单 API
        参考: https://pay.weixin.qq.com/wiki/doc/apiv3/apis/chapter3_3_1.shtml
        """
        raise NotImplementedError("微信支付未接入，请先使用 Plan B 人工确认")

    @staticmethod
    async def verify_callback(
        body: str,
        signature: str,
        serial: str,
        nonce: str,
        timestamp: str,
    ) -> dict:
        """验证微信支付回调签名

        TODO: 使用微信支付 APIv3 证书验证签名
        """
        raise NotImplementedError("微信支付未接入")

    @staticmethod
    async def refund(
        payment_id: str,
        amount: float,
        reason: str,
    ) -> dict:
        """微信退款

        TODO: 对接微信退款 API
        """
        raise NotImplementedError("微信支付未接入")


# ==================== 支付宝（预留） ====================

class AlipayService:
    """支付宝服务 — 企业主体确定后实现"""

    @staticmethod
    async def create_wap_payment(
        order_id: str,
        amount: float,
        subject: str,
    ) -> str:
        """创建支付宝 WAP 支付

        TODO: 对接支付宝手机网站支付 API
        """
        raise NotImplementedError("支付宝未接入")

    @staticmethod
    async def refund(
        payment_id: str,
        amount: float,
        reason: str,
    ) -> dict:
        """支付宝退款

        TODO: 对接支付宝退款 API
        """
        raise NotImplementedError("支付宝未接入")


# ==================== 服务工厂 ====================

def get_payment_service() -> ManualPaymentService:
    """获取当前支付服务实例

    MVP 阶段返回 ManualPaymentService。
    企业主体确定后根据配置返回 WechatPayService / AlipayService。
    """
    return ManualPaymentService()
