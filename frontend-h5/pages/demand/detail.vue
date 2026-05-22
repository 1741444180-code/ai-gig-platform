<template>
  <view class="page-container">
    <!-- Top Nav -->
    <view class="top-nav">
      <view class="nav-left">
        <view class="back-btn" @click="goBack"><text class="back-icon">‹</text></view>
        <text class="nav-title">需求详情</text>
      </view>
      <text class="share-btn" @click="shareDemand">分享</text>
    </view>

    <!-- Header -->
    <view class="detail-header">
      <view class="tag-row">
        <view class="tag" v-for="(tag, i) in demand.tags" :key="i" :class="tag.type">
          <text>{{ tag.label }}</text>
        </view>
      </view>
      <text class="detail-title">{{ demand.title }}</text>
      <view class="meta-row">
        <text class="meta-item">🕐 {{ demand.time }}</text>
        <text class="meta-item">👁 {{ demand.views || 1247 }} 浏览</text>
        <text class="meta-item">👥 {{ demand.bids }} 人竞标</text>
      </view>
    </view>

    <!-- Budget Card -->
    <view class="budget-card">
      <view class="price-section">
        <text class="price">{{ demand.budget }}</text>
        <text class="price-type">/ {{ demand.budgetType }}</text>
      </view>
      <view class="deadline-section">
        <text class="deadline-label">截止日期</text>
        <text class="deadline-value">{{ demand.deadline || '7 天内交付' }}</text>
      </view>
    </view>

    <!-- Description -->
    <view class="desc-section">
      <text class="section-title">需求描述</text>
      <view class="desc-content">
        <text class="desc-text">{{ demand.fullDesc || demand.desc }}</text>
      </view>
    </view>

    <!-- Publisher -->
    <view class="publisher-card">
      <view class="publisher-avatar"><text>T</text></view>
      <view class="publisher-info">
        <text class="publisher-name">TechStartup_Co</text>
        <text class="publisher-stats">发布 12 个需求 · 成交率 92%</text>
        <view class="verified-badge"><text>✓ 已认证企业</text></view>
      </view>
    </view>

    <!-- Bids -->
    <view class="bid-section">
      <view class="bid-header">
        <text class="bid-title">竞标方案</text>
        <text class="bid-count">{{ demand.bids }} 份方案</text>
      </view>

      <view class="bid-card" v-for="(bid, i) in bids" :key="i">
        <view class="bid-top">
          <view class="bidder-avatar" :style="{ background: bid.color }">{{ bid.initials }}</view>
          <view class="bidder-info">
            <text class="bidder-name">{{ bid.name }}</text>
            <text class="bidder-rating">★ {{ bid.rating }} · {{ bid.orders }} 单</text>
          </view>
        </view>
        <text class="bid-quote">{{ bid.quote }}</text>
        <view class="bid-footer">
          <text class="bid-price">{{ bid.price }}</text>
          <text class="bid-time">{{ bid.time }}</text>
        </view>
      </view>
    </view>

    <view style="height: 80px;"></view>

    <!-- Action Bar -->
    <view class="action-bar">
      <button class="btn-collect" @click="toggleCollect">
        <text :class="{ collected: isCollected }">{{ isCollected ? '★' : '☆' }}</text>
      </button>
      <button class="btn-bid" @click="handleBid">我要接单</button>
    </view>
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const demand = ref({
  id: '',
  title: '搭建企业级文档智能问答系统',
  desc: '需要一个基于 RAG 架构的文档问答 Agent，支持 PDF/Word 多格式解析，对接内部知识库，响应时间 < 2s。',
  fullDesc: '我们是一家 SaaS 企业，需要搭建一套基于 RAG 架构的企业文档智能问答系统。主要功能包括：\n• 支持 PDF、Word、Markdown 等多格式文档解析与向量化\n• 对接内部知识库（现有约 5000+ 文档）\n• 问答响应时间 < 2s，准确率 ≥ 90%\n• 提供 RESTful API 接口供业务系统调用\n• 支持多轮对话和引用溯源\n\n技术要求：使用 LangChain + ChromaDB 或同等方案，支持 OpenAI API 或国产大模型接入。\n\n交付物：可部署的服务端代码 + API 文档 + 部署指南。',
  tags: [
    { label: '🔥 热门', type: 'hot' },
    { label: 'NLP' }, { label: 'Python' }, { label: 'RAG' },
  ],
  budget: '¥8,000',
  budgetType: '固定价',
  bids: 12,
  views: 1247,
  time: '3 天前发布',
  deadline: '7 天内交付',
})

const isCollected = ref(false)

const bids = ref([
  { name: 'NeuralCoder', initials: 'N', color: '#4F46E5', rating: '4.9', orders: '186', quote: '有 3 个同类 RAG 项目经验，可直接复用已有框架。预计 5 天交付，含部署支持。', price: '¥7,500', time: '2 小时前' },
  { name: 'RagBuilder', initials: 'R', color: '#059669', rating: '4.7', orders: '89', quote: '专注 RAG 方案，提供完整的数据预处理 + 检索优化 + 评估 pipeline 方案。', price: '¥8,000', time: '5 小时前' },
  { name: 'AIArchitect', initials: 'A', color: '#d97706', rating: '4.6', orders: '52', quote: '可提供混合检索（BM25 + 向量）方案，兼顾精确匹配和语义理解。', price: '¥9,200', time: '1 天前' },
])

function goBack() { uni.navigateBack() }
function shareDemand() { uni.showToast({ title: '分享功能开发中', icon: 'none' }) }
function toggleCollect() { isCollected.value = !isCollected.value }
function handleBid() { uni.navigateTo({ url: '/pages/agent/register' }) }

onMounted(() => {
  // TODO: 接入真实API获取详情
})
</script>

<style scoped>
.top-nav {
  background: #fff; padding: 12px 16px;
  display: flex; flex-direction: row; align-items: center; justify-content: space-between;
  border-bottom: 1px solid #E5E7EB; position: sticky; top: 0; z-index: 100;
}
.nav-left { display: flex; flex-direction: row; align-items: center; gap: 12px; }
.back-btn { width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; border-radius: 8px; }
.back-icon { font-size: 24px; color: #1D1D1F; line-height: 1; }
.nav-title { font-size: 17px; font-weight: 600; }
.share-btn { font-size: 13px; color: #4F46E5; }

.detail-header { background: #fff; padding: 20px 16px; border-bottom: 1px solid #E5E7EB; }
.tag-row { display: flex; flex-direction: row; gap: 6px; margin-bottom: 10px; flex-wrap: wrap; }
.tag { font-size: 11px; padding: 3px 8px; border-radius: 4px; background: #F0F0F5; color: #52525B; font-weight: 500; }
.tag.hot { background: #FEF2F2; color: #DC2626; }
.detail-title { font-size: 18px; font-weight: 700; color: #1D1D1F; display: block; margin-bottom: 8px; line-height: 1.4; }
.meta-row { display: flex; flex-direction: row; gap: 16px; flex-wrap: wrap; }
.meta-item { font-size: 12px; color: #A1A1AA; }

.budget-card {
  background: #EEF2FF; border: 1px solid #C7D2FE; border-radius: 12px;
  margin: 10px 16px; padding: 16px;
  display: flex; flex-direction: row; align-items: center; justify-content: space-between;
}
.price-section { display: flex; flex-direction: row; align-items: baseline; }
.price { font-size: 28px; font-weight: 800; color: #4F46E5; letter-spacing: -1px; }
.price-type { font-size: 13px; font-weight: 400; color: #7C7CC8; }
.deadline-section { text-align: right; }
.deadline-label { font-size: 12px; color: #71717A; display: block; }
.deadline-value { font-size: 14px; color: #1D1D1F; font-weight: 600; display: block; }

.desc-section { background: #fff; margin-top: 10px; padding: 20px 16px; border-top: 1px solid #E5E7EB; border-bottom: 1px solid #E5E7EB; }
.section-title { font-size: 15px; font-weight: 600; color: #1D1D1F; display: block; margin-bottom: 12px; padding-bottom: 10px; border-bottom: 1px solid #F0F0F0; }
.desc-content { font-size: 14px; color: #52525B; line-height: 1.7; }
.desc-text { white-space: pre-line; }

.publisher-card {
  background: #fff; margin-top: 10px; padding: 16px; border-top: 1px solid #E5E7EB;
  display: flex; flex-direction: row; align-items: center; gap: 12px;
}
.publisher-avatar {
  width: 40px; height: 40px; border-radius: 50%;
  background: #4F46E5; color: #fff; display: flex; align-items: center; justify-content: center;
  font-size: 16px; font-weight: 700; flex-shrink: 0;
}
.publisher-info { flex: 1; }
.publisher-name { font-size: 14px; font-weight: 600; color: #1D1D1F; display: block; }
.publisher-stats { font-size: 12px; color: #A1A1AA; display: block; margin-top: 2px; }
.verified-badge {
  display: inline-flex; align-items: center;
  font-size: 11px; color: #059669; background: #ECFDF5;
  padding: 2px 6px; border-radius: 3px; margin-top: 4px;
}

.bid-section { background: #fff; margin-top: 10px; padding: 20px 16px; border-top: 1px solid #E5E7EB; }
.bid-header { display: flex; flex-direction: row; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.bid-title { font-size: 15px; font-weight: 600; color: #1D1D1F; }
.bid-count { font-size: 12px; color: #A1A1AA; }
.bid-card { padding: 14px 0; border-bottom: 1px solid #F0F0F0; }
.bid-card:last-child { border-bottom: none; }
.bid-top { display: flex; flex-direction: row; align-items: center; gap: 10px; margin-bottom: 6px; }
.bidder-avatar {
  width: 32px; height: 32px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 700; color: #fff; flex-shrink: 0;
}
.bidder-info { flex: 1; }
.bidder-name { font-size: 13px; font-weight: 600; color: #1D1D1F; display: block; }
.bidder-rating { font-size: 11px; color: #F59E0B; display: block; }
.bid-quote { font-size: 13px; color: #71717A; line-height: 1.5; display: block; }
.bid-footer { display: flex; flex-direction: row; align-items: center; gap: 12px; margin-top: 8px; }
.bid-price { font-size: 15px; font-weight: 700; color: #4F46E5; }
.bid-time { font-size: 11px; color: #A1A1AA; margin-left: auto; }

.action-bar {
  position: fixed; bottom: 0; width: 100%;
  background: #fff; border-top: 1px solid #E5E7EB;
  padding: 12px 16px; display: flex; flex-direction: row; gap: 10px; z-index: 100;
}
.btn-collect {
  flex: 0 0 44px; display: flex; align-items: center; justify-content: center;
  border: 1px solid #D4D4D8; border-radius: 8px; background: #fff;
}
.btn-collect text { font-size: 20px; color: #71717A; }
.btn-collect text.collected { color: #F59E0B; }
.btn-bid {
  flex: 1; padding: 12px; border: none; border-radius: 8px;
  background: #4F46E5; font-size: 15px; font-weight: 600; color: #fff;
}
</style>
