<!-- Demand Card 组件 - 风格A 简洁专业 -->
<template>
  <view class="demand-card" @click="$emit('click')">
    <view class="color-bar" :class="barClass"></view>
    <view class="card-inner">
      <view class="tag-row">
        <view class="tag" v-for="(tag, i) in demand.tags" :key="i" :class="tag.type">
          <text>{{ tag.label }}</text>
        </view>
      </view>
      <text class="title">{{ demand.title }}</text>
      <text class="desc">{{ demand.desc }}</text>
      <view class="meta">
        <view class="budget">
          <text class="budget-text">{{ demand.budget }}</text>
          <text class="budget-type">/ {{ demand.budgetType }}</text>
        </view>
        <view class="info">
          <text class="info-item">{{ demand.bids }} 人竞标</text>
          <text class="info-item">{{ demand.time }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  demand: { type: Object, required: true },
})

const barClass = computed(() => {
  const tags = props.demand.tags || []
  for (const tag of tags) {
    if (tag.type === 'hot') return 'hot'
    if (tag.type === 'urgent') return 'urgent'
    if (tag.type === 'new') return 'new'
  }
  return 'new'
})
</script>

<style scoped>
.demand-card {
  background: #FFFFFF;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 10px;
  border: 1px solid #E8E8EC;
  position: relative;
  overflow: hidden;
}
.color-bar {
  position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
}
.color-bar.hot { background: #DC2626; }
.color-bar.urgent { background: #EA580C; }
.color-bar.new { background: #4F46E5; }
.card-inner { padding-left: 8px; }
.tag-row { display: flex; flex-direction: row; gap: 6px; margin-bottom: 8px; flex-wrap: wrap; }
.tag {
  font-size: 11px; padding: 3px 8px; border-radius: 4px;
  background: #F0F0F5; color: #52525B; font-weight: 500;
}
.tag.hot { background: #FEF2F2; color: #DC2626; }
.tag.urgent { background: #FFF7ED; color: #EA580C; }
.tag.new { background: #EEF2FF; color: #4F46E5; }
.title {
  font-size: 15px; font-weight: 600; color: #1D1D1F;
  display: block; margin-bottom: 6px; line-height: 1.4;
}
.desc {
  font-size: 13px; color: #71717A; line-height: 1.5;
  display: block; margin-bottom: 12px;
  overflow: hidden; text-overflow: ellipsis;
  -webkit-line-clamp: 2; display: -webkit-box;
  -webkit-box-orient: vertical;
}
.meta { display: flex; flex-direction: row; align-items: center; justify-content: space-between; }
.budget { display: flex; flex-direction: row; align-items: baseline; }
.budget-text { font-size: 17px; font-weight: 700; color: #4F46E5; }
.budget-type { font-size: 11px; font-weight: 400; color: #A1A1AA; }
.info { display: flex; flex-direction: row; gap: 12px; }
.info-item { font-size: 11px; color: #A1A1AA; }
</style>
