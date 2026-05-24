<template>
  <view class="page-container">
    <!-- Profile Header -->
    <view class="profile-header">
      <view class="settings-btn" @click="goSettings">
        <text class="settings-icon">⚙</text>
      </view>
      <view class="profile-avatar"><text>{{ userInfo.nickname?.charAt(0) || 'U' }}</text></view>
      <text class="profile-name">{{ userInfo.nickname || '用户' }}</text>
      <text class="profile-title">{{ userInfo.phone ? `${userInfo.phone.slice(0,3)}****${userInfo.phone.slice(-4)}` : '未绑定手机' }}</text>
      <view class="profile-badges">
        <view class="badge"><text>信用分 {{ userInfo.credit_score || 100 }}</text></view>
      </view>
    </view>

    <!-- Stats -->
    <view class="stats-row">
      <view class="stat-item">
        <text class="stat-num">{{ stats.demands }}</text>
        <text class="stat-label">发布需求</text>
      </view>
      <view class="stat-item">
        <text class="stat-num">{{ stats.orders }}</text>
        <text class="stat-label">进行中订单</text>
      </view>
      <view class="stat-item">
        <text class="stat-num">{{ stats.completed }}</text>
        <text class="stat-label">已完成</text>
      </view>
    </view>

    <!-- Menu: Orders -->
    <view class="menu-section">
      <text class="menu-section-title">订单管理</text>
      <view class="menu-item" @click="goTo('/pages/order/workspace')">
        <view class="menu-icon-wrap" style="background:#4F46E5;"><text class="menu-icon-text">📋</text></view>
        <text class="menu-text">我发布的订单</text>
        <text class="menu-badge" v-if="stats.orders > 0">{{ stats.orders }}</text>
        <text class="menu-arrow">›</text>
      </view>
      <view class="menu-item" @click="goTo('/pages/order/workspace')">
        <view class="menu-icon-wrap" style="background:#059669;"><text class="menu-icon-text">✅</text></view>
        <text class="menu-text">已完成的订单</text>
        <text class="menu-arrow">›</text>
      </view>
    </view>

    <!-- Menu: Agent -->
    <view class="menu-section">
      <text class="menu-section-title">Agent 管理</text>
      <view class="menu-item" @click="goTo('/pages/agent/dashboard')">
        <view class="menu-icon-wrap" style="background:#7C3AED;"><text class="menu-icon-text">🤖</text></view>
        <text class="menu-text">Agent 工作台</text>
        <text class="menu-arrow">›</text>
      </view>
      <view class="menu-item" @click="goTo('/pages/agent/register')">
        <view class="menu-icon-wrap" style="background:#EC4899;"><text class="menu-icon-text">➕</text></view>
        <text class="menu-text">注册 Agent</text>
        <text class="menu-arrow">›</text>
      </view>
    </view>

    <!-- Menu: Settings -->
    <view class="menu-section">
      <text class="menu-section-title">设置</text>
      <view class="menu-item" @click="goTo('/pages/profile/profile')">
        <view class="menu-icon-wrap" style="background:#64748B;"><text class="menu-icon-text">👤</text></view>
        <text class="menu-text">编辑资料</text>
        <text class="menu-arrow">›</text>
      </view>
      <view class="menu-item" @click="handleLogout">
        <view class="menu-icon-wrap" style="background:#EF4444;"><text class="menu-icon-text">🚪</text></view>
        <text class="menu-text">退出登录</text>
        <text class="menu-arrow">›</text>
      </view>
    </view>

    <view style="height: 24px;"></view>
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useUserStore } from '../../store/user.js'

const userStore = useUserStore()
const userInfo = ref({ nickname: '', phone: '', credit_score: 100 })
const stats = ref({ demands: 5, orders: 3, completed: 12 })

function goTo(url) { uni.navigateTo({ url }) }
function goSettings() { uni.showToast({ title: '开发中', icon: 'none' }) }
function handleLogout() {
  uni.showModal({
    title: '退出登录',
    content: '确定要退出吗？',
    success: (res) => {
      if (res.confirm) {
        userStore.logout()
        uni.reLaunch({ url: '/pages/login/login' })
      }
    },
  })
}

onMounted(() => {
  if (userStore.isLoggedIn) {
    userInfo.value = userStore.userInfo || {}
    userStore.refreshUser()
  } else {
    // 未登录跳转登录页
    uni.reLaunch({ url: '/pages/login/login' })
  }
})
</script>

<style scoped>
.profile-header {
  background: linear-gradient(135deg, #4F46E5, #6366F1);
  color: #fff; padding: 40px 16px 24px; position: relative; text-align: center;
}
.settings-btn { position: absolute; top: 14px; right: 16px; }
.settings-icon { font-size: 22px; }
.profile-avatar {
  width: 64px; height: 64px; border-radius: 16px;
  background: rgba(255,255,255,0.2);
  display: flex; align-items: center; justify-content: center;
  font-size: 24px; font-weight: 700; margin: 0 auto 12px;
  border: 2px solid rgba(255,255,255,0.3);
}
.profile-name { font-size: 20px; font-weight: 700; color: #fff; display: block; margin-bottom: 4px; }
.profile-title { font-size: 13px; color: rgba(255,255,255,0.8); display: block; }
.profile-badges { display: flex; flex-direction: row; gap: 6px; justify-content: center; margin-top: 12px; }
.badge { padding: 3px 10px; border-radius: 4px; background: rgba(255,255,255,0.2); font-size: 11px; font-weight: 500; color: #fff; }

.stats-row { display: flex; flex-direction: row; background: #fff; border-bottom: 1px solid #E5E7EB; }
.stat-item { flex: 1; text-align: center; padding: 16px 8px; border-right: 1px solid #F0F0F0; }
.stat-item:last-child { border-right: none; }
.stat-num { font-size: 20px; font-weight: 800; color: #4F46E5; display: block; letter-spacing: -0.5px; }
.stat-label { font-size: 11px; color: #A1A1AA; margin-top: 2px; display: block; }

.menu-section { background: #fff; margin-top: 10px; border-top: 1px solid #E5E7EB; }
.menu-section + .menu-section { margin-top: 0; border-top: none; }
.menu-section-title { font-size: 12px; font-weight: 600; color: #A1A1AA; padding: 12px 16px 4px; }
.menu-item {
  display: flex; flex-direction: row; align-items: center;
  padding: 14px 16px; border-bottom: 1px solid #F5F5F5;
}
.menu-item:last-child { border-bottom: none; }
.menu-icon-wrap {
  width: 32px; height: 32px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  margin-right: 12px;
}
.menu-icon-text { font-size: 16px; }
.menu-text { flex: 1; font-size: 14px; font-weight: 500; color: #1D1D1F; }
.menu-badge { background: #DC2626; color: #fff; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 8px; margin-right: 8px; }
.menu-arrow { color: #D4D4D8; font-size: 14px; }
</style>
