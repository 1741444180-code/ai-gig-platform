<template>
  <view class="detail-container" v-if="demand">
    <!-- 基本信息区 -->
    <view class="section basic">
      <view class="title-row">
        <text class="title">{{ demand.title }}</text>
        <text class="status-tag" :class="'status-' + demand.status">{{ demand.status_text || demand.status }}</text>
      </view>
      <view class="info-grid">
        <view class="info-item">
          <text class="info-label">分类</text>
          <text class="info-value">{{ demand.category_text || demand.category }}</text>
        </view>
        <view class="info-item">
          <text class="info-label">预算</text>
          <text class="info-value budget">¥{{ demand.budget }}</text>
        </view>
        <view class="info-item">
          <text class="info-label">截止日期</text>
          <text class="info-value">{{ demand.deadline }}</text>
        </view>
        <view class="info-item">
          <text class="info-label">发布时间</text>
          <text class="info-value">{{ formatTime(demand.created_at) }}</text>
        </view>
      </view>
    </view>

    <!-- 需求描述 -->
    <view class="section">
      <text class="section-title">需求描述</text>
      <text class="description">{{ demand.description }}</text>
    </view>

    <!-- 附件图片 -->
    <view v-if="demand.attachment_url" class="section">
      <text class="section-title">附件图片</text>
      <image :src="demand.attachment_url" class="attachment-img" mode="widthFix" />
    </view>

    <!-- AI标签 -->
    <view v-if="demand.ai_tags && demand.ai_tags.length" class="section">
      <text class="section-title">AI标签</text>
      <view class="tag-list">
        <text v-for="tag in demand.ai_tags" :key="tag" class="tag">{{ tag }}</text>
      </view>
    </view>

    <!-- 匹配Agent列表 -->
    <view class="section">
      <text class="section-title">匹配的AI Agent</text>
      <view v-if="agents.length === 0" class="empty-agents">
        <text>暂无匹配Agent</text>
      </view>
      <view
        v-for="agent in agents"
        :key="agent.id"
        class="agent-card"
      >
        <view class="agent-info">
          <text class="agent-name">{{ agent.name }}</text>
          <text class="agent-desc">{{ agent.description }}</text>
        </view>
        <button class="select-btn" @click="selectAgent(agent)">选择</button>
      </view>
    </view>

    <!-- 底部操作栏 -->
    <view class="bottom-bar" v-if="demand.status === 'open'">
      <button v-if="!isLoggedIn" class="action-btn primary" @click="toLogin">登录后委托</button>
      <button v-else class="action-btn primary" @click="doEntrust">立即委托</button>
    </view>
  </view>

  <view v-else class="loading-page">
    <text>加载中...</text>
  </view>
</template>

<script>
import { demands } from '@/api/index.js'

export default {
  data() {
    return {
      id: null,
      demand: null,
      agents: [],
      isLoggedIn: false,
    }
  },
  onLoad(query) {
    if (query.id) {
      this.id = query.id
      this.loadDetail()
    }
  },
  onShow() {
    this.isLoggedIn = !!uni.getStorageSync('access_token')
  },
  methods: {
    async loadDetail() {
      try {
        uni.showLoading({ title: '加载中...' })
        const [demandRes, agentsRes] = await Promise.all([
          demands.get(this.id),
          demands.getMatches(this.id).catch(() => ({ items: [] })),
        ])
        uni.hideLoading()
        this.demand = demandRes
        this.agents = agentsRes.items || agentsRes || []
      } catch (e) {
        uni.hideLoading()
        uni.showToast({ title: e.message || '加载失败', icon: 'none' })
      }
    },

    formatTime(ts) {
      if (!ts) return ''
      const d = new Date(ts)
      return `${d.getFullYear()}-${(d.getMonth() + 1).toString().padStart(2, '0')}-${d.getDate().toString().padStart(2, '0')}`
    },

    toLogin() {
      uni.navigateTo({ url: '/pages/login/login' })
    },

    selectAgent(agent) {
      if (!this.isLoggedIn) {
        this.toLogin()
        return
      }
      uni.showModal({
        title: '确认委托',
        content: `确定委托给 Agent「${agent.name}」吗？`,
        success: (res) => {
          if (res.confirm) this.doEntrust(agent.id)
        },
      })
    },

    async doEntrust(agentId) {
      try {
        uni.showLoading({ title: '委托中...' })
        // 调用创建订单接口（如果后端有的话）
        // 否则只更新需求状态
        await demands.update(this.id, { status: 'matched', assigned_agent_id: agentId })
        uni.hideLoading()
        uni.showToast({ title: '委托成功', icon: 'success' })
        setTimeout(() => uni.navigateBack(), 1500)
      } catch (e) {
        uni.hideLoading()
        uni.showToast({ title: e.message || '委托失败', icon: 'none' })
      }
    },
  },
}
</script>

<style scoped>
.detail-container {
  padding: 20rpx;
  padding-bottom: 140rpx;
  background: #f5f5f5;
  min-height: 100vh;
}
.section {
  background: #fff;
  border-radius: 12rpx;
  padding: 30rpx;
  margin-bottom: 20rpx;
}
.basic {}
.title-row {
  display: flex;
  align-items: center;
  gap: 20rpx;
  margin-bottom: 24rpx;
}
.title {
  flex: 1;
  font-size: 36rpx;
  font-weight: bold;
  color: #333;
}
.status-tag {
  font-size: 24rpx;
  padding: 6rpx 20rpx;
  border-radius: 20rpx;
  flex-shrink: 0;
}
.status-open { background: #e6f7e6; color: #52c41a; }
.status-matched { background: #e6f0ff; color: #1890ff; }
.status-completed { background: #f0f0f0; color: #999; }
.status-cancelled { background: #fff2e8; color: #ff6600; }

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20rpx;
}
.info-item {}
.info-label {
  display: block;
  font-size: 24rpx;
  color: #999;
  margin-bottom: 8rpx;
}
.info-value {
  display: block;
  font-size: 28rpx;
  color: #333;
}
.info-value.budget {
  color: #ff6b00;
  font-weight: bold;
}
.section-title {
  display: block;
  font-size: 30rpx;
  font-weight: bold;
  color: #333;
  margin-bottom: 20rpx;
}
.description {
  display: block;
  font-size: 28rpx;
  color: #666;
  line-height: 1.8;
}
.attachment-img {
  width: 100%;
  border-radius: 8rpx;
}
.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 16rpx;
}
.tag {
  background: #e6f0ff;
  color: #007aff;
  font-size: 24rpx;
  padding: 8rpx 24rpx;
  border-radius: 20rpx;
}
.empty-agents {
  text-align: center;
  color: #999;
  font-size: 28rpx;
  padding: 40rpx;
}
.agent-card {
  display: flex;
  align-items: center;
  background: #f8f8f8;
  border-radius: 8rpx;
  padding: 24rpx;
  margin-bottom: 16rpx;
}
.agent-info {
  flex: 1;
}
.agent-name {
  display: block;
  font-size: 30rpx;
  font-weight: bold;
  color: #333;
  margin-bottom: 8rpx;
}
.agent-desc {
  display: block;
  font-size: 24rpx;
  color: #666;
}
.select-btn {
  background: #007aff;
  color: #fff;
  font-size: 26rpx;
  padding: 12rpx 32rpx;
  border-radius: 32rpx;
  border: none;
}
.bottom-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 20rpx 40rpx;
  background: #fff;
  border-top: 1px solid #eee;
}
.action-btn {
  width: 100%;
  height: 96rpx;
  line-height: 96rpx;
  border-radius: 48rpx;
  font-size: 34rpx;
  font-weight: bold;
  border: none;
}
.action-btn.primary {
  background: linear-gradient(135deg, #007aff, #0056cc);
  color: #fff;
}
.loading-page {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  color: #999;
}
</style>