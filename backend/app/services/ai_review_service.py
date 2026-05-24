"""AI交付物质量评分服务 (ai-review-01).

输入需求描述+交付物内容 -> AI返回质量评分(0-100)+评分理由。
作为验收辅助参考，不替代人工判断。
"""

import json
import logging
from typing import Optional, Dict, Any

from app.config import settings

logger = logging.getLogger(__name__)

# 模拟模式标志
MOCK_MODE = not bool(settings.dashscope_api_key)


async def ai_review_delivery(
    demand_title: str,
    demand_description: str,
    delivery_content: Optional[str] = None,
    delivery_url: Optional[str] = None,
    category: Optional[str] = None,
    tags: Optional[str] = None,
) -> Dict[str, Any]:
    """AI验收评分：分析需求与交付物的匹配度，返回质量评分。

    Args:
        demand_title: 需求标题
        demand_description: 需求描述
        delivery_content: 交付物文本内容
        delivery_url: 交付物链接
        category: 需求分类
        tags: 需求标签JSON

    Returns:
        {
            "score": int,              # 质量评分 0-100
            "reason": str,             # 评分理由
            "strengths": [str],        # 优点列表
            "improvements": [str],     # 改进建议
            "completion_percent": int, # 完成度预估 0-100
        }
    """
    if MOCK_MODE:
        return _mock_review(
            demand_title=demand_title,
            demand_description=demand_description,
            delivery_content=delivery_content,
            delivery_url=delivery_url,
            category=category,
            tags=tags,
        )
    else:
        return await _ai_review(
            demand_title=demand_title,
            demand_description=demand_description,
            delivery_content=delivery_content,
            delivery_url=delivery_url,
            category=category,
            tags=tags,
        )


def _mock_review(
    demand_title: str,
    demand_description: str,
    delivery_content: Optional[str] = None,
    delivery_url: Optional[str] = None,
    category: Optional[str] = None,
    tags: Optional[str] = None,
) -> Dict[str, Any]:
    """模拟AI评分（基于文本匹配和长度分析）。"""
    score = 70  # 基础分
    reasons = []
    strengths = []
    improvements = []

    # 1. 交付物内容长度评分
    if delivery_content:
        content_len = len(delivery_content)
        if content_len > 500:
            score += 15
            strengths.append("交付内容详实")
        elif content_len > 100:
            score += 5
        else:
            score -= 10
            improvements.append("交付内容偏短，建议补充更多细节")
    elif delivery_url:
        score += 5
        strengths.append("已提供交付链接")
    else:
        score -= 20
        improvements.append("缺少交付内容")

    # 2. 标题匹配度（关键词重叠）
    if demand_title and delivery_content:
        title_keywords = set(demand_title.lower().split())
        delivery_words = set(delivery_content.lower().split())
        overlap = len(title_keywords & delivery_words)
        if overlap >= 3:
            score += 10
            strengths.append("内容与需求高度相关")
        elif overlap >= 1:
            score += 3
        else:
            score -= 5
            improvements.append("内容与需求标题关联度不高")

    # 3. 分类/标签匹配
    if category and delivery_content:
        if category.lower() in delivery_content.lower():
            score += 5

    # 4. 描述匹配度
    if demand_description and delivery_content:
        desc_keywords = set(demand_description.lower().split())
        if len(desc_keywords) > 0:
            match_ratio = len(desc_keywords & set(delivery_content.lower().split())) / len(desc_keywords)
            if match_ratio > 0.5:
                score += 10
                strengths.append("充分理解需求要求")
            elif match_ratio > 0.2:
                score += 3
            else:
                improvements.append("建议更深入理解需求细节")

    # 限制范围
    score = max(0, min(100, score))

    # 完成度估算
    completion_percent = min(100, 50 + (score - 30))

    if not improvements:
        improvements.append("整体表现良好，可继续保持")
    if not strengths:
        strengths.append("基础交付已完成")

    logger.info(f"[MOCK AI Review] score={score}, completion={completion_percent}")

    return {
        "score": score,
        "reason": f"AI辅助评分 {score}/100：{'; '.join(reasons) if reasons else '基于内容分析'}",
        "strengths": strengths,
        "improvements": improvements,
        "completion_percent": completion_percent,
    }


async def _ai_review(
    demand_title: str,
    demand_description: str,
    delivery_content: Optional[str] = None,
    delivery_url: Optional[str] = None,
    category: Optional[str] = None,
    tags: Optional[str] = None,
) -> Dict[str, Any]:
    """真实调用通义千问 API 进行验收评分。"""
    logger.warning("AI API key not configured, falling back to mock")
    return _mock_review(
        demand_title=demand_title,
        demand_description=demand_description,
        delivery_content=delivery_content,
        delivery_url=delivery_url,
        category=category,
        tags=tags,
    )


async def ai_arbitration_review(
    demand_title: str,
    demand_description: str,
    delivery_content: Optional[str] = None,
    delivery_url: Optional[str] = None,
    reject_reason: Optional[str] = None,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """AI辅助仲裁初裁 (ai-review-03)。

    分析需求与交付物的匹配度，给出建议退款比例和理由。

    Returns:
        {
            "suggested_refund_percent": int,   # 建议退款比例 0-100
            "suggested_resolution": str,       # 建议裁决: refund|partial_refund|release_agent|redeliver
            "reason": str,                     # 分析理由
            "match_score": int,                # 需求-交付物匹配度 0-100
        }
    """
    if MOCK_MODE:
        return _mock_arbitration(
            demand_title=demand_title,
            demand_description=demand_description,
            delivery_content=delivery_content,
            delivery_url=delivery_url,
            reject_reason=reject_reason,
            category=category,
        )
    else:
        return await _ai_arbitration_real(
            demand_title=demand_title,
            demand_description=demand_description,
            delivery_content=delivery_content,
            delivery_url=delivery_url,
            reject_reason=reject_reason,
            category=category,
        )


def _mock_arbitration(
    demand_title: str,
    demand_description: str,
    delivery_content: Optional[str] = None,
    delivery_url: Optional[str] = None,
    reject_reason: Optional[str] = None,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """模拟仲裁分析。"""
    # 先用验收评分做基础
    review = _mock_review(
        demand_title=demand_title,
        demand_description=demand_description,
        delivery_content=delivery_content,
        delivery_url=delivery_url,
        category=category,
    )

    match_score = review["score"]

    # 基于匹配度决定建议
    if match_score >= 80:
        suggested_refund = 0
        resolution = "release_agent"
        reason = "交付物质量良好，建议放款给Agent"
    elif match_score >= 60:
        suggested_refund = 30
        resolution = "partial_refund"
        reason = "交付物基本满足需求但存在不足，建议部分退款30%"
    elif match_score >= 40:
        suggested_refund = 50
        resolution = "partial_refund"
        reason = "交付物与需求有较大差距，建议部分退款50%"
    elif match_score >= 20:
        suggested_refund = 80
        resolution = "partial_refund"
        reason = "交付物质量较差，建议大部分退款80%"
    else:
        suggested_refund = 100
        resolution = "refund"
        reason = "交付物严重不符合需求，建议全额退款"

    # 考虑拒绝原因
    if reject_reason and "未完成" in reject_reason:
        suggested_refund = min(100, suggested_refund + 20)
        reason += f"；用户反馈'{reject_reason}'"
        resolution = "refund" if suggested_refund >= 80 else resolution

    logger.info(f"[MOCK AI Arbitration] match_score={match_score}, resolution={resolution}, refund={suggested_refund}%")

    return {
        "suggested_refund_percent": suggested_refund,
        "suggested_resolution": resolution,
        "reason": reason,
        "match_score": match_score,
    }


async def _ai_arbitration_real(
    demand_title: str,
    demand_description: str,
    delivery_content: Optional[str] = None,
    delivery_url: Optional[str] = None,
    reject_reason: Optional[str] = None,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """真实调用通义千问 API 进行仲裁分析。"""
    logger.warning("AI API key not configured, falling back to mock")
    return _mock_arbitration(
        demand_title=demand_title,
        demand_description=demand_description,
        delivery_content=delivery_content,
        delivery_url=delivery_url,
        reject_reason=reject_reason,
        category=category,
    )
