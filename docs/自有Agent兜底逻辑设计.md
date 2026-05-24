# A00062 — 自有 Agent 兜底逻辑设计

## 背景

建权决策：初期 Agent 干不了平台顶上（兜底）。  
自有 Agent 在无外部 Agent 接单时，超时自动接管需求。

## 兜底流程

```
需求发布(match_mode=auto)
    ↓
撮合引擎匹配
    ↓
├── 有匹配的活跃 Agent → 正常推送
│   └── Agent 30分钟内接单 → 正常流程
│   └── Agent 30分钟内未接单 → 触发兜底
│
├── 无匹配的活跃 Agent → 触发兜底
│
└── 兜底逻辑:
    ├── 查找平台自有 Agent（tags 包含 "平台自有"）
    ├── 按能力匹配选择最合适的自有 Agent
    ├── 自动创建订单（金额 = min(需求预算, Agent基础报价)）
    ├── 通知用户："平台免费为您提供服务"
    └── 自有 Agent 自动处理 → 交付
```

## 自有 Agent 列表

| Agent | 能力标签 | 端口 | API Key 前缀 |
|-------|---------|------|-------------|
| 文案Agent | 文案写作、翻译、产品描述、小红书 | 9101 | ak_writer_ |
| 图片Agent | 图像设计、Logo、海报、AI生图 | 9102 | ak_design_ |

## 触发条件

1. 需求发布后 5 分钟内无 Agent 接单
2. 或需求 status 保持 "open" 超过 30 分钟
3. 平台定时任务（Celery/APScheduler）定期扫描

## 技术实现（待开发）

```python
# services/platform_fallback.py
async def check_and_fallback(db: AsyncSession):
    """扫描超时未接单的需求，触发平台自有Agent兜底"""
    
    # 1. 查询超时需求
    timeout_requirements = await get_timeout_requirements(db, timeout_minutes=30)
    
    # 2. 对每个超时需求，查找最匹配的自有Agent
    for req in timeout_requirements:
        best_agent = await find_best_platform_agent(db, req)
        if best_agent:
            # 3. 自动创建订单（免费/大额优惠券）
            order = await create_fallback_order(db, req, best_agent)
            await notify_user(order)
```
