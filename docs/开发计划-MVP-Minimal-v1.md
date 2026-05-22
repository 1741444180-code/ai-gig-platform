# A00062 MVP-Minimal 开发计划 v1

> **规划人：** 小陈（PM + 全栈开发）  
> **模型：** DeepSeek V4 Pro  
> **日期：** 2026-05-22  
> **当前进度：** ~50%（后端80% + 前端100%整合完成）

---

## 第一步：理解需求

**一句话目标：** 2周出可用的核心链路 — 需求发布→撮合→接单→交付→验收。

**数据流：**
```
用户注册 → 登录(JWT) → 发布需求(自由文本) 
    → AI结构化(分类/标签/预算/紧急度) 
    → 撮合引擎(规则60%+向量40%) 
    → 匹配Agent → 自动接单(API Key) 
    → 订单创建 → Agent交付 → 用户验收
```

---

## 第二步：拆成模块

### 依赖关系图

```
[P0-1 删除旧models] ──┐
[P0-2 删除旧schemas] ─┤──→ [P0-4 全局事务修复]
[P0-3 删除旧API]    ──┘        ↓
                          [P1-1 前端API路径对齐]
                               ↓
                          [P1-2 集成测试]
                               ↓
                          [P1-3 交叉验证]
                               ↓
                          [文档更新 + 汇报]
```

---

## 第三步：排优先级

### P0 — 阻塞性代码问题，必须立即修复（否则运行报错）

| # | 问题 | 影响 | 位置 |
|---|------|------|------|
| 1 | models/ 下有 7 个**重复定义**的旧模型文件（user.py/agent.py/demand.py 等），与 models.py 的类名冲突 | Import 时可能导致模块混乱 | app/models/ |
| 2 | schemas/demand.py 是旧版，与当前 schemas/requirement.py 重复 | 前后端不一致 | app/schemas/demand.py |
| 3 | api/v1/demands.py / users.py 是旧路由，与当前路由重复 | FastAPI 启动可能报路由冲突 | app/api/v1/ |
| 4 | **db commit 事务冲突**：业务代码调用 await db.commit()，但 get_db 在 finally 也执行 commit | 可能导致事务错误/重复提交 | 多个文件 |
| 5 | admin dashboard 的 order query where 条件问题 | 无 status 筛选时报 SQL 错误 | api/v1/admin.py |

### P1 — 功能完善

| # | 功能 | 状态 |
|---|------|------|
| 1 | 前端 API 路径对齐（demands→requirements, me→auth/me, phone→auth/phone） | ⬜ |
| 2 | 集成测试 | ⬜ |
| 3 | 交叉验证 | ⬜ |
| 4 | 文档更新（CHANGELOG/API/验收报告） | ⬜ |

---

## 第四步：评估风险

| 风险 | 可能性 | 影响 | Plan B |
|------|--------|------|--------|
| 旧 models 删除后其他文件有隐藏引用 | 中 | ImportError | 全局搜索引用后逐一修复 |
| db.commit() 与 get_db 冲突 | 高 (已确认) | 事务错误 | 统一改为 await db.flush() |
| 前端 API 路径修复后页面未同步 | 低 | 联调失败 | 逐页检查 import 路径 |

---

## 第五步：出计划表

### 📊 A00062 剩余开发任务（10个，约3小时）

| # | 模块 | 类型 | 模型 | 预估 | 依赖 | 状态 |
|---|------|------|------|------|------|------|
| 1 | 删除旧 models (user/agent/demand/order/payment/review/credit_log.py) | 🔴P0 | qwen3.6-plus | 10min | 无 | ⬜ |
| 2 | 删除旧 schemas (demand.py) + 旧API (demands.py, users.py) | 🔴P0 | qwen3.6-plus | 10min | 1 | ⬜ |
| 3 | 全局事务修复：await db.commit() → await db.flush() | 🔴P0 | qwen3.6-plus | 15min | 2 | ⬜ |
| 4 | admin.py where 条件 + ORM 查询修复 | 🔴P0 | qwen3.6-plus | 10min | 2 | ⬜ |
| 5 | 前端 API 路径对齐 (demands→requirements, me→auth/me) | 🟡P1 | qwen3.6-plus | 10min | 3 | ⬜ |
| 6 | 前后端语法编译验证 (42+ 文件) | 质量 | qwen3.6-plus | 5min | 3,5 | ⬜ |
| 7 | 集成测试 (认证→需求→Agent→撮合→接单→交付→验收) | 测试 | qwen3.6-plus | 15min | 6 | ⬜ |
| 8 | 自有 Agent 部署对接 (小明协助) | 部署 | - | 15min | 7 | ⬜ |
| 9 | 交叉验证 (找黄金九安排同事测试核心流程) | 质量 | - | 10min | 8 | ⬜ |
| 10 | 文档更新 (CHANGELOG + API 文档 + 验收报告) + 汇报 | 交付 | qwen3.6-plus | 10min | 9 | ⬜ |

**预计总工时：** ~2 小时（10 个任务，多数可并行派 subagent）  
**并行能力：** #1-#4 可同时派 4 个 subagent

---

## 分工安排

| 角色 | 负责 |
|------|------|
| **Subagent (qwen3.6-plus)** | #1-7 代码清理、修复、测试 |
| **小陈 (PM/架构)** | 审核 subagent 代码 + 合并 + #9 交叉验证 + #10 文档 |
| **V4 Pro** | 关键决策分析、代码审核 |
| **小明** | #8 自有 Agent 部署 |
| **黄金九** | #9 交叉验证协调 |

---

## 🧪 交叉测试规范

1. 开发完成 + 自测通过
2. 写交叉测试说明（测试步骤 + 预期结果）
3. 发给交叉测试人（黄金九协调安排）
4. 对方执行 → 记录结果
5. 通过 → 合并发布；失败 → 修 bug 再测

---

*计划完成。确认后开始执行。*
