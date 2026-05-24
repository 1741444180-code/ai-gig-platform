"""AI验收评分 + 仲裁分析 集成测试 (ai-review-01~03).

Coverage: 交付物评分/评分端点/仲裁分析.
"""

import pytest
from app.services.ai_review_service import (
    ai_review_delivery,
    ai_arbitration_review,
    _mock_review,
    _mock_arbitration,
)


@pytest.mark.asyncio
async def test_ai_review_rich_content_scores_high():
    """内容详实的交付物应获得高分。"""
    result = await ai_review_delivery(
        demand_title="需要一篇产品推广文案",
        demand_description="介绍新产品功能，面向企业客户，200字以内",
        delivery_content="""
        产品推广文案
        企业级AI解决方案——提升团队效率300%
        我们的新一代智能平台集成了机器学习和自动化工作流，
        帮助企业快速构建数据驱动的决策系统。
        核心功能包括智能分析、自动报表、实时监控和预测模型。
        立即体验，让您的团队领先一步。
        """,
        category="文案",
        tags='["文案","营销","推广"]',
    )
    assert "score" in result
    assert result["score"] >= 70
    assert len(result["strengths"]) > 0
    assert result["completion_percent"] >= 50


@pytest.mark.asyncio
async def test_ai_review_empty_delivery_scores_low():
    """缺少交付内容的应获得低分。"""
    result = await ai_review_delivery(
        demand_title="复杂数据分析报告",
        demand_description="需要分析5000条销售数据并生成可视化报表",
        delivery_content=None,
    )
    assert result["score"] <= 60
    assert len(result["improvements"]) > 0


@pytest.mark.asyncio
async def test_ai_review_title_matching():
    """交付内容与标题高度相关的应加分。"""
    result = await ai_review_delivery(
        demand_title="Python 后端开发",
        demand_description="FastAPI + PostgreSQL",
        delivery_content="Python 后端开发 项目已完成 FastAPI 框架 PostgreSQL 数据库",
        category="编程开发",
    )
    assert result["score"] >= 70


@pytest.mark.asyncio
async def test_ai_review_returns_all_fields():
    """返回结构应包含所有必要字段。"""
    result = await ai_review_delivery(
        demand_title="测试",
        demand_description="测试内容",
        delivery_content="测试交付物内容，长度足够长以获取基础分数。补充更多文字。继续写一些内容。",
    )
    assert "score" in result and isinstance(result["score"], int)
    assert "reason" in result and isinstance(result["reason"], str)
    assert "strengths" in result and isinstance(result["strengths"], list)
    assert "improvements" in result and isinstance(result["improvements"], list)
    assert "completion_percent" in result and isinstance(result["completion_percent"], int)


@pytest.mark.asyncio
async def test_ai_arbitration_good_delivery():
    """高质量交付物应建议放款给Agent。"""
    result = await ai_arbitration_review(
        demand_title="产品LOGO设计",
        demand_description="需要设计一个简洁现代的LOGO，蓝色系，适合科技公司",
        delivery_content="LOGO设计已完成，采用蓝色渐变配色，简洁几何图形，适配各种场景。详细设计说明和源文件已提供。",
        category="设计",
    )
    assert result["match_score"] >= 60
    assert result["suggested_resolution"] in ["release_agent", "partial_refund"]
    assert 0 <= result["suggested_refund_percent"] <= 100


@pytest.mark.asyncio
async def test_ai_arbitration_poor_delivery():
    """低质量交付物应建议退款。"""
    result = await ai_arbitration_review(
        demand_title="完整网站开发",
        demand_description="需要一个包含登录、注册、商品展示、购物车的完整电商网站",
        delivery_content="已做完",
        reject_reason="未完成，只做了首页",
    )
    assert result["match_score"] < 60
    assert result["suggested_resolution"] in ["refund", "partial_refund"]
    assert result["suggested_refund_percent"] >= 50


@pytest.mark.asyncio
async def test_ai_arbitration_edge_reject():
    """带'未完成'拒绝原因的应加重退款比例。"""
    result = await ai_arbitration_review(
        demand_title="数据迁移任务",
        demand_description="将10万条用户数据从旧系统迁移到新系统",
        delivery_content="只迁移了一半数据，5万条",
        reject_reason="未完成，数据不完整",
    )
    assert result["suggested_refund_percent"] >= 70


@pytest.mark.asyncio
async def test_ai_review_score_range():
    """评分必须在0-100范围内。"""
    result = await ai_review_delivery(
        demand_title="极端测试",
        demand_description="测试边界值",
        delivery_content="短",
    )
    assert 0 <= result["score"] <= 100


@pytest.mark.asyncio
async def test_ai_arbitration_edge_high_quality():
    """极高匹配度应放款。"""
    result = await ai_arbitration_review(
        demand_title="翻译1000字英文文档",
        demand_description="需要将一份1000字的英文技术文档翻译成中文，要求专业准确",
        delivery_content="翻译已完成，1000字英文技术文档全部翻译为中文。保持了技术术语的准确性，句式流畅。已校对两遍确保无错译。这是一份高质量的翻译，术语准确，表达专业，客户可以直接使用。还附带了术语表以便参考。",
    )
    assert result["match_score"] >= 50
    assert result["suggested_refund_percent"] <= 50


@pytest.mark.asyncio
async def test_mock_review_consistency():
    """相同输入应产生相同输出。"""
    r1 = _mock_review(
        demand_title="需求标题",
        demand_description="需求描述内容",
        delivery_content="交付物内容文本，这是一致性测试。需要足够长的文本来避免随机性。继续补充内容确保分数稳定。",
        category="文案",
        tags='["文案"]',
    )
    r2 = _mock_review(
        demand_title="需求标题",
        demand_description="需求描述内容",
        delivery_content="交付物内容文本，这是一致性测试。需要足够长的文本来避免随机性。继续补充内容确保分数稳定。",
        category="文案",
        tags='["文案"]',
    )
    assert r1 == r2


@pytest.mark.asyncio
async def test_mock_arbitration_consistency():
    """仲裁分析也应保持一致。"""
    r1 = _mock_arbitration(
        demand_title="测试仲裁",
        demand_description="测试内容",
        delivery_content="交付物内容，长度足够。继续补充更多内容以确保分数合理。这里写更多细节。",
    )
    r2 = _mock_arbitration(
        demand_title="测试仲裁",
        demand_description="测试内容",
        delivery_content="交付物内容，长度足够。继续补充更多内容以确保分数合理。这里写更多细节。",
    )
    assert r1 == r2
