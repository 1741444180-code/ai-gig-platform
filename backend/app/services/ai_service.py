"""AI 服务封装 — 需求结构化提取 (demand-02/03).

当前版本：模拟模式（Mock），不真实调用AI API。
生产环境配置 APP_DASHSCOPE_API_KEY 后自动切换为真实调用。
"""

import json
import logging
from typing import Optional

from app.core.config import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)

# 模拟模式标志
MOCK_MODE = not bool(settings.QWEN_API_KEY)


# 需求分类提示词
CATEGORIES = [
    "文案", "翻译", "图片生成", "视频制作", "音频处理",
    "数据采集", "数据分析", "编程开发", "设计", "咨询",
    "教育", "营销", "客服", "其他"
]


async def ai_extract_tags(text: str) -> dict:
    """使用AI从需求描述中提取结构化标签。

    Args:
        text: 用户输入的需求描述文本。

    Returns:
        {
            "category": str,          # 分类
            "tags": [str],            # 标签列表
            "complexity": str,        # low | medium | high
            "keywords": [str],        # 关键词
            "budget_range": str,      # 预算范围建议
        }
    """
    if MOCK_MODE:
        return _mock_extract(text)
    else:
        return await _ai_extract(text)


def _mock_extract(text: str) -> dict:
    """模拟AI提取（关键词匹配）。"""
    text_lower = text.lower()
    
    # 简单规则匹配分类
    category = "其他"
    for cat in ["文案", "翻译", "图片", "视频", "编程", "数据", "设计"]:
        if cat in text_lower:
            category = cat
            break
    if category == "其他" and any(w in text_lower for w in ["写", "作", "文章", "内容"]):
        category = "文案"
    
    # 提取关键词（分词模拟）
    words = text.split()
    keywords = [w for w in words if len(w) > 1][:5]
    
    # 复杂度和预算估算
    complexity = "low"
    if len(text) > 100:
        complexity = "medium"
    if len(text) > 500:
        complexity = "high"
    
    budget_range = "50-200"
    if complexity == "medium":
        budget_range = "200-500"
    elif complexity == "high":
        budget_range = "500-2000"
    
    # 标签
    tags = [category]
    if "AI" in text or "智能" in text:
        tags.append("AI")
    if "紧急" in text:
        tags.append("加急")
    
    logger.info(f"[MOCK AI] Extracted: category={category}, tags={tags}, complexity={complexity}")
    
    return {
        "category": category,
        "tags": tags,
        "complexity": complexity,
        "keywords": keywords,
        "budget_range": budget_range,
    }


async def _ai_extract(text: str) -> dict:
    """真实调用通义千问 API (OpenAI 兼容协议)。"""
    import httpx
    
    api_key = settings.QWEN_API_KEY
    base_url = settings.DASHSCOPE_BASE_URL
    model = settings.QWEN_MODEL or "qwen-plus"
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "user", "content": build_extract_prompt(text)}
                    ],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            result = json.loads(content)
            logger.info(f"[AI Extract] category={result.get('category')}, tags={result.get('tags')}")
            return result
    except Exception as e:
        logger.error(f"[AI Extract] API call failed: {e}, falling back to mock")
        return _mock_extract(text)


def build_extract_prompt(text: str) -> str:
    """构建AI提取标签的Prompt。"""
    categories_str = "、".join(CATEGORIES)
    return f"""你是一个需求分析助手。请分析以下用户需求，提取结构化信息。

用户需求：{text}

请返回JSON格式：
{{
    "category": "从以下分类中选择最匹配的一项：{categories_str}",
    "tags": ["提取2-5个标签"],
    "complexity": "low|medium|high",
    "keywords": ["提取3-5个关键词"],
    "budget_range": "估算合理的价格范围"
}}

只返回JSON，不要其他内容。
"""
