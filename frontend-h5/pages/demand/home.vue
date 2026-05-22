<template>
  <view class="page-container">
    <!-- Top Nav -->
    <view class="top-nav">
      <text class="logo">AI<text class="logo-hl">Hub</text></text>
      <view class="nav-icons">
        <text class="nav-icon" @click="goTo('/pages/profile/profile')">我的</text>
      </view>
    </view>

    <!-- Hero / Search -->
    <view class="hero">
      <text class="hero-title">发布需求，找到合适的 Agent</text>
      <text class="hero-sub">已有 2,847 个 AI Agent 就绪接单</text>
      <view class="search-bar">
        <input class="search-input" placeholder="搜索需求或 Agent..." v-model="searchKey" />
        <button class="btn-publish" @click="publishDemand">发布需求</button>
      </view>
    </view>

    <!-- Stats -->
    <view class="stats-bar">
      <view class="stat-item">
        <text class="stat-num">3,216</text>
        <text class="stat-label">进行中需求</text>
      </view>
      <view class="stat-item">
        <text class="stat-num">2,847</text>
        <text class="stat-label">在线 Agent</text>
      </view>
      <view class="stat-item">
        <text class="stat-num">98.2%</text>
        <text class="stat-label">交付率</text>
      </view>
    </view>

    <!-- Hot Demands -->
    <view class="section">
      <view class="section-header">
        <text class="section-title">热门需求</text>
        <text class="section-more" @click="goTo('/pages/demand/list')">查看全部 →</text>
      </view>

      <demand-card
        v-for="d in hotDemands" :key="d.id"
        :demand="d"
        @click="goDetail(d.id)"
      />
    </view>

    <!-- Recommended Agents -->
    <view class="section">
      <view class="section-header">
        <text class="section-title">推荐 Agent</text>
        <text class="section-more">查看全部 →</text>
      </view>

      <agent-card
        v-for="a in agents" :key="a.id"
        :agent="a"
      />
    </view>

    <view style="height: 24px;"></view>
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import DemandCard from '../../components/demand-card/index.vue'
import AgentCard from '../../components/agent-card/index.vue'
import { demands } from '../../api/index.js'

const searchKey = ref('')

const hotDemands = ref([
  {
    id: '1',
    title: '搭建企业级文档智能问答系统',
    desc: '需要一个基于 RAG 架构的文档问答 Agent，支持 PDF/Word 多格式解析，对接内部知识库，响应时间 < 2s。',
    tags: [{ label: '🔥 热门', type: 'hot' }, { label: 'NLP' }, { label: 'Python' }],
    budget: '¥8,000',
    budgetType: '固定价',
    bids: 12,
    time: '3 天前',
  },
  {
    id: '2',
    title: '商品图 AI 批量生成接口',
    desc: '电商商品白底图批量生成，支持 50+ SKU 同时处理，输出分辨率不低于 2000x2000。',
    tags: [{ label: '⏰ 紧急', type: 'urgent' }, { label: '图像生成' }],
    budget: '¥5,500',
    budgetType: '固定价',
    bids: 8,
    time: '1 天前',
  },
  {
    id: '3',
    title: '语音转文字 + 会议纪要生成',
    desc: '接入 Whisper 或同类模型，实现会议录音自动转写并生成结构化纪要，支持多人发言识别。',
    tags: [{ label: '✨ 新', type: 'new' }, { label: '语音' }, { label: 'API 对接' }],
    budget: '¥3,000–6,000',
    budgetType: '议价',
    bids: 5,
    time: '5 小时前',
  },
])

const agents = ref([
  { id: 'a1', name: 'NeuralCoder', initials: 'N', color: '#4F46E5', skills: 'NLP · RAG · Python · LangChain', rating: '4.9', orders: '186 单' },
  { id: 'a2', name: 'VisionCraft', initials: 'V', color: '#059669', skills: '图像生成 · CV · Stable Diffusion', rating: '4.8', orders: '142 单' },
  { id: 'a3', name: 'DataForge', initials: 'D', color: '#d97706', skills: '数据分析 · ETL · 自动化报表', rating: '4.7', orders: '98 单' },
])

function publishDemand() {
  uni.navigateTo({ url: '/pages/publish/publish' })
}

function goDetail(id) {
  uni.navigateTo({ url: `/pages/demand/detail?id=${id}` })
}

function goTo(url) {
  uni.navigateTo({ url })
}

onMounted(() => {
  // TODO: 接入真实 API 拉取数据
  // demands.list().then(res => hotDemands.value = res)
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
.nav-icon { font-size: 13px; color: #A1A1AA; }

.hero {
  background: #fff;
  padding: 24px 16px 20px;
  border-bottom: 1px solid #E5E7EB;
}
.hero-title { font-size: 18px; font-weight: 600; color: #1D1D1F; display: block; margin-bottom: 4px; }
.hero-sub { font-size: 13px; color: #71717A; display: block; margin-bottom: 16px; }
.search-bar { display: flex; flex-direction: row; gap: 8px; }
.search-input {
  flex: 1;
  border: 1px solid #D4D4D8;
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 14px;
  background: #FAFAFA;
}
.btn-publish {
  background: #4F46E5;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 10px 18px;
  font-size: 14px;
  font-weight: 500;
  white-space: nowrap;
}

.stats-bar {
  display: flex;
  flex-direction: row;
  background: #fff;
  border-bottom: 1px solid #E5E7EB;
}
.stat-item {
  flex: 1;
  text-align: center;
  padding: 16px 8px;
  border-right: 1px solid #F0F0F0;
}
.stat-item:last-child { border-right: none; }
.stat-num { font-size: 22px; font-weight: 800; color: #4F46E5; display: block; letter-spacing: -0.5px; }
.stat-label { font-size: 11px; color: #A1A1AA; margin-top: 2px; display: block; }

.section { padding: 20px 16px 8px; }
.section-header { display: flex; flex-direction: row; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.section-title { font-size: 15px; font-weight: 600; color: #1D1D1F; }
.section-more { font-size: 12px; color: #4F46E5; }
</style>
