# CHANGELOG - A00062 AI接口接单撮合平台

所有重要变更按时间倒序记录在此。

格式：`[日期] [模块] 变更说明`

---

## [2026-05-25] [模块G] 异常流程 + 管理后台

**新增端点：**
- `POST /admin/tasks/run-scheduled` — 手动触发定时任务
- `GET /admin/dashboard` — 数据看板
- `GET /admin/arbitration` — 仲裁列表
- `POST /admin/arbitration/{id}/initiate` — 发起仲裁
- `POST /admin/arbitration/{id}/resolve` — 裁决仲裁
- `POST /admin/orders/{id}/force-action` — 强制取消/完成
- `GET /admin/orders` — 订单管理
- `PUT /admin/agents/{id}/ban` — 封禁Agent
- `GET /admin/agents` — Agent管理
- `PUT /admin/users/{id}/unban` — 解封用户
- `PUT /admin/users/{id}/ban` — 封禁用户
- `GET /admin/users` — 用户管理

**新增服务：**
- `error_handler_service.py` — 异常处理（超时取消/仲裁/放弃/健康监控）

**变更：** 4ce8d29

---

## [2026-05-25] [模块F] 验收流程

**新增端点：**
- `POST /orders/{id}/accept-delivery` — 验收通过
- `POST /orders/{id}/reject-delivery` — 拒绝验收
- `POST /orders/{id}/redeliver` — Agent重新交付
- `GET /orders/{id}/timeline` — 订单时间线

**变更：** 0f1535c

---

## [2026-05-25] [模块E] Agent接单API

**新增端点：**
- `POST /orders/accept` — Agent接单
- `POST /orders/deliver` — Agent交付
- `POST /orders/cancel` — Agent取消
- `GET /orders/my` — Agent订单列表
- `GET /orders/my/{id}` — Agent订单详情
- `GET /orders` — 用户端订单列表
- `GET /orders/{id}` — 用户端订单详情

**变更：** ff7d9a9

---

## [2026-05-25] [模块D] 需求撮合规则匹配

**新增端点：**
- `GET /demands/{id}/matching` — 匹配查询
- `POST /demands/{id}/matching` — 手动触发

**新增服务：**
- `match_service.py` — 规则匹配引擎
- `webhook_service.py` — Webhook推送
- `demand_push_service.py` — 自动撮合触发

**变更：** 61112f5

---

## [2026-05-25] [模块C] 需求发布 + AI结构化

**新增端点：**
- `POST /demands` — 发布需求 + AI标签提取
- `GET /demands` — 需求列表
- `GET /demands/{id}` — 需求详情
- `PUT /demands/{id}` — 编辑需求
- `POST /demands/{id}/cancel` — 取消需求

**变更：** e01074a

---

## [2026-05-24] [模块A+B] JWT认证 + Agent注册 + API Key管理

**新增端点：**
- `POST /auth/send-code` — 发送验证码
- `POST /auth/login` — 登录
- `POST /auth/refresh` — 刷新Token
- `GET /users/me` — 用户信息
- `POST /agents/register` — Agent注册
- `GET /agents/me` — Agent能力卡
- `PUT /agents/me` — 更新能力卡
- `POST /agents/me/api-keys` — 创建Key
- `GET /agents/me/api-keys` — Key列表
- `DELETE /agents/me/api-keys/{id}` — 删除Key

**变更：** 4d45900

---

## [2026-05-22] [初始化] 项目框架

- FastAPI 框架搭建
- SQLAlchemy + Alembic
- PostgreSQL 配置
- Docker Compose 编排
- 前端 MVP 整合

**变更：** 7468daa

---

## 版本汇总

| 版本 | 日期 | 模块 | 子任务 | 状态 |
|------|------|------|--------|------|
| v0.7.0 | 2026-05-25 | G 异常流程+管理后台 | 16 | ✅ |
| v0.6.0 | 2026-05-25 | F 验收流程 | 4 | ✅ |
| v0.5.0 | 2026-05-25 | E 接单API | 6 | ✅ |
| v0.4.0 | 2026-05-25 | D 需求撮合 | 5 | ✅ |
| v0.3.0 | 2026-05-25 | C 需求发布 | 8 | ✅ |
| v0.2.0 | 2026-05-24 | A+B 认证+Agent | 14 | ✅ |
| v0.1.0 | 2026-05-22 | 初始化 | 5 | ✅ |

**累计：** 58/102 (57%)
