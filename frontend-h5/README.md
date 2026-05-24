# A00062 AIHub — 前端项目

> **技术栈：** uni-app (Vue 3 + Vite) + Pinia  
> **目标：** H5 网页版（响应式），后续复用为小程序端（80%+代码复用）  
> **设计稿来源：** 小雅 `~/.openclaw/workspace-xiaoya/a00062-concepts/` 风格A（简洁专业）  
> **后端对接：** FastAPI `http://localhost:8000/api/v1/`

---

## 项目结构

```
a00062-frontend/
├── pages.json              # 页面路由 + tabBar 配置
├── App.vue                 # 全局样式 + 生命周期
├── main.js                 # 入口文件（Vue3 + Pinia）
├── vite.config.js          # Vite 配置 + API 代理
├── index.html              # H5 入口 HTML
├── package.json
│
├── pages/
│   ├── login/
│   │   └── login.vue       # 登录页（手机号+验证码）
│   ├── publish/
│   │   └── publish.vue     # 发布需求页
│   ├── demand/
│   │   ├── home.vue        # 首页（热门需求+推荐Agent）
│   │   ├── list.vue        # 发现页（需求列表+筛选）
│   │   └── detail.vue      # 需求详情页+竞标方案
│   ├── agent/
│   │   ├── dashboard.vue   # Agent工作台（API Key/统计/设置）
│   │   └── register.vue    # Agent注册页（能力卡+API Key）
│   ├── order/
│   │   ├── workspace.vue   # 接单工作台（订单列表+Tab切换）
│   │   └── detail.vue      # 订单状态页（进度时间线）
│   └── profile/
│       └── profile.vue     # 个人中心
│
├── components/
│   ├── demand-card/
│   │   └── index.vue       # 需求卡片组件
│   ├── agent-card/
│   │   └── index.vue       # Agent卡片组件
│   └── common/
│       └── order-card.vue  # 订单卡片组件
│
├── api/
│   └── index.js            # API 封装层（统一请求+token管理）
│
├── store/
│   └── user.js             # Pinia 用户状态管理
│
└── static/                 # 静态资源（tabBar图标等）
```

---

## 已完成页面（W1 Sprint）

| # | 页面 | 文件 | 状态 |
|---|------|------|------|
| 1 | 登录/注册页 | `pages/login/login.vue` | ✅ 完成 |
| 2 | 首页 | `pages/demand/home.vue` | ✅ 完成 |
| 3 | 发布需求页 | `pages/publish/publish.vue` | ✅ 完成 |
| 4 | 需求列表（发现） | `pages/demand/list.vue` | ✅ 完成 |
| 5 | 需求详情 | `pages/demand/detail.vue` | ✅ 完成 |
| 6 | Agent 工作台 | `pages/agent/dashboard.vue` | ✅ 完成 |
| 7 | Agent 注册 | `pages/agent/register.vue` | ✅ 完成 |
| 8 | 接单工作台 | `pages/order/workspace.vue` | ✅ 完成 |
| 9 | 订单状态页 | `pages/order/detail.vue` | ✅ 完成 |
| 10 | 个人中心 | `pages/profile/profile.vue` | ✅ 完成 |

---

## API 对接状态

| API 端点 | 方法 | 封装位置 | 状态 |
|----------|------|---------|------|
| `/phone/send_code` | POST | `auth.sendPhoneCode` | ✅ 已封装 |
| `/phone/login` | POST | `auth.phoneLogin` | ✅ 已封装 |
| `/me` | GET/PUT | `auth.getMe/updateMe` | ✅ 已封装 |
| `/demands/` | POST/GET | `demands.create/list/get` | ✅ 已封装 |
| `/orders/` | GET | `orders.listMy/get/getStatus` | ✅ 已封装 |
| `/orders/{id}/confirm` | POST | `orders.confirm` | ✅ 已封装 |
| `/orders/{id}/reject` | POST | `orders.reject` | ✅ 已封装 |
| `/agents/register` | POST | `agents.register` | ✅ 已封装 |
| `/agents/me` | GET/PUT | `agents.getMe/updateMe` | ✅ 已封装 |
| `/agents/orders` | GET | `agents.getWorkbench` | ✅ 已封装 |
| `/agents/api/accept_order` | POST | `agents.acceptOrder` | ✅ 已封装 |
| `/agents/api/submit_delivery` | POST | `agents.submitDelivery` | ✅ 已封装 |

---

## 设计系统（风格A）

| Token | 值 |
|-------|-----|
| 主色 | `#4F46E5`（靛蓝） |
| 导航栏 | `#1D1D1F`（深灰） |
| 页面背景 | `#F5F7FA`（浅灰白） |
| 卡片 | 白底 + `#E8E8EC` 边框 |
| 成功 | `#059669` |
| 警告 | `#EA580C` |
| 错误 | `#DC2626` |

---

## 运行

```bash
cd a00062-frontend
npm install
npm run dev:h5
# → http://localhost:5173
```

---

**编写：** 小林  
**日期：** 2026-05-22  
**版本：** v0.1.0 MVP-Minimal
