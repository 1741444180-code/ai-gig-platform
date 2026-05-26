<template>
  <view class="login-container">
    <view class="header">
      <text class="title">AI接单撮合平台</text>
      <text class="subtitle">快速委托AI任务，省心又高效</text>
    </view>

    <view class="form">
      <view class="form-item">
        <text class="label">手机号</text>
        <input
          v-model="phone"
          type="number"
          maxlength="11"
          placeholder="请输入11位手机号"
          class="input"
        />
      </view>

      <view class="form-item">
        <text class="label">验证码</text>
        <view class="code-row">
          <input
            v-model="code"
            type="number"
            maxlength="6"
            placeholder="请输入6位验证码"
            class="input code-input"
          />
          <button
            class="code-btn"
            :disabled="countdown > 0"
            @click="sendCode"
          >
            {{ countdown > 0 ? `${countdown}s` : '发送验证码' }}
          </button>
        </view>
      </view>

      <button class="login-btn" :disabled="!canLogin" @click="doLogin">
        登录
      </button>
    </view>
  </view>
</template>

<script>
import { auth } from '@/api/index.js'

export default {
  data() {
    return {
      phone: '',
      code: '',
      countdown: 0,
      timer: null,
    }
  },
  computed: {
    canLogin() {
      return this.phone.length === 11 && this.code.length === 6
    },
  },
  methods: {
    async sendCode() {
      if (this.phone.length !== 11) {
        uni.showToast({ title: '请输入11位手机号', icon: 'none' })
        return
      }
      try {
        uni.showLoading({ title: '发送中...' })
        await auth.sendPhoneCode(this.phone)
        uni.hideLoading()
        uni.showToast({ title: '验证码已发送', icon: 'success' })
        this.countdown = 60
        this.timer = setInterval(() => {
          this.countdown--
          if (this.countdown <= 0) {
            clearInterval(this.timer)
          }
        }, 1000)
      } catch (e) {
        uni.hideLoading()
        uni.showToast({ title: e.message || '发送失败', icon: 'none' })
      }
    },

    async doLogin() {
      if (!this.canLogin) return
      try {
        uni.showLoading({ title: '登录中...' })
        const res = await auth.phoneLogin(this.phone, this.code)
        uni.hideLoading()
        // 存储 token 和用户信息
        uni.setStorageSync('access_token', res.access_token)
        if (res.refresh_token) {
          uni.setStorageSync('refresh_token', res.refresh_token)
        }
        if (res.user_info) {
          uni.setStorageSync('user_info', res.user_info)
        }
        uni.showToast({ title: '登录成功', icon: 'success' })
        // 跳转首页
        setTimeout(() => {
          uni.reLaunch({ url: '/pages/index/index' })
        }, 1500)
      } catch (e) {
        uni.hideLoading()
        uni.showToast({ title: e.message || '登录失败', icon: 'none' })
      }
    },
  },
  beforeDestroy() {
    if (this.timer) clearInterval(this.timer)
  },
}
</script>

<style scoped>
.login-container {
  padding: 60rpx 40rpx;
}
.header {
  margin-bottom: 80rpx;
  text-align: center;
}
.title {
  display: block;
  font-size: 48rpx;
  font-weight: bold;
  color: #333;
  margin-bottom: 16rpx;
}
.subtitle {
  display: block;
  font-size: 28rpx;
  color: #999;
}
.form {
  background: #fff;
  border-radius: 16rpx;
  padding: 40rpx;
}
.form-item {
  margin-bottom: 40rpx;
}
.label {
  display: block;
  font-size: 28rpx;
  color: #333;
  margin-bottom: 16rpx;
  font-weight: 500;
}
.input {
  height: 88rpx;
  background: #f8f8f8;
  border-radius: 8rpx;
  padding: 0 24rpx;
  font-size: 30rpx;
}
.code-row {
  display: flex;
  align-items: center;
  gap: 20rpx;
}
.code-input {
  flex: 1;
}
.code-btn {
  width: 220rpx;
  height: 88rpx;
  line-height: 88rpx;
  background: #007aff;
  color: #fff;
  font-size: 26rpx;
  border-radius: 8rpx;
  padding: 0;
  border: none;
}
.code-btn[disabled] {
  background: #ccc;
}
.login-btn {
  width: 100%;
  height: 96rpx;
  line-height: 96rpx;
  background: #007aff;
  color: #fff;
  font-size: 34rpx;
  font-weight: bold;
  border-radius: 48rpx;
  border: none;
  margin-top: 20rpx;
}
.login-btn[disabled] {
  background: #ccc;
}
</style>