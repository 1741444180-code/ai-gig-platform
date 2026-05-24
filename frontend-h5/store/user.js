/**
 * A00062 — Pinia Store (全局状态管理)
 */
import { defineStore } from 'pinia'
import { auth } from '../api/index.js'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: uni.getStorageSync('access_token') || '',
    userInfo: uni.getStorageSync('user_info') || null,
    isLoggedIn: !!uni.getStorageSync('access_token'),
  }),

  getters: {
    nickname: (state) => state.userInfo?.nickname || '用户',
    phone: (state) => state.userInfo?.phone || '',
    avatar: (state) => state.userInfo?.avatar || '',
    creditScore: (state) => state.userInfo?.credit_score || 100,
    balance: (state) => state.userInfo?.balance || 0,
  },

  actions: {
    async loginWithPhone(phone, code) {
      const res = await auth.phoneLogin(phone, code)
      this.token = res.access_token
      this.userInfo = res.user_info
      this.isLoggedIn = true
      uni.setStorageSync('access_token', res.access_token)
      uni.setStorageSync('user_info', res.user_info)
      return res
    },

    async refreshUser() {
      try {
        const res = await auth.getMe()
        this.userInfo = res
        uni.setStorageSync('user_info', res)
      } catch (e) {
        console.error('刷新用户信息失败', e)
      }
    },

    logout() {
      this.token = ''
      this.userInfo = null
      this.isLoggedIn = false
      uni.removeStorageSync('access_token')
      uni.removeStorageSync('user_info')
    },
  },
})
