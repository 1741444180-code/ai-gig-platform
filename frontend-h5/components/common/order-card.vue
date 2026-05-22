<!-- Order Card 组件 -->
<template>
  <view class="order-card" @click="$emit('click')">
    <view class="order-header">
      <text class="order-title">{{ order.title }}</text>
      <view class="order-status" :class="order.statusType">
        <text>{{ order.status }}</text>
      </view>
    </view>
    <view class="order-body">
      <view class="order-meta">
        <text class="meta-text" v-if="order.agent">Agent: {{ order.agent }}</text>
        <text class="meta-text">{{ order.time }}</text>
      </view>
      <text class="order-price">{{ order.price }}</text>
    </view>
    <view class="order-footer" v-if="order.deadline">
      <text class="deadline-label">截止:</text>
      <text class="deadline-value">{{ order.deadline }}</text>
    </view>
  </view>
</template>

<script setup>
defineProps({
  order: { type: Object, required: true },
})
</script>

<style scoped>
.order-card {
  background: #FFFFFF;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 10px;
  border: 1px solid #E8E8EC;
}
.order-header {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.order-title { font-size: 14px; font-weight: 600; color: #1D1D1F; flex: 1; }
.order-status { padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 500; }
.order-status.pending { background: #EEF2FF; color: #4F46E5; }
.order-status.processing { background: #FFF7ED; color: #EA580C; }
.order-status.delivered { background: #EEF2FF; color: #4F46E5; }
.order-status.completed { background: #ECFDF5; color: #059669; }
.order-body {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
}
.order-meta { display: flex; flex-direction: row; gap: 12px; }
.meta-text { font-size: 12px; color: #A1A1AA; }
.order-price { font-size: 16px; font-weight: 700; color: #4F46E5; }
.order-footer { margin-top: 8px; padding-top: 8px; border-top: 1px solid #F0F0F0; }
.deadline-label { font-size: 11px; color: #A1A1AA; }
.deadline-value { font-size: 11px; color: #EA580C; font-weight: 500; margin-left: 4px; }
</style>
