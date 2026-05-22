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

// ==================== 认证模块 ====================

export const auth = {
  /** 发送手机验证码 (MVP阶段验证码固定为 123456) */
  sendPhoneCode(phone) {
    return request({ url: '/phone/send_code', method: 'POST', data: { phone } })
  },

  /** 手机号登录 */
  phoneLogin(phone, verifyCode) {
    return request({
      url: '/phone/login',
      method: 'POST',
      data: { phone, verify_code: verifyCode },
    })
  },

  /** 获取当前用户信息 */
  getMe() {
    return request({ url: '/me', method: 'GET', needAuth: true })
  },

  /** 更新用户信息 */
  updateMe(data) {
    return request({ url: '/me', method: 'PUT', data, needAuth: true })
  },
}

// ==================== 需求模块 ====================

export const demands = {
  /** 创建需求 */
  create(data) {
    return request({ url: '/demands/', method: 'POST', data, needAuth: true })
  },

  /** 获取需求列表 */
  list(params = {}) {
    return request({ url: '/demands/', method: 'GET', data: params, needAuth: false })
  },

  /** 获取需求详情 */
  get(id) {
    return request({ url: `/demands/${id}`, method: 'GET', needAuth: false })
  },
}

// ==================== 订单模块 ====================

export const orders = {
  /** 获取我的订单列表 */
  listMy(params = {}) {
    return request({ url: '/orders/', method: 'GET', data: params, needAuth: true })
  },

  /** 获取订单详情 */
  get(id) {
    return request({ url: `/orders/${id}`, method: 'GET', needAuth: true })
  },

  /** 查询订单状态 */
  getStatus(id) {
    return request({ url: `/orders/${id}/status`, method: 'GET', needAuth: true })
  },

  /** 确认验收 */
  confirm(id) {
    return request({ url: `/orders/${id}/confirm`, method: 'POST', needAuth: true })
  },

  /** 拒绝验收 */
  reject(id, reason) {
    return request({ url: `/orders/${id}/reject`, method: 'POST', data: { reason }, needAuth: true })
  },
}

// ==================== Agent模块 ====================

export const agents = {
  /** 注册Agent能力卡 */
  register(data) {
    return request({ url: '/agents/register', method: 'POST', data, needAuth: true })
  },

  /** 获取我的Agent信息 */
  getMe() {
    return request({ url: '/agents/me', method: 'GET', needAuth: true })
  },

  /** 更新Agent能力卡 */
  updateMe(data) {
    return request({ url: '/agents/me', method: 'PUT', data, needAuth: true })
  },

  /** 切换自动接单开关 */
  toggleAutoAccept() {
    return request({ url: '/agents/me/toggle_auto_accept', method: 'POST', needAuth: true })
  },

  /** Agent接单工作台 */
  getWorkbench(params = {}) {
    return request({ url: '/agents/orders', method: 'GET', data: params, needAuth: true })
  },

  /** 外部Agent通过API Key接单 */
  acceptOrder(apiKey, data) {
    return request({
      url: '/agents/api/accept_order',
      method: 'POST',
      data: { api_key: apiKey, ...data },
    })
  },

  /** 外部Agent提交交付物 */
  submitDelivery(apiKey, data) {
    return request({
      url: '/agents/api/submit_delivery',
      method: 'POST',
      data: { api_key: apiKey, ...data },
    })
  },
}

export default { auth, demands, orders, agents }
