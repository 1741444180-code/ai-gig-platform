<template>
  <view class="page-container">
    <!-- Top Nav -->
    <view class="top-nav">
      <view class="back-btn" @click="goBack">
        <text class="back-icon">‹</text>
      </view>
      <text class="nav-title">登录</text>
    </view>

    <!-- Logo Area -->
    <view class="logo-area">
      <view class="logo-circle">
        <text class="logo-text">AI</text>
      </view>
      <text class="app-name">AI<text class="app-name-hl">Hub</text></text>
      <text class="app-desc">AI接口接单撮合平台</text>
    </view>

    <!-- Login Form -->
    <view class="form-card">
      <text class="form-title">手机号登录</text>

      <view class="input-group">
        <text class="input-label">手机号</text>
        <input
          class="input-field"
          type="number"
          maxlength="11"
          placeholder="请输入手机号"
          v-model="phone"
        />
      </view>

      <view class="input-group">
        <text class="input-label">验证码</text>
        <view class="code-row">
          <input
            class="input-field code-input"
            type="number"
            maxlength="6"
            placeholder="请输入验证码"
            v-model="code"
          />
          <button
            class="btn-send-code"
            :class="{ disabled: codeSent && countdown > 0 }"
            @click="sendCode"
            :disabled="codeSent && countdown > 0"
          >
            {{ countdown > 0 ? `${countdown}s` : '发送验证码' }}
          </button>
        </view>
      </view>

      <text class="tip">💡 MVP阶段验证码固定为 <text class="tip-code">123456</text></text>

      <button class="btn-login" @click="handleLogin" :loading="loading">登录</button>

      <text class="agreement">
        登录即同意
        <text class="agreement-link">《用户协议》</text>
        和
        <text class="agreement-link">《隐私政策》</text>
      </text>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { useUserStore } from '../../store/user.js'
import { auth } from '../../api/index.js'

const phone = ref('')
const code = ref('')
const codeSent = ref(false)
const countdown = ref(0)
const loading = ref(false)

let timer = null

function goBack() {
  uni.navigateBack()
}

function sendCode() {
  if (!phone.value || phone.value.length !== 11) {
    uni.showToast({ title: '请输入正确的手机号', icon: 'none' })
    return
  }
  if (countdown.value > 0) return

  auth.sendPhoneCode(phone.value)
    .then(() => {
      codeSent.value = true
      countdown.value = 60
      timer = setInterval(() => {
        countdown.value--
        if (countdown.value <= 0) {
          clearInterval(timer)
        }
      }, 1000)
      uni.showToast({ title: '验证码已发送', icon: 'success' })
    })
    .catch(() => {
      uni.showToast({ title: '发送失败', icon: 'none' })
    })
}

async function handleLogin() {
  if (!phone.value || phone.value.length !== 11) {
    uni.showToast({ title: '请输入正确的手机号', icon: 'none' })
    return
  }
  if (!code.value || code.value.length < 4) {
    uni.showToast({ title: '请输入验证码', icon: 'none' })
    return
  }

  loading.value = true
  try {
    const userStore = useUserStore()
    await userStore.loginWithPhone(phone.value, code.value)
    uni.showToast({ title: '登录成功', icon: 'success' })
    setTimeout(() => {
      uni.switchTab({ url: '/pages/demand/home' })
    }, 500)
  } catch (e) {
    uni.showToast({ title: e.message || '登录失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.top-nav {
  background: #fff;
  padding: 12px 16px;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid #E5E7EB;
  position: sticky;
  top: 0;
  z-index: 100;
}
.back-btn {
  width: 32px; height: 32px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 8px;
}
.back-icon { font-size: 24px; color: #1D1D1F; line-height: 1; }
.nav-title { font-size: 17px; font-weight: 600; }

.logo-area {
  text-align: center;
  padding: 48px 16px 32px;
}
.logo-circle {
  width: 72px; height: 72px;
  border-radius: 50%;
  background: linear-gradient(135deg, #4F46E5, #6366F1);
  display: flex; align-items: center; justify-content: center;
  margin: 0 auto 16px;
}
.logo-text { font-size: 24px; font-weight: 800; color: #fff; }
.app-name { font-size: 24px; font-weight: 800; color: #1D1D1F; display: block; }
.app-name-hl { color: #4F46E5; }
.app-desc { font-size: 13px; color: #A1A1AA; display: block; margin-top: 4px; }

.form-card {
  background: #fff;
  margin: 0 16px;
  border-radius: 12px;
  padding: 24px 20px;
}
.form-title { font-size: 18px; font-weight: 700; color: #1D1D1F; display: block; margin-bottom: 20px; }
.input-group { margin-bottom: 16px; }
.input-label { font-size: 14px; font-weight: 600; color: #1D1D1F; display: block; margin-bottom: 8px; }
.input-field {
  width: 100%;
  border: 1px solid #D4D4D8;
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 14px;
  background: #FAFAFA;
}
.code-row { display: flex; flex-direction: row; gap: 10px; }
.code-input { flex: 1; }
.btn-send-code {
  flex: 0 0 100px;
  background: #4F46E5;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 10px 0;
  font-size: 13px;
  font-weight: 500;
}
.btn-send-code.disabled {
  background: #C7D2FE;
}
.tip {
  font-size: 12px;
  color: #A1A1AA;
  display: block;
  margin-bottom: 20px;
}
.tip-code {
  color: #4F46E5;
  font-weight: 600;
  font-family: 'SF Mono', monospace;
}
.btn-login {
  width: 100%;
  background: #4F46E5;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 12px;
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 16px;
}
.agreement {
  font-size: 12px;
  color: #A1A1AA;
  text-align: center;
  display: block;
}
.agreement-link { color: #4F46E5; }
</style>
