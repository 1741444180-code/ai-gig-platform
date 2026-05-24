<template>
  <view class="home">
    <!-- 搜索栏 -->
    <view class="search-bar">
      <view class="search-input-wrap">
        <text class="search-icon">🔍</text>
        <input
          class="search-input"
          placeholder="搜索需求关键词"
          v-model="searchQuery"
          confirm-type="search"
          @confirm="onSearch"
        />
        <text v-if="searchQuery" class="search-clear" @click="clearSearch">✕</text>
      </view>
      <view class="publish-btn" @click="goPublish">
        <text>+</text>
        <text class="publish-text">发布</text>
      </view>
    </view>

    <!-- 分类Tab -->
    <scroll-view class="category-tabs" scroll-x :show-scrollbar="false">
      <view
        v-for="cat in categories"
        :key="cat.value"
        :class="['tab-item', { active: activeCategory === cat.value }]"
        @click="switchCategory(cat.value)"
      >
        <text>{{ cat.label }}</text>
      </view>
    </scroll-view>

    <!-- 需求列表 -->
    <scroll-view
      class="demand-list"
      scroll-y
      :refresher-enabled="true"
      :refresher-triggered="isRefreshing"
      @refresherrefresh="onRefresh"
      @scrolltolower="loadMore"
    >
      <view v-if="demandList.length === 0 && !loading" class="empty-state">
        <text class="empty-icon">📋</text>
        <text class="empty-text">暂无需求</text>
        <text class="empty-hint">点击上方「发布」按钮发布你的第一个需求</text>
      </view>

      <view
        v-for="item in demandList"
        :key="item.id"
        class="demand-card"
        @click="goDetail(item.id)"
      >
        <view class="card-header">
          <text class="card-title">{{ item.title }}</text>
          <text class="card-budget">¥{{ item.budget }}</text>
        </view>
        <view class="card-meta">
          <text class="card-category">{{ item.category_name }}</text>
          <text class="card-time">{{ formatTime(item.created_at) }}</text>
        </view>
        <view class="card-desc">{{ item.description }}</view>
        <view class="card-footer">
          <text v-if="item.ai_tags && item.ai_tags.length > 0" class="card-tag">{{ item.ai_tags[0] }}</text>
          <text class="card-status" :class="'status-' + item.status">{{ statusText(item.status) }}</text>
        </view>
      </view>

      <view v-if="loading" class="loading-more">
        <text>加载中...</text>
      </view>
      <view v-if="noMore && demandList.length > 0" class="no-more">
        <text>— 已经到底了 —</text>
      </view>
    </scroll-view>
  </view>
</template>

<script>
import demandApi from '@/api/demand.js';

export default {
  data() {
    return {
      searchQuery: '',
      activeCategory: 'all',
      categories: [
        { label: '全部', value: 'all' },
        { label: '文案', value: 'copywriting' },
        { label: '设计', value: 'design' },
        { label: '开发', value: 'development' },
        { label: '运营', value: 'operation' },
        { label: '翻译', value: 'translation' },
        { label: '视频', value: 'video' },
        { label: '其他', value: 'other' }
      ],
      demandList: [],
      page: 1,
      pageSize: 10,
      loading: false,
      noMore: false,
      isRefreshing: false
    };
  },

  onLoad() {
    this.fetchList(true);
  },

  onPullDownRefresh() {
    this.isRefreshing = true;
    this.fetchList(true).finally(() => {
      this.isRefreshing = false;
      uni.stopPullDownRefresh();
    });
  },

  methods: {
    async fetchList(reset = false) {
      if (this.loading) return;
      if (reset) {
        this.page = 1;
        this.noMore = false;
        this.demandList = [];
      }
      this.loading = true;
      try {
        const params = {
          page: this.page,
          pageSize: this.pageSize
        };
        if (this.activeCategory !== 'all') {
          params.category = this.activeCategory;
        }
        if (this.searchQuery.trim()) {
          params.search = this.searchQuery.trim();
        }
        const res = await demandApi.getList(params);
        const list = res.data || res.list || [];
        if (reset) {
          this.demandList = list;
        } else {
          this.demandList = [...this.demandList, ...list];
        }
        this.noMore = list.length < this.pageSize;
        this.page += 1;
      } catch (e) {
        console.error('fetchList error:', e);
      } finally {
        this.loading = false;
      }
    },

    onSearch() {
      this.fetchList(true);
    },

    clearSearch() {
      this.searchQuery = '';
      this.fetchList(true);
    },

    switchCategory(val) {
      if (this.activeCategory === val) return;
      this.activeCategory = val;
      this.fetchList(true);
    },

    onRefresh() {
      this.isRefreshing = true;
      this.fetchList(true).finally(() => {
        this.isRefreshing = false;
      });
    },

    loadMore() {
      if (!this.noMore && !this.loading) {
        this.fetchList(false);
      }
    },

    goPublish() {
      uni.navigateTo({ url: '/pages/demand/publish' });
    },

    goDetail(id) {
      uni.navigateTo({ url: `/pages/demand/detail?id=${id}` });
    },

    formatTime(time) {
      if (!time) return '';
      const d = new Date(time);
      const now = new Date();
      const diff = now - d;
      if (diff < 60000) return '刚刚';
      if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
      if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
      if (diff < 604800000) return `${Math.floor(diff / 86400000)}天前`;
      return `${d.getMonth() + 1}-${d.getDate()}`;
    },

    statusText(status) {
      const map = { 0: '待接单', 1: '进行中', 2: '已完成', 3: '已取消' };
      return map[status] || '未知';
    }
  }
};
</script>

<style scoped>
.home {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background-color: #F5F7FA;
}

/* 搜索栏 */
.search-bar {
  display: flex;
  align-items: center;
  padding: 12rpx 24rpx;
  background-color: #fff;
  gap: 16rpx;
}

.search-input-wrap {
  flex: 1;
  display: flex;
  align-items: center;
  background-color: #F0F2F5;
  border-radius: 32rpx;
  padding: 16rpx 24rpx;
  gap: 12rpx;
}

.search-icon {
  font-size: 28rpx;
}

.search-input {
  flex: 1;
  font-size: 28rpx;
  color: #333;
}

.search-clear {
  font-size: 28rpx;
  color: #999;
  padding: 0 8rpx;
}

.publish-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #3B82F6;
  color: #fff;
  border-radius: 32rpx;
  padding: 16rpx 24rpx;
  font-size: 28rpx;
  gap: 4rpx;
}

.publish-text {
  font-size: 26rpx;
}

/* 分类Tab */
.category-tabs {
  background-color: #fff;
  padding: 0 24rpx;
  white-space: nowrap;
  border-bottom: 1rpx solid #eee;
}

.tab-item {
  display: inline-block;
  padding: 20rpx 28rpx;
  font-size: 28rpx;
  color: #666;
  position: relative;
}

.tab-item.active {
  color: #3B82F6;
  font-weight: bold;
}

.tab-item.active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 40rpx;
  height: 6rpx;
  background-color: #3B82F6;
  border-radius: 3rpx;
}

/* 需求列表 */
.demand-list {
  flex: 1;
  padding: 16rpx 24rpx;
  box-sizing: border-box;
}

.demand-card {
  background-color: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 16rpx;
  box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.04);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12rpx;
}

.card-title {
  flex: 1;
  font-size: 32rpx;
  font-weight: bold;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-right: 16rpx;
}

.card-budget {
  font-size: 32rpx;
  font-weight: bold;
  color: #EF4444;
  white-space: nowrap;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 16rpx;
  margin-bottom: 12rpx;
}

.card-category {
  font-size: 24rpx;
  color: #3B82F6;
  background-color: #EBF5FF;
  padding: 4rpx 16rpx;
  border-radius: 8rpx;
}

.card-time {
  font-size: 24rpx;
  color: #999;
}

.card-desc {
  font-size: 26rpx;
  color: #666;
  line-height: 1.5;
  margin-bottom: 12rpx;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.card-footer {
  display: flex;
  align-items: center;
  gap: 12rpx;
}

.card-tag {
  font-size: 22rpx;
  color: #8B5CF6;
  background-color: #F3F0FF;
  padding: 4rpx 12rpx;
  border-radius: 8rpx;
}

.card-status {
  font-size: 22rpx;
  padding: 4rpx 12rpx;
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

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 120rpx 0;
}

.empty-icon {
  font-size: 100rpx;
  margin-bottom: 24rpx;
}

.empty-text {
  font-size: 32rpx;
  color: #666;
  margin-bottom: 12rpx;
}

.empty-hint {
  font-size: 26rpx;
  color: #999;
}

.loading-more, .no-more {
  text-align: center;
  padding: 24rpx 0;
  font-size: 24rpx;
  color: #999;
}
</style>
