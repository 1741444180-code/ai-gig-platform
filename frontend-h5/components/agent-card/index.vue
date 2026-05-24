<!-- Agent Card 组件 - 风格A -->
<template>
  <view class="agent-card">
    <view class="agent-avatar" :style="{ background: agent.color }">
      <text>{{ agent.initials }}</text>
    </view>
    <view class="agent-info">
      <text class="name">{{ agent.name }}</text>
      <text class="skills">{{ agent.skills }}</text>
    </view>
    <view class="agent-stats">
      <text class="rating">★ {{ agent.rating }}</text>
      <text class="orders">{{ agent.orders }}</text>
    </view>
  </view>
</template>

<script setup>
defineProps({
  agent: { type: Object, required: true },
})
</script>

<style scoped>
.agent-card {
  background: #FFFFFF;
  border-radius: 12px;
  padding: 14px 16px;
  margin-bottom: 10px;
  border: 1px solid #E8E8EC;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 12px;
}
.agent-avatar {
  width: 44px; height: 44px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; font-weight: 700; color: #fff; flex-shrink: 0;
}
.agent-info { flex: 1; min-width: 0; }
.agent-info .name { font-size: 14px; font-weight: 600; color: #1D1D1F; display: block; }
.agent-info .skills { font-size: 12px; color: #71717A; display: block; margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.agent-stats { text-align: right; flex-shrink: 0; }
.agent-stats .rating { font-size: 13px; font-weight: 600; color: #F59E0B; display: block; }
.agent-stats .orders { font-size: 11px; color: #A1A1AA; display: block; margin-top: 2px; }
</style>
