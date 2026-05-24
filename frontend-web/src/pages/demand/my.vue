<template>
  <view class="my-page">
    <!-- Tab切换 -->
    <view class="tabs-wrap">
      <view
        v-for="tab in tabs"
        :key="tab.value"
        :class="['tab-btn', { active: activeTab === tab.value }]"
        @click="switchTab(tab.value)"
      >
        <text>{{ tab.label }}</text>
      </view>
    </view>

    <!-- 需求列表 -->
    <scroll-view
      class="demand-scroll"
      scroll-y
      :refresher-enabled="true"
      :refresher-triggered="isRefreshing"
      @refresherrefresh="onRefresh"
      @scrolltolower="loadMore"
    >
      <view v-if="list.length === 0 && !loading" class="empty-state">
        <text class="empty-icon">{{ emptyIcons[activeTab] }}</text>
        <text class="empty-text">{{ emptyTexts[activeTab] }}</text>
      </view>

      <view
        v-for="item in list"
        :key="item.id"
        class="demand-card"
        @click="goDetail(item.id)"
      >
        <view class="card-top">
          <text class="card-title">{{ item.title }}</text>
          <text class="status-tag" :class="'status-' + item.status">
            {{ statusText(item.status) }}
          </text>
        </view>
        <view class="card-info">
          <text class="info-item">¥{{ item.budget }}</text>
          <text class="info-sep">·</text>
          <text class="info-item">{{ item.category_name }}</text>
          <text class="info-sep">·</text>
          <text class="info-item">{{ item.deadline }}</text>
        </view>
        <view class="card-desc">{{ item.description }}</view>
        <text class="card-time">{{ formatTime(item.created_at) }}</text>
      </view>

      <view v-if="loading" class="loading-text">
        <text>加载中...</text>
      </view>
      <view v-if="noMore && list.length > 0" class="no-more-text">
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
      tabs: [
        { label: '发布中', value: 0 },
        { label: '进行中', value: 1 },
        { label: '已完成', value: 2 }
      ],
      activeTab: 0,
      list: [],
      page: 1,
      pageSize: 10,
      loading: false,
      noMore: false,
      isRefreshing: false,
      statusTexts: { 0: '待接单', 1: '进行中', 2: '已完成', 3: '已取消' },
      emptyIcons: { 0: '📝', 1: '⏳', 2: '🎉' },
      emptyTexts: {
        0: '暂无发布中的需求',
        1: '暂无进行中的需求',
        2: '暂无已完成的需求'
      }
    };
  },

  onLoad() {
    this.fetchList(true);
  },

  methods: {
    async fetchList(reset = false) {
      if (this.loading) return;
      if (reset) {
        this.page = 1;
        this.noMore = false;
        this.list = [];
      }
      this.loading = true;
      try {
        const res = await demandApi.getMyDemands({
          status: this.activeTab,
          page: this.page,
          pageSize: this.pageSize
        });
        const data = res.data || res.list || [];
        if (reset) {
          this.list = data;
        } else {
          this.list = [...this.list, ...data];
        }
        this.noMore = data.length < this.pageSize;
        this.page += 1;
      } catch (e) {
        console.error('fetchMyDemands error:', e);
      } finally {
        this.loading = false;
      }
    },

    switchTab(val) {
      if (this.activeTab === val) return;
      this.activeTab = val;
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

    goDetail(id) {
      uni.navigateTo({ url: `/pages/demand/detail?id=${id}` });
    },

    statusText(status) {
      return this.statusTexts[status] || '未知';
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
      return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    }
  }
};
</script>

<style scoped>
.my-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background-color: #F5F7FA;
}

.tabs-wrap {
  display: flex;
  background-color: #fff;
  padding: 16rpx 24rpx;
  gap: 16rpx;
}

.tab-btn {
  flex: 1;
  text-align: center;
  padding: 16rpx 0;
  border-radius: 32rpx;
  font-size: 28rpx;
  color: #666;
  background-color: #F0F2F5;
}

.tab-btn.active {
  color: #3B82F6;
  background-color: #EBF5FF;
  font-weight: bold;
}

.demand-scroll {
  flex: 1;
  padding: 16rpx 24rpx;
  box-sizing: border-box;
}

.demand-card {
  background-color: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 16rpx;
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12rpx;
}

.card-title {
  flex: 1;
  font-size: 30rpx;
  font-weight: bold;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-right: 16rpx;
}

.status-tag {
  font-size: 22rpx;
  padding: 4rpx 16rpx;
  border-radius: 8rpx;
  flex-shrink: 0;
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

.card-info {
  display: flex;
  align-items: center;
  gap: 8rpx;
  margin-bottom: 12rpx;
  font-size: 24rpx;
  color: #999;
}

.info-item {
  color: #666;
}

.info-sep {
  color: #ddd;
}

.card-desc {
  font-size: 26rpx;
  color: #666;
  line-height: 1.5;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  margin-bottom: 12rpx;
}

.card-time {
  font-size: 22rpx;
  color: #999;
  text-align: right;
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 120rpx 0;
}

.empty-icon {
  font-size: 80rpx;
  margin-bottom: 24rpx;
}

.empty-text {
  font-size: 28rpx;
  color: #999;
}

.loading-text, .no-more-text {
  text-align: center;
  padding: 24rpx 0;
  font-size: 24rpx;
  color: #999;
}
</style>
