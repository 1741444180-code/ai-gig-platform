<template>
  <view class="index-container">
    <!-- 顶部分类Tab -->
    <view class="tab-bar">
      <view
        v-for="cat in categories"
        :key="cat.value"
        :class="['tab-item', { active: currentCategory === cat.value }]"
        @click="switchCategory(cat.value)"
      >
        {{ cat.label }}
      </view>
    </view>

    <!-- 需求列表 -->
    <scroll-view
      scroll-y
      class="demand-list"
      @scrolltolower="loadMore"
    >
      <view v-if="demands.length === 0 && !loading" class="empty">
        <text class="empty-text">暂无需求，去发布一个吧</text>
        <button class="publish-btn" @click="goPublish">发布需求</button>
      </view>

      <view
        v-for="item in demands"
        :key="item.id"
        class="demand-card"
        @click="goDetail(item.id)"
      >
        <view class="card-header">
          <text class="card-title">{{ item.title }}</text>
          <text class="card-category">{{ item.category_text || item.category }}</text>
        </view>
        <view class="card-desc">{{ item.description }}</view>
        <view class="card-footer">
          <text class="card-budget">预算: ¥{{ item.budget }}</text>
          <text class="card-time">{{ formatTime(item.created_at) }}</text>
        </view>
      </view>

      <view v-if="loading" class="loading">
        <text>加载中...</text>
      </view>

      <view v-if="noMore && demands.length > 0" class="no-more">
        <text>没有更多了</text>
      </view>
    </scroll-view>

    <!-- 底部发布按钮 -->
    <view class="bottom-bar">
      <button class="fab" @click="goPublish">+ 发布需求</button>
    </view>
  </view>
</template>

<script>
import { demands } from '@/api/index.js'

const CATEGORIES = [
  { label: '全部', value: '' },
  { label: '文案', value: 'copywriting' },
  { label: '图片', value: 'image' },
  { label: '视频', value: 'video' },
  { label: '开发', value: 'development' },
  { label: '其他', value: 'other' },
]

export default {
  data() {
    return {
      categories: CATEGORIES,
      currentCategory: '',
      demands: [],
      page: 1,
      pageSize: 10,
      loading: false,
      noMore: false,
    }
  },
  onLoad() {
    this.fetchDemands()
  },
  onShow() {
    // 返回时刷新
    this.fetchDemands()
  },
  methods: {
    async fetchDemands() {
      if (this.loading) return
      this.loading = true
      try {
        uni.showLoading({ title: '加载中...' })
        const params = { page: this.page, page_size: this.pageSize }
        if (this.currentCategory) params.category = this.currentCategory
        const res = await demands.list(params)
        uni.hideLoading()
        // 兼容分页结构
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

    switchCategory(cat) {
      this.currentCategory = cat
      this.page = 1
      this.noMore = false
      this.demands = []
      this.fetchDemands()
    },

    loadMore() {
      if (this.noMore || this.loading) return
      this.page++
      this.fetchDemands()
    },

    goDetail(id) {
      uni.navigateTo({ url: `/pages/demand/detail?id=${id}` })
    },

    goPublish() {
      uni.navigateTo({ url: '/pages/demand/publish' })
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
.index-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f5f5f5;
}
.tab-bar {
  display: flex;
  background: #fff;
  padding: 0 20rpx;
  border-bottom: 1px solid #eee;
  overflow-x: auto;
  flex-shrink: 0;
}
.tab-item {
  flex-shrink: 0;
  padding: 24rpx 30rpx;
  font-size: 28rpx;
  color: #666;
  position: relative;
}
.tab-item.active {
  color: #007aff;
  font-weight: bold;
}
.tab-item.active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 40rpx;
  height: 4rpx;
  background: #007aff;
  border-radius: 2rpx;
}
.demand-list {
  flex: 1;
  padding: 20rpx;
}
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 200rpx;
}
.empty-text {
  color: #999;
  font-size: 28rpx;
  margin-bottom: 40rpx;
}
.publish-btn {
  background: #007aff;
  color: #fff;
  font-size: 28rpx;
  padding: 20rpx 60rpx;
  border-radius: 40rpx;
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
.card-category {
  font-size: 22rpx;
  background: #e6f0ff;
  color: #007aff;
  padding: 4rpx 16rpx;
  border-radius: 20rpx;
  flex-shrink: 0;
}
.card-desc {
  font-size: 26rpx;
  color: #666;
  line-height: 1.6;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  margin-bottom: 20rpx;
}
.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
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
.bottom-bar {
  padding: 20rpx 40rpx;
  background: #fff;
  border-top: 1px solid #eee;
}
.fab {
  width: 100%;
  height: 96rpx;
  line-height: 96rpx;
  background: linear-gradient(135deg, #007aff, #0056cc);
  color: #fff;
  font-size: 32rpx;
  font-weight: bold;
  border-radius: 48rpx;
  border: none;
}
</style>