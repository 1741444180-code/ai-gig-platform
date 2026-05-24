<template>
  <view class="page-container">
    <!-- Top Nav -->
    <view class="top-nav">
      <text class="logo">AI<text class="logo-hl">Hub</text></text>
      <view class="nav-right">
        <text class="nav-icon" @click="goPublish">发布需求</text>
      </view>
    </view>

    <!-- Filter Tabs -->
    <view class="filter-bar">
      <text
        class="filter-tab"
        :class="{ active: activeFilter === 'all' }"
        @click="activeFilter = 'all'"
      >全部</text>
      <text
        class="filter-tab"
        :class="{ active: activeFilter === 'hot' }"
        @click="activeFilter = 'hot'"
      >热门</text>
      <text
        class="filter-tab"
        :class="{ active: activeFilter === 'urgent' }"
        @click="activeFilter = 'urgent'"
      >紧急</text>
      <text
        class="filter-tab"
        :class="{ active: activeFilter === 'new' }"
        @click="activeFilter = 'new'"
      >最新</text>
    </view>

    <!-- Demand List -->
    <view class="section">
      <demand-card
        v-for="d in filteredDemands" :key="d.id"
        :demand="d"
        @click="goDetail(d.id)"
      />
    </view>

    <view style="height: 24px;"></view>
  </view>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import DemandCard from '../../components/demand-card/index.vue'

const activeFilter = ref('all')

const allDemands = ref([
  {
    id: '1',
    title: '搭建企业级文档智能问答系统',
    desc: '需要一个基于 RAG 架构的文档问答 Agent，支持 PDF/Word 多格式解析，对接内部知识库。',
    tags: [{ label: '🔥 热门', type: 'hot' }, { label: 'NLP' }, { label: 'Python' }],
    budget: '¥8,000',
    budgetType: '固定价',
    bids: 12,
    time: '3 天前',
    filter: 'hot',
  },
  {
    id: '2',
    title: '商品图 AI 批量生成接口',
    desc: '电商商品白底图批量生成，支持 50+ SKU 同时处理。',
    tags: [{ label: '⏰ 紧急', type: 'urgent' }, { label: '图像生成' }],
    budget: '¥5,500',
    budgetType: '固定价',
    bids: 8,
    time: '1 天前',
    filter: 'urgent',
  },
  {
    id: '3',
    title: '语音转文字 + 会议纪要生成',
    desc: '接入 Whisper 或同类模型，实现会议录音自动转写。',
    tags: [{ label: '✨ 新', type: 'new' }, { label: '语音' }, { label: 'API 对接' }],
    budget: '¥3,000–6,000',
    budgetType: '议价',
    bids: 5,
    time: '5 小时前',
    filter: 'new',
  },
  {
    id: '4',
    title: '企业数据看板自动化',
    desc: '需要自动生成周报/月报的可视化方案，对接内部数据库。',
    tags: [{ label: '数据分析' }, { label: 'Python' }],
    budget: '¥4,000',
    budgetType: '固定价',
    bids: 3,
    time: '2 天前',
    filter: 'all',
  },
  {
    id: '5',
    title: '多语言翻译API对接',
    desc: '接入主流翻译引擎，支持中/英/日/韩/法语互译。',
    tags: [{ label: '✨ 新', type: 'new' }, { label: 'NLP' }, { label: '翻译' }],
    budget: '¥6,000–10,000',
    budgetType: '议价',
    bids: 2,
    time: '1 小时前',
    filter: 'new',
  },
])

const filteredDemands = computed(() => {
  if (activeFilter.value === 'all') return allDemands.value
  return allDemands.value.filter(d => d.filter === activeFilter.value)
})

function goPublish() {
  uni.navigateTo({ url: '/pages/publish/publish' })
}

function goDetail(id) {
  uni.navigateTo({ url: `/pages/demand/detail?id=${id}` })
}

onMounted(() => {
  // TODO: 接入真实API
})
</script>

<style scoped>
.top-nav {
  background: #1D1D1F;
  padding: 14px 16px;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  position: sticky;
  top: 0;
  z-index: 100;
}
.logo { font-size: 16px; font-weight: 700; color: #fff; letter-spacing: -0.3px; }
.logo-hl { color: #4F46E5; }
.nav-icon { font-size: 13px; color: #4F46E5; }

.filter-bar {
  display: flex;
  flex-direction: row;
  background: #fff;
  padding: 12px 16px;
  gap: 16px;
  border-bottom: 1px solid #E5E7EB;
  position: sticky;
  top: 48px;
  z-index: 99;
}
.filter-tab {
  font-size: 14px;
  color: #71717A;
  padding: 6px 12px;
  border-radius: 16px;
  background: #F5F7FA;
}
.filter-tab.active {
  color: #4F46E5;
  background: #EEF2FF;
  font-weight: 600;
}

.section { padding: 16px; }
</style>
