<template>
  <view class="my-container">
    <!-- Tab切换 -->
    <view class="tab-bar">
      <view
        v-for="tab in tabs"
        :key="tab.value"
        :class="['tab-item', { active: currentTab === tab.value }]"
        @click="switchTab(tab.value)"
      >
        {{ tab.label }}
      </view>
    </view>

    <!-- 需求列表 -->
    <scroll-view scroll-y class="list" @scrolltolower="loadMore">
      <view v-if="demands.length === 0 && !loading" class="empty">
        <text class="empty-text">暂无相关需求</text>
      </view>

      <view
        v-for="item in demands"
        :key="item.id"
        class="demand-card"
        @click="goDetail(item.id)"
      >
        <view class="card-header">
          <text class="card-title">{{ item.title }}</text>
          <text class="status-tag" :class="'status-' + item.status">{{ item.status_text || item.status }}</text>
        </view>
        <view class="card-info">
          <text class="info-tag">{{ item.category_text || item.category }}</text>
          <text class="card-budget">¥{{ item.budget }}</text>
        </view>
        <view class="card-time">发布于 {{ formatTime(item.created_at) }}</view>
      </view>

      <view v-if="loading" class="loading"><text>加载中...</text></view>
      <view v-if="noMore && demands.length > 0" class="no-more"><text>没有更多了</text></view>
    </scroll-view>
  </view>
</template>

<script>
import { demands } from '@/api/index.js'

const TABS = [
  { label: '全部', value: '' },
  { label: '进行中', value: 'open,matched' },
  { label: '已完成', value: 'completed' },
]

export default {
  data() {
    return {
      tabs: TABS,
      currentTab: '',
      demands: [],
      page: 1,
      pageSize: 10,
      loading: false,
      noMore: false,
    }
  },
  onLoad() {
    this.fetchMyDemands()
  },
  methods: {
    async fetchMyDemands() {
      if (this.loading) return
      this.loading = true
      try {
        uni.showLoading({ title: '加载中...' })
        const params = { page: this.page, page_size: this.pageSize }
        if (this.currentTab) params.status = this.currentTab
        const res = await demands.list(params)
        uni.hideLoading()
        const list = Array.isArray(res) ? res : (res.items || [])
        if (this.page === 1) {
          this.demands = list
        } else {
          this.demands = [...this.demands, ...list]
        }
        this.noMore = list.length < this.pageSize
      } catch (e) {
        uni.hideLoading()
        uni.showToast({ title: e.message || '加载失败', icon: 'none' })
      } finally {
        this.loading = false
      }
    },

    switchTab(val) {
      this.currentTab = val
      this.page = 1
      this.noMore = false
      this.demands = []
      this.fetchMyDemands()
    },

    loadMore() {
      if (this.noMore || this.loading) return
      this.page++
      this.fetchMyDemands()
    },

    goDetail(id) {
      uni.navigateTo({ url: `/pages/demand/detail?id=${id}` })
    },

    formatTime(ts) {
      if (!ts) return ''
      const d = new Date(ts)
      return `${d.getMonth() + 1}-${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
    },
  },
}
</script>

<style scoped>
.my-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f5f5f5;
}
.tab-bar {
  display: flex;
  background: #fff;
  border-bottom: 1px solid #eee;
}
.tab-item {
  flex: 1;
  text-align: center;
  padding: 28rpx 0;
  font-size: 28rpx;
  color: #666;
}
.tab-item.active {
  color: #007aff;
  font-weight: bold;
  border-bottom: 4rpx solid #007aff;
}
.list {
  flex: 1;
  padding: 20rpx;
}
.empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 400rpx;
}
.empty-text {
  color: #999;
  font-size: 28rpx;
}
.demand-card {
  background: #fff;
  border-radius: 12rpx;
  padding: 30rpx;
  margin-bottom: 20rpx;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16rpx;
}
.card-title {
  font-size: 32rpx;
  font-weight: bold;
  color: #333;
  flex: 1;
}
.status-tag {
  font-size: 22rpx;
  padding: 4rpx 16rpx;
  border-radius: 20rpx;
  flex-shrink: 0;
}
.status-open { background: #e6f7e6; color: #52c41a; }
.status-matched { background: #e6f0ff; color: #1890ff; }
.status-completed { background: #f0f0f0; color: #999; }
.card-info {
  display: flex;
  align-items: center;
  gap: 20rpx;
  margin-bottom: 12rpx;
}
.info-tag {
  font-size: 24rpx;
  background: #e6f0ff;
  color: #007aff;
  padding: 4rpx 16rpx;
  border-radius: 20rpx;
}
.card-budget {
  font-size: 28rpx;
  color: #ff6b00;
  font-weight: bold;
}
.card-time {
  font-size: 24rpx;
  color: #999;
}
.loading,
.no-more {
  text-align: center;
  padding: 30rpx;
  color: #999;
  font-size: 24rpx;
}
</style>