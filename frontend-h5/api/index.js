/**
 * A00062 AIHub — HTTP API 封装层
 * 对接 FastAPI 后端，所有接口统一走这里
 */

// TODO: 切换为真实后端地址
const BASE_URL = typeof window !== 'undefined' && window.location?.origin
  ? window.location.origin
  : 'http://localhost:8000'

const API_BASE = `${BASE_URL}/api/v1`

/**
 * 统一请求封装
 */
function request({ url, method = 'GET', data, header = {}, needAuth = false }) {
  return new Promise((resolve, reject) => {
    const headers = { 'Content-Type': 'application/json', ...header }

    if (needAuth) {
      const token = uni.getStorageSync('access_token')
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }
    }

    uni.request({
      url: `${API_BASE}${url}`,
      method,
      data,
      header: headers,
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else if (res.statusCode === 401) {
          // token 失效，跳转登录
          uni.removeStorageSync('access_token')
          uni.removeStorageSync('user_info')
          uni.reLaunch({ url: '/pages/login/login' })
          reject(new Error('登录已过期'))
        } else {
          const msg = res.data?.detail || '请求失败'
          reject(new Error(msg))
        }
      },
      fail(err) {
        reject(err)
      },
    })
  })
}

/**
 * 统一请求封装（使用 Agent API Key Bearer 认证）
 * 用于 Agent 端接口，Authorization 头传 Bearer ak_xxx
 */
function requestWithApiKey({ url, method = 'GET', data, header = {}, apiKey }) {
  return new Promise((resolve, reject) => {
    const headers = { 'Content-Type': 'application/json', ...header }
    if (apiKey) {
      headers['Authorization'] = `Bearer ${apiKey}`
    }

    uni.request({
      url: `${API_BASE}${url}`,
      method,
      data,
      header: headers,
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else {
          const msg = res.data?.detail || '请求失败'
          reject(new Error(msg))
        }
      },
      fail(err) {
        reject(err)
      },
    })
  })
}

// ==================== 认证模块 ====================
// 后端 auth 路由 prefix="/auth"，注册在 v1/__init__.py
// POST /auth/send-code | POST /auth/login | POST /auth/refresh | GET /auth/me

export const auth = {
  /** 发送手机验证码 */
  sendPhoneCode(phone) {
    return request({ url: '/auth/send-code', method: 'POST', data: { phone } })
  },

  /** 手机号+验证码登录 (字段名 sms_code) */
  phoneLogin(phone, verifyCode) {
    return request({
      url: '/auth/login',
      method: 'POST',
      data: { phone, sms_code: verifyCode },
    })
  },

  /** 获取当前用户信息 */
  getMe() {
    return request({ url: '/auth/me', method: 'GET', needAuth: true })
  },

  /** Token刷新 */
  refreshToken(refreshToken) {
    return request({
      url: '/auth/refresh',
      method: 'POST',
      data: { refresh_token: refreshToken },
    })
  },
}

// ==================== 需求模块（后端路径: /demands/） ====================
// 后端 demands 路由 prefix="/demands"
// POST /demands/ | GET /demands/ | GET /demands/{id} | PUT /demands/{id} | POST /demands/{id}/cancel | POST /demands/{id}/match | GET /demands/{id}/matching

export const demands = {
  /** 创建需求 (含AI结构化) */
  create(data) {
    return request({ url: '/demands/', method: 'POST', data, needAuth: true })
  },

  /** 获取需求列表 (支持 category/status/min_budget/max_budget/keyword/page/page_size) */
  list(params = {}) {
    return request({ url: '/demands/', method: 'GET', data: params, needAuth: true })
  },

  /** 获取需求详情 */
  get(id) {
    return request({ url: `/demands/${id}`, method: 'GET', needAuth: true })
  },

  /** 编辑需求 */
  update(id, data) {
    return request({ url: `/demands/${id}`, method: 'PUT', data, needAuth: true })
  },

  /** 取消需求 */
  cancel(id) {
    return request({ url: `/demands/${id}/cancel`, method: 'POST', needAuth: true })
  },

  /** 手动触发撮合匹配 */
  triggerMatch(id) {
    return request({ url: `/demands/${id}/match`, method: 'POST', needAuth: true })
  },

  /** 查看匹配Agent列表 */
  getMatches(id) {
    return request({ url: `/demands/${id}/matching`, method: 'GET', needAuth: true })
  },
}

// ==================== 订单模块（后端路径: /orders/） ====================
// 后端 orders 路由 prefix="/orders"，使用 get_current_agent (API Key Bearer)
// 用户端也走 /orders/，使用 get_current_user (JWT Bearer)
// 用户端: GET /orders/ | GET /orders/{id}
// Agent端: POST /orders/{id}/accept | POST /orders/{id}/deliver | POST /orders/{id}/cancel | GET /agents/orders
// 验收端: POST /orders/{id}/accept-delivery | POST /orders/{id}/reject-delivery | POST /orders/{id}/redeliver | GET /orders/{id}/timeline

export const orders = {
  /** 用户端：获取我的订单列表 */
  listMy(params = {}) {
    return request({ url: '/orders/', method: 'GET', data: params, needAuth: true })
  },

  /** 用户端：获取订单详情 */
  get(id) {
    return request({ url: `/orders/${id}`, method: 'GET', needAuth: true })
  },

  /** 用户端：验收通过 */
  acceptDelivery(id) {
    return request({ url: `/orders/${id}/accept-delivery`, method: 'POST', needAuth: true })
  },

  /** 用户端：拒绝验收 */
  rejectDelivery(id, reason) {
    return request({ url: `/orders/${id}/reject-delivery`, method: 'POST', data: { reason }, needAuth: true })
  },

  /** 用户端：查看订单时间线 */
  getTimeline(id) {
    return request({ url: `/orders/${id}/timeline`, method: 'GET', needAuth: true })
  },

  // Agent端（需用 API Key 认证，不走 JWT）
  /** Agent端：接单 (需 API Key Bearer) */
  acceptByAgent(orderId, data, apiKey) {
    return requestWithApiKey({
      url: `/orders/${orderId}/accept`,
      method: 'POST',
      data,
      apiKey,
    })
  },

  /** Agent端：交付 (需 API Key Bearer) */
  deliverByAgent(orderId, data, apiKey) {
    return requestWithApiKey({
      url: `/orders/${orderId}/deliver`,
      method: 'POST',
      data,
      apiKey,
    })
  },

  /** Agent端：取消接单 (需 API Key Bearer) */
  cancelByAgent(orderId, apiKey) {
    return requestWithApiKey({
      url: `/orders/${orderId}/cancel`,
      method: 'POST',
      data: {},
      apiKey,
    })
  },

  /** Agent端：查询自己的订单列表 (需 API Key Bearer) */
  listByAgent(params = {}, apiKey) {
    return requestWithApiKey({
      url: '/agents/orders',
      method: 'GET',
      data: params,
      apiKey,
    })
  },

  /** Agent端：查询订单详情 (需 API Key Bearer) */
  getByAgent(orderId, apiKey) {
    return requestWithApiKey({
      url: `/agents/orders/${orderId}`,
      method: 'GET',
      apiKey,
    })
  },
}

// ==================== Agent模块 ====================

export const agents = {
  /** 注册Agent能力卡 (agent-04) */
  register(data) {
    return request({ url: '/agents/register', method: 'POST', data, needAuth: true })
  },

  /** 获取我的Agent列表 */
  getMyAgents() {
    return request({ url: '/agents/me', method: 'GET', needAuth: true })
  },

  /** 获取所有Agent列表 */
  list() {
    return request({ url: '/agents/', method: 'GET', needAuth: true })
  },

  /** 获取Agent详情 */
  get(agentId) {
    return request({ url: `/agents/${agentId}`, method: 'GET', needAuth: true })
  },

  /** 更新Agent能力卡 (agent-05) PUT /agents/profile */
  updateMe(data) {
    return request({ url: '/agents/profile', method: 'PUT', data, needAuth: true })
  },

  /** Agent端：获取自己的订单列表 */
  getOrders(params = {}, apiKey) {
    return requestWithApiKey({ url: '/agents/orders', method: 'GET', data: params, apiKey })
  },

  /** Agent端：获取订单详情 */
  getOrderDetail(orderId, apiKey) {
    return requestWithApiKey({ url: `/agents/orders/${orderId}`, method: 'GET', apiKey })
  },

  /** Agent端：接单 */
  acceptOrder(orderId, data, apiKey) {
    return requestWithApiKey({ url: `/agents/orders/${orderId}/accept`, method: 'POST', data, apiKey })
  },

  /** Agent端：交付 */
  deliverOrder(orderId, data, apiKey) {
    return requestWithApiKey({ url: `/agents/orders/${orderId}/deliver`, method: 'POST', data, apiKey })
  },

  /** Agent端：取消接单 */
  cancelOrder(orderId, apiKey) {
    return requestWithApiKey({ url: `/agents/orders/${orderId}/cancel`, method: 'POST', data: {}, apiKey })
  },

  /** 查看Agent API Key列表 (脱敏) */
  listKeys() {
    return request({ url: '/agents/keys', method: 'GET', needAuth: true })
  },

  /** 轮换API Key */
  rotateKey() {
    return request({ url: '/agents/keys/rotate', method: 'POST', needAuth: true })
  },

  /** 撤销API Key */
  revokeKey() {
    return request({ url: '/agents/keys/revoke', method: 'POST', needAuth: true })
  },

  /** 配置自有Agent (管理员) */
  configureOwnerAgent(agentId, data) {
    return request({ url: `/agents/${agentId}/owner-config`, method: 'PUT', data, needAuth: true })
  },
}

// ==================== 钱包模块 ====================

export const wallet = {
  /** 收益查询 */
  getIncome() {
    return request({ url: '/wallet/income', method: 'GET', needAuth: true })
  },

  /** 提现记录 */
  getWithdrawals(params = {}) {
    return request({ url: '/wallet/withdrawals', method: 'GET', data: params, needAuth: true })
  },
}

// ==================== 管理后台模块 ====================

export const admin = {
  /** 数据看板 */
  getDashboard() {
    return request({ url: '/admin/dashboard', method: 'GET', needAuth: true })
  },

  /** 用户管理列表 GET /admin/users */
  getUsers(params = {}) {
    return request({ url: '/admin/users', method: 'GET', data: params, needAuth: true })
  },

  /** 封禁用户 PUT /admin/users/{user_id}/ban */
  banUser(userId, data = {}) {
    return request({ url: `/admin/users/${userId}/ban`, method: 'PUT', data, needAuth: true })
  },

  /** 解封用户 PUT /admin/users/{user_id}/unban */
  unbanUser(userId) {
    return request({ url: `/admin/users/${userId}/unban`, method: 'PUT', needAuth: true })
  },

  /** Agent管理列表 GET /admin/agents */
  getAgents(params = {}) {
    return request({ url: '/admin/agents', method: 'GET', data: params, needAuth: true })
  },

  /** 封禁Agent PUT /admin/agents/{agent_id}/ban */
  banAgent(agentId, data = {}) {
    return request({ url: `/admin/agents/${agentId}/ban`, method: 'PUT', data, needAuth: true })
  },

  /** 解封Agent PUT /admin/agents/{agent_id}/unban */
  unbanAgent(agentId) {
    return request({ url: `/admin/agents/${agentId}/unban`, method: 'PUT', needAuth: true })
  },

  /** 订单管理列表 GET /admin/orders */
  getOrders(params = {}) {
    return request({ url: '/admin/orders', method: 'GET', data: params, needAuth: true })
  },

  /** 强制取消/完成订单 POST /admin/orders/{order_id}/force-action */
  forceOrderAction(orderId, data) {
    return request({ url: `/admin/orders/${orderId}/force-action`, method: 'POST', data, needAuth: true })
  },

  /** 仲裁列表 GET /admin/arbitration */
  getArbitration(params = {}) {
    return request({ url: '/admin/arbitration', method: 'GET', data: params, needAuth: true })
  },

  /** 裁决仲裁 POST /admin/arbitration/{order_id}/resolve */
  resolveArbitration(orderId, data) {
    return request({ url: `/admin/arbitration/${orderId}/resolve`, method: 'POST', data, needAuth: true })
  },

  /** 支付列表 GET /admin/payments */
  getPayments(params = {}) {
    return request({ url: '/admin/payments', method: 'GET', data: params, needAuth: true })
  },

  /** 确认支付 POST /admin/payments/{payment_id}/confirm */
  confirmPayment(paymentId) {
    return request({ url: `/admin/payments/${paymentId}/confirm`, method: 'POST', needAuth: true })
  },

  /** 拒绝支付 POST /admin/payments/{payment_id}/reject */
  rejectPayment(paymentId) {
    return request({ url: `/admin/payments/${paymentId}/reject`, method: 'POST', needAuth: true })
  },

  /** 提现列表 GET /admin/withdraws */
  getWithdraws(params = {}) {
    return request({ url: '/admin/withdraws', method: 'GET', data: params, needAuth: true })
  },

  /** 批准提现 POST /admin/withdraws/{withdraw_id}/approve */
  approveWithdraw(withdrawId) {
    return request({ url: `/admin/withdraws/${withdrawId}/approve`, method: 'POST', needAuth: true })
  },

  /** 拒绝提现 POST /admin/withdraws/{withdraw_id}/reject */
  rejectWithdraw(withdrawId) {
    return request({ url: `/admin/withdraws/${withdrawId}/reject`, method: 'POST', needAuth: true })
  },
}

export default { auth, demands, orders, agents, wallet, admin }