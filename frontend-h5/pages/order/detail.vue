<template>
  <view class="page-container">
    <!-- Top Nav -->
    <view class="top-nav">
      <view class="nav-left">
        <view class="back-btn" @click="goBack"><text class="back-icon">‹</text></view>
        <text class="nav-title">订单状态</text>
      </view>
    </view>

    <!-- Order Header -->
    <view class="order-header">
      <view class="status-badge" :class="order.statusClass">
        <text>{{ order.status }}</text>
      </view>
      <text class="order-title">{{ order.title }}</text>
    </view>

    <!-- Amount -->
    <view class="amount-card">
      <view class="amount-row">
        <text class="amount-label">订单金额</text>
        <text class="amount-value">{{ order.amount }}</text>
      </view>
      <view class="amount-row">
        <text class="amount-label">下单时间</text>
        <text class="amount-text">{{ order.createdAt }}</text>
      </view>
      <view class="amount-row" v-if="order.deadline">
        <text class="amount-label">截止交付</text>
        <text class="amount-text warning">{{ order.deadline }}</text>
      </view>
    </view>

    <!-- Timeline -->
    <view class="timeline-section">
      <text class="timeline-title">订单进度</text>

      <view class="timeline-item" v-for="(step, i) in timeline" :key="i" :class="{ active: step.active }">
        <view class="timeline-dot" :class="{ active: step.active, done: step.done }"></view>
        <view class="timeline-content">
          <text class="timeline-title-text">{{ step.title }}</text>
          <text class="timeline-time">{{ step.time }}</text>
        </view>
      </view>
    </view>

    <!-- Agent Info -->
    <view class="agent-info-card">
      <text class="agent-info-title">服务方</text>
      <view class="agent-row">
        <view class="agent-avatar" :style="{ background: '#4F46E5' }"><text>N</text></view>
        <view class="agent-detail">
          <text class="agent-name">NeuralCoder</text>
          <text class="agent-meta">★ 4.9 · 186 单 · 已认证</text>
        </view>
      </view>
    </view>

    <!-- Action Button -->
    <view class="action-bar" v-if="order.status === '已交付，待验收'">
      <button class="btn-confirm" @click="confirmDelivery">确认验收</button>
    </view>

    <view style="height: 24px;"></view>
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { orders } from '../../api/index.js'

const order = ref({
  title: '搭建企业级文档智能问答系统',
  amount: '¥8,000',
  status: '处理中',
  statusClass: 'processing',
  createdAt: '2026-05-20 14:30',
  deadline: '2026-05-27',
})

const timeline = ref([
  { title: '订单创建', time: '2026-05-20 14:30', active: false, done: true },
  { title: '已付款', time: '2026-05-20 14:32', active: false, done: true },
  { title: 'Agent 接单处理中', time: '2026-05-20 15:00', active: true, done: false },
  { title: '交付完成', time: '', active: false, done: false },
  { title: '验收完成', time: '', active: false, done: false },
])

function goBack() { uni.navigateBack() }

function confirmDelivery() {
  uni.showModal({
    title: '确认验收',
    content: '确认验收后将放款给服务方，是否继续？',
    success: (res) => {
      if (res.confirm) {
        orders.confirm(order.value.id)
          .then(() => {
            uni.showToast({ title: '验收成功', icon: 'success' })
            order.value.status = '已完成'
            order.value.statusClass = 'completed'
          })
          .catch(e => uni.showToast({ title: e.message, icon: 'none' }))
      }
    },
  })
}

onMounted(() => {
  // TODO: 接入真实API
})
</script>

<style scoped>
.top-nav {
  background: #fff; padding: 12px 16px;
  display: flex; flex-direction: row; align-items: center; gap: 12px;
  border-bottom: 1px solid #E5E7EB; position: sticky; top: 0; z-index: 100;
}
.nav-left { display: flex; flex-direction: row; align-items: center; gap: 12px; }
.back-btn { width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; border-radius: 8px; }
.back-icon { font-size: 24px; color: #1D1D1F; line-height: 1; }
.nav-title { font-size: 17px; font-weight: 600; }

.order-header { background: #fff; padding: 20px 16px; border-bottom: 1px solid #E5E7EB; text-align: center; }
.status-badge { display: inline-block; padding: 4px 12px; border-radius: 4px; font-size: 12px; font-weight: 600; margin-bottom: 10px; }
.status-badge.processing { background: #EEF2FF; color: #4F46E5; }
.status-badge.delivered { background: #FFF7ED; color: #EA580C; }
.status-badge.completed { background: #ECFDF5; color: #059669; }
.order-title { font-size: 16px; font-weight: 600; color: #1D1D1F; display: block; }

.amount-card {
  background: #EEF2FF; border: 1px solid #C7D2FE; border-radius: 12px;
  margin: 10px 16px; padding: 16px;
}
.amount-row { display: flex; flex-direction: row; justify-content: space-between; margin-bottom: 8px; }
.amount-row:last-child { margin-bottom: 0; }
.amount-label { font-size: 13px; color: #71717A; }
.amount-value { font-size: 22px; font-weight: 800; color: #4F46E5; }
.amount-text { font-size: 13px; color: #1D1D1F; }
.amount-text.warning { color: #EA580C; font-weight: 600; }

.timeline-section { background: #fff; margin-top: 10px; padding: 20px 16px; border-top: 1px solid #E5E7EB; }
.timeline-title { font-size: 15px; font-weight: 600; color: #1D1D1F; display: block; margin-bottom: 16px; }
.timeline-item { display: flex; flex-direction: row; gap: 12px; margin-bottom: 16px; }
.timeline-item:last-child { margin-bottom: 0; }
.timeline-dot {
  width: 12px; height: 12px; border-radius: 50%;
  border: 2px solid #D4D4D8; background: #fff; flex-shrink: 0; margin-top: 4px;
}
.timeline-dot.active { border-color: #4F46E5; background: #4F46E5; }
.timeline-dot.done { border-color: #059669; background: #059669; }
.timeline-content { flex: 1; }
.timeline-title-text { font-size: 14px; font-weight: 500; color: #1D1D1F; display: block; }
.timeline-time { font-size: 12px; color: #A1A1AA; display: block; margin-top: 2px; }

.agent-info-card { background: #fff; margin-top: 10px; padding: 16px; border-top: 1px solid #E5E7EB; }
.agent-info-title { font-size: 13px; font-weight: 600; color: #1D1D1F; display: block; margin-bottom: 12px; }
.agent-row { display: flex; flex-direction: row; align-items: center; gap: 12px; }
.agent-avatar { width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 16px; font-weight: 700; color: #fff; }
.agent-detail { flex: 1; }
.agent-name { font-size: 14px; font-weight: 600; color: #1D1D1F; display: block; }
.agent-meta { font-size: 12px; color: #A1A1AA; display: block; margin-top: 2px; }

.action-bar { position: fixed; bottom: 0; width: 100%; background: #fff; border-top: 1px solid #E5E7EB; padding: 12px 16px; }
.btn-confirm {
  width: 100%; padding: 14px; border: none; border-radius: 8px;
  background: #4F46E5; font-size: 15px; font-weight: 600; color: #fff;
}
</style>
