# CHANGELOG — A00062 AI接口接单撮合平台

> 维护人：小陈 | 最后更新：2026-05-22

---

## v0.5.0 (2026-05-22) — 全面重构 + P0修复 + 前端整合 + 集成测试通过

### 新增
- 前端 MVP：10 页面 + 3 组件 + 12 API 封装层（小林贡献，集成入项目）
- 开发计划：MVP-Minimal-v1.md（五步拆解 + 10 个任务）
- 交叉验证规范集成到工作计划
- 端到端集成测试：55 个端点全部验证通过（SA-C）

### 修复
- 🔴 删除 10 个旧重复文件（models/user.py, agent.py, demand.py, order.py, payment.py, review.py, credit_log.py, schemas/demand.py, api/v1/demands.py, users.py）
- 🔴 事务修复：await db.commit() → await db.flush()（orders/auto_confirm/webhook 共 3 个文件）
- 🔴 admin.py where 条件重构（_make_where + 增加支付统计）
- 🟡 前端 API 路径对齐：demands→requirements, me→auth/me, phone→auth/phone
- 🟡 models/__init__.py 统一从 models.models 导入

### SA-C 集成测试发现（2026-05-23）
- 55 个端点全部验证通过 ✅
- 🟡 12 个中等优先问题：部分端点缺少 response_model 声明
- 🟢 3 个低优先问题：不影响核心功能
- **结论：** 所有问题均不阻塞发布，后续版本修复

### 数据
- 代码行数：3743 → 3391（删除 352 行）
- Python 文件：43 → 33（删除 10 个重复文件）
- 全部语法检查通过

### 新增
- 前端 MVP：10 页面 + 3 组件 + 12 API 封装层（小林贡献，集成入项目）
- 开发计划：MVP-Minimal-v1.md（五步拆解 + 10 个任务）
- 交叉验证规范集成到工作计划

### 修复
- 🔴 删除 10 个旧重复文件（models/user.py, agent.py, demand.py, order.py, payment.py, review.py, credit_log.py, schemas/demand.py, api/v1/demands.py, users.py）
- 🔴 事务修复：await db.commit() → await db.flush()（orders/auto_confirm/webhook 共 3 个文件）
- 🔴 admin.py where 条件重构（_make_where + 增加支付统计）
- 🟡 前端 API 路径对齐：demands→requirements, me→auth/me, phone→auth/phone
- 🟡 models/__init__.py 统一从 models.models 导入

### 数据
- 代码行数：3743 → 3391（删除 352 行）
- Python 文件：43 → 33（删除 10 个重复文件）
- 全部语法检查通过

---

## v0.4.0 (2026-05-22) — Agent 注册 + API Key 管理

### 新增
- 3步注册流程（账号 → 能力卡 → API Key）
- API Key SHA-256 存储 + Scope 权限（full/read/sandbox/sandbox_test）
- 沙箱环境（is_sandbox 标记 + 独立权限）
- Webhook 推送服务（5次重试 + 指数退避 + 幂等性 Key）
- 验收标准文档（ACCEPTANCE-Agent注册-v0.4.0.md）

---

## v0.3.0 (2026-05-22) — 撮合引擎 + Webhook 日志

### 新增
- match_agents_hybrid(): 规则匹配(60%) + 向量匹配(40%) 综合评分
- 需求预览端点 (POST /requirements/preview)
- WebhookLog 模型 + admin 查询
- 自动撮合触发（match_mode="auto"）

---

## v0.2.0 (2026-05-22) — JWT 认证模块

### 新增
- 用户注册（手机号+密码，bcrypt）
- 密码登录 + Token 刷新（access_token 30min / refresh_token 30天）
- 14 个单元测试全部通过
- 修复 config 字段名不匹配

---

## v0.1.0 (2026-05-22) — 项目框架

### 新增
- FastAPI 后端骨架 + 7 ORM 模型 + 4 API 路由
- Docker Compose 编排（PostgreSQL 16 + FastAPI）
- 数据库 DDL + 索引 + 触发器
