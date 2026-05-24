<template>
  <view class="detail-page">
    <view v-if="loading" class="loading-wrap">
      <text>加载中...</text>
    </view>

    <view v-else-if="demand" class="detail-content">
      <!-- 需求详情 -->
      <view class="section">
        <view class="section-header">
          <text class="section-title">需求详情</text>
          <text class="status-badge" :class="'status-' + demand.status">
            {{ statusText(demand.status) }}
          </text>
        </view>
        <text class="demand-title">{{ demand.title }}</text>
        <view class="demand-meta">
          <text class="meta-tag">{{ demand.category_name }}</text>
          <text class="meta-budget">¥{{ demand.budget }}</text>
          <text class="meta-deadline">截止: {{ demand.deadline }}</text>
        </view>
        <text class="demand-desc">{{ demand.description }}</text>

        <!-- 附件图片 -->
        <view v-if="demand.attachments && demand.attachments.length > 0" class="attachment-list">
          <text class="attachment-label">附件:</text>
          <image
            v-for="(img, idx) in demand.attachments"
            :key="idx"
            :src="img"
            mode="aspectFill"
            class="attachment-img"
            @click="previewImage(idx)"
          />
        </view>
      </view>

      <!-- AI标签 -->
      <view class="section" v-if="demand.ai_tags && demand.ai_tags.length > 0">
        <view class="section-header">
          <text class="section-title">AI 智能分析</text>
        </view>
        <view class="tag-list">
          <text v-for="tag in demand.ai_tags" :key="tag" class="ai-tag">
            {{ tag }}
          </text>
        </view>
      </view>

      <!-- 匹配Agent列表 -->
      <view class="section">
        <view class="section-header">
          <text class="section-title">推荐 Agent ({{ agentList.length }})</text>
        </view>

        <view v-if="loadingAgents" class="agent-loading">
          <text>正在匹配 Agent...</text>
        </view>

        <view v-else-if="agentList.length === 0" class="agent-empty">
          <text class="agent-empty-icon">🤖</text>
          <text class="agent-empty-text">暂无匹配的 Agent</text>
        </view>

        <view v-for="agent in agentList" :key="agent.id" class="agent-card">
          <view class="agent-info">
            <view class="agent-avatar">{{ agent.name.charAt(0) }}</view>
            <view class="agent-detail">
              <text class="agent-name">{{ agent.name }}</text>
              <view class="agent-stats">
                <text class="agent-credit">信用分: {{ agent.credit_score }}</text>
                <text class="agent-completion">完成: {{ agent.completed_count }}单</text>
              </view>
            </view>
          </view>
          <view class="agent-match">
            <text class="match-percent">{{ agent.match_score }}%</text>
            <text class="match-label">匹配度</text>
          </view>
          <button
            class="agent-assign-btn"
            @click="assignToAgent(agent)"
            :disabled="demand.status !== 0"
          >
            {{ demand.status === 0 ? '指派接单' : '已接单' }}
          </button>
        </view>
      </view>
    </view>

    <view v-else class="error-wrap">
      <text class="error-icon">⚠️</text>
      <text class="error-text">加载失败</text>
    </view>
  </view>
</template>

<script>
import demandApi from '@/api/demand.js';

export default {
  data() {
    return {
      demandId: null,
      demand: null,
      agentList: [],
      loading: true,
      loadingAgents: true
    };
  },

  onLoad(options) {
    this.demandId = options.id;
    this.fetchDetail();
    this.fetchMatchingAgents();
  },

  methods: {
    async fetchDetail() {
      this.loading = true;
      try {
        const res = await demandApi.getDetail(this.demandId);
        this.demand = res.data || res;
      } catch (e) {
        console.error('fetchDetail error:', e);
        this.demand = null;
      } finally {
        this.loading = false;
      }
    },

    async fetchMatchingAgents() {
      this.loadingAgents = true;
      try {
        const res = await demandApi.getMatchingAgents(this.demandId);
        this.agentList = res.data || res.list || res || [];
      } catch (e) {
        console.error('fetchMatchingAgents error:', e);
        this.agentList = [];
      } finally {
        this.loadingAgents = false;
      }
    },

    statusText(status) {
      const map = { 0: '待接单', 1: '进行中', 2: '已完成', 3: '已取消' };
      return map[status] || '未知';
    },

    previewImage(idx) {
      uni.previewImage({
        current: idx,
        urls: this.demand.attachments
      });
    },

    async assignToAgent(agent) {
      if (this.demand.status !== 0) return;

      uni.showModal({
        title: '确认指派',
        content: `确认将需求指派给 Agent「${agent.name}」接单？`,
        success: async (res) => {
          if (!res.confirm) return;
          try {
            await demandApi.assignAgent(this.demandId, { agent_id: agent.id });
            uni.showToast({ title: '指派成功', icon: 'success' });
            this.demand.status = 1;
          } catch (e) {
            console.error('assign error:', e);
          }
        }
      });
    }
  }
};
</script>

<style scoped>
.detail-page {
  min-height: 100vh;
  background-color: #F5F7FA;
}

.loading-wrap, .error-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 60vh;
  font-size: 28rpx;
  color: #999;
}

.error-icon {
  font-size: 64rpx;
  margin-bottom: 16rpx;
}

.error-text {
  font-size: 28rpx;
  color: #999;
}

.detail-content {
  padding: 24rpx;
}

.section {
  background-color: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 24rpx;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20rpx;
  padding-bottom: 16rpx;
  border-bottom: 1rpx solid #f0f0f0;
}

.section-title {
  font-size: 30rpx;
  font-weight: bold;
  color: #333;
}

.status-badge {
  font-size: 24rpx;
  padding: 6rpx 16rpx;
  border-radius: 8rpx;
}

.status-0 {
  color: #3B82F6;
  background-color: #EBF5FF;
}

.status-1 {
  color: #F59E0B;
  background-color: #FFF7ED;
}

.status-2 {
  color: #10B981;
  background-color: #ECFDF5;
}

.status-3 {
  color: #999;
  background-color: #F3F4F6;
}

.demand-title {
  font-size: 36rpx;
  font-weight: bold;
  color: #333;
  line-height: 1.4;
  margin-bottom: 16rpx;
}

.demand-meta {
  display: flex;
  align-items: center;
  gap: 16rpx;
  flex-wrap: wrap;
  margin-bottom: 20rpx;
}

.meta-tag {
  font-size: 24rpx;
  color: #3B82F6;
  background-color: #EBF5FF;
  padding: 6rpx 16rpx;
  border-radius: 8rpx;
}

.meta-budget {
  font-size: 32rpx;
  font-weight: bold;
  color: #EF4444;
}

.meta-deadline {
  font-size: 24rpx;
  color: #999;
}

.demand-desc {
  font-size: 28rpx;
  color: #666;
  line-height: 1.7;
  white-space: pre-wrap;
}

/* 附件 */
.attachment-list {
  margin-top: 20rpx;
}

.attachment-label {
  font-size: 26rpx;
  color: #666;
  display: block;
  margin-bottom: 12rpx;
}

.attachment-img {
  width: 160rpx;
  height: 160rpx;
  border-radius: 12rpx;
  margin-right: 16rpx;
}

/* AI标签 */
.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
}

.ai-tag {
  font-size: 24rpx;
  color: #8B5CF6;
  background: linear-gradient(135deg, #F3F0FF, #EDE9FE);
  padding: 8rpx 20rpx;
  border-radius: 24rpx;
  border: 1rpx solid #DDD6FE;
}

/* Agent列表 */
.agent-loading, .agent-empty {
  text-align: center;
  padding: 40rpx 0;
  color: #999;
  font-size: 26rpx;
}

.agent-empty-icon {
  font-size: 64rpx;
  display: block;
  margin-bottom: 12rpx;
}

.agent-card {
  display: flex;
  align-items: center;
  padding: 20rpx 0;
  border-bottom: 1rpx solid #f0f0f0;
  gap: 16rpx;
}

.agent-card:last-child {
  border-bottom: none;
}

.agent-avatar {
  width: 72rpx;
  height: 72rpx;
  border-radius: 50%;
  background-color: #3B82F6;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32rpx;
  font-weight: bold;
  flex-shrink: 0;
}

.agent-detail {
  flex: 1;
}

.agent-name {
  font-size: 28rpx;
  font-weight: bold;
  color: #333;
  display: block;
  margin-bottom: 6rpx;
}

.agent-stats {
  display: flex;
  gap: 20rpx;
}

.agent-credit, .agent-completion {
  font-size: 22rpx;
  color: #666;
}

.agent-match {
  text-align: center;
  flex-shrink: 0;
}

.match-percent {
  font-size: 32rpx;
  font-weight: bold;
  color: #10B981;
  display: block;
}

.match-label {
  font-size: 20rpx;
  color: #999;
}

.agent-assign-btn {
  background-color: #3B82F6;
  color: #fff;
  font-size: 24rpx;
  padding: 0 24rpx;
  height: 56rpx;
  line-height: 56rpx;
  border-radius: 28rpx;
  border: none;
  flex-shrink: 0;
}

.agent-assign-btn[disabled] {
  background-color: #E5E7EB;
  color: #9CA3AF;
}
</style>
