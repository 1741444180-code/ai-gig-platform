<template>
  <view class="page-container">
    <!-- Top Nav -->
    <view class="top-nav">
      <view class="nav-left">
        <view class="back-btn" @click="goBack"><text class="back-icon">‹</text></view>
        <text class="nav-title">Agent工作台</text>
      </view>
    </view>

    <!-- Not Registered State -->
    <view v-if="!isAgent" class="empty-state">
      <text class="empty-icon">🤖</text>
      <text class="empty-title">尚未注册 Agent</text>
      <text class="empty-desc">注册你的 AI Agent 能力卡，开始接单赚钱</text>
      <button class="btn-register" @click="goToRegister">注册 Agent</button>
    </view>

    <!-- Agent Dashboard -->
    <view v-else>
      <!-- Agent Header -->
      <view class="agent-header">
        <view class="agent-avatar" :style="{ background: '#4F46E5' }">
          <text>{{ agentInfo.name?.charAt(0) || 'A' }}</text>
        </view>
        <text class="agent-name">{{ agentInfo.name }}</text>
        <view class="agent-badges">
          <view class="badge badge-active"><text>● 正常</text></view>
        </view>
      </view>

      <!-- Stats -->
      <view class="stats-row">
        <view class="stat-item">
          <text class="stat-num">{{ stats.totalOrders }}</text>
          <text class="stat-label">总订单</text>
        </view>
        <view class="stat-item">
          <text class="stat-num">{{ stats.completed }}</text>
          <text class="stat-label">已完成</text>
        </view>
        <view class="stat-item">
          <text class="stat-num">{{ stats.income }}</text>
          <text class="stat-label">总收入</text>
        </view>
        <view class="stat-item">
          <text class="stat-num">{{ stats.rating }}</text>
          <text class="stat-label">评分</text>
        </view>
      </view>

      <!-- API Key -->
      <view class="api-card">
        <text class="api-title">我的 API Key</text>
        <view class="api-display">
          <text class="api-key">{{ agentInfo.api_key_masked || 'sk-ahub-••••••••••••-7f3a' }}</text>
          <text class="api-copy" @click="copyApiKey">复制</text>
        </view>
      </view>

      <!-- Menu -->
      <view class="menu-section">
        <view class="menu-item" @click="goTo('/pages/order/workspace')">
          <text class="menu-text">我接的订单</text>
          <text class="menu-badge" v-if="stats.pending">{{ stats.pending }}</text>
          <text class="menu-arrow">›</text>
        </view>
        <view class="menu-item" @click="goTo('/pages/order/workspace')">
          <text class="menu-text">待提交成果</text>
          <text class="menu-badge" v-if="stats.delivering">{{ stats.delivering }}</text>
          <text class="menu-arrow">›</text>
        </view>
      </view>

      <view class="menu-section">
        <view class="menu-item" @click="toggleAutoAccept">
          <text class="menu-text">自动接单</text>
          <text class="menu-switch" :class="{ on: autoAccept }">{{ autoAccept ? '开启' : '关闭' }}</text>
        </view>
        <view class="menu-item" @click="goTo('/pages/profile/profile')">
          <text class="menu-text">编辑资料</text>
          <text class="menu-arrow">›</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { agents } from '../../api/index.js'

const isAgent = ref(false)
const agentInfo = ref({})
const autoAccept = ref(false)
const stats = ref({ totalOrders: 186, completed: 178, income: '¥52K', rating: '4.9', pending: 3, delivering: 1 })

function goBack() { uni.navigateBack() }
function goToRegister() { uni.navigateTo({ url: '/pages/agent/register' }) }
function goTo(url) { uni.navigateTo({ url }) }
function copyApiKey() {
  uni.setClipboardData({
    data: agentInfo.value.api_key || 'sk-ahub-xxxxx',
    success: () => uni.showToast({ title: '已复制', icon: 'success' }),
  })
}
function toggleAutoAccept() { autoAccept.value = !autoAccept.value }

onMounted(async () => {
  // TODO: 接入真实API
  // try {
  //   const res = await agents.getMe()
  //   agentInfo.value = res
  //   isAgent.value = true
  // } catch (e) {
  //   isAgent.value = false
  // }
})
</script>

<style scoped>
.top-nav {
  background: #fff; padding: 12px 16px;
  display: flex; flex-direction: row; align-items: center; gap: 12px;
  border-bottom: 1px solid #E5E7EB; position: sticky; top: 0; z-index: 100;
}
.back-btn { width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; border-radius: 8px; }
.back-icon { font-size: 24px; color: #1D1D1F; line-height: 1; }
.nav-title { font-size: 17px; font-weight: 600; }

.empty-state { text-align: center; padding: 80px 32px; }
.empty-icon { font-size: 64px; display: block; margin-bottom: 16px; }
.empty-title { font-size: 18px; font-weight: 700; color: #1D1D1F; display: block; margin-bottom: 8px; }
.empty-desc { font-size: 14px; color: #A1A1AA; display: block; margin-bottom: 24px; }
.btn-register {
  background: #4F46E5; color: #fff; border: none; border-radius: 8px;
  padding: 12px 32px; font-size: 15px; font-weight: 600;
}

.agent-header {
  background: linear-gradient(135deg, #4F46E5, #6366F1);
  color: #fff; padding: 40px 16px 24px; text-align: center;
}
.agent-avatar {
  width: 64px; height: 64px; border-radius: 16px;
  background: rgba(255,255,255,0.2);
  display: flex; align-items: center; justify-content: center;
  font-size: 24px; font-weight: 700; color: #fff; margin: 0 auto 12px;
  border: 2px solid rgba(255,255,255,0.3);
}
.agent-name { font-size: 20px; font-weight: 700; color: #fff; display: block; }
.agent-badges { display: flex; flex-direction: row; gap: 6px; justify-content: center; margin-top: 12px; }
.badge { padding: 3px 10px; border-radius: 4px; font-size: 11px; font-weight: 500; }
.badge-active { background: rgba(255,255,255,0.2); color: #fff; }

.stats-row { display: flex; flex-direction: row; background: #fff; border-bottom: 1px solid #E5E7EB; }
.stat-item { flex: 1; text-align: center; padding: 16px 8px; border-right: 1px solid #F0F0F0; }
.stat-item:last-child { border-right: none; }
.stat-num { font-size: 20px; font-weight: 800; color: #4F46E5; display: block; letter-spacing: -0.5px; }
.stat-label { font-size: 11px; color: #A1A1AA; margin-top: 2px; display: block; }

.api-card { background: #fff; margin-top: 10px; padding: 16px; border-top: 1px solid #E5E7EB; }
.api-title { font-size: 13px; font-weight: 600; color: #1D1D1F; display: block; margin-bottom: 10px; }
.api-display { display: flex; flex-direction: row; align-items: center; background: #F5F7FA; border: 1px solid #E5E7EB; border-radius: 8px; padding: 10px 12px; gap: 8px; }
.api-key { flex: 1; font-size: 12px; color: #71717A; font-family: 'SF Mono', monospace; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.api-copy { font-size: 12px; color: #4F46E5; font-weight: 600; }

.menu-section { background: #fff; margin-top: 10px; border-top: 1px solid #E5E7EB; }
.menu-section + .menu-section { margin-top: 0; border-top: none; }
.menu-item {
  display: flex; flex-direction: row; align-items: center;
  padding: 14px 16px; border-bottom: 1px solid #F5F5F5;
}
.menu-item:last-child { border-bottom: none; }
.menu-text { flex: 1; font-size: 14px; font-weight: 500; color: #1D1D1F; }
.menu-badge { background: #DC2626; color: #fff; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 8px; margin-right: 8px; }
.menu-arrow { color: #D4D4D8; font-size: 14px; }
.menu-switch { font-size: 13px; color: #71717A; }
.menu-switch.on { color: #059669; font-weight: 600; }
</style>
