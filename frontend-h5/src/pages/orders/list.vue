<template>
  <view class="orders-page">
    <view class="orders-tabs">
      <view
        v-for="tab in tabs"
        :key="tab.key"
        class="tab-item"
        :class="{ active: currentTab === tab.key }"
        @click="switchTab(tab.key)"
      >{{ tab.label }}</view>
    </view>
    <view class="order-list">
      <view v-if="orderList.length === 0 && !loading" class="empty-orders">
        <text>暂无订单</text>
      </view>
      <view
        v-for="order in orderList"
        :key="order.id"
        class="order-card"
        @click="goDetail(order.id)"
      >
        <view class="order-header">
          <text class="order-title">{{ order.demand_title || '订单 #' + order.id }}</text>
          <text class="order-status" :class="'status-' + order.status">{{ statusText(order.status) }}</text>
        </view>
        <view class="order-info">
          <text class="budget">¥{{ order.budget }}</text>
          <text class="time">{{ formatTime(order.created_at) }}</text>
        </view>
        <view class="order-actions" v-if="order.status === 'delivered'">
          <button class="btn-accept" @click.stop="acceptDelivery(order.id)">验收通过</button>
          <button class="btn-reject" @click.stop="showReject(order.id)">拒绝</button>
        </view>
      </view>
    </view>
    <view v-if="hasMore && orderList.length > 0" class="load-more" @click="loadMore">
      <text>加载更多</text>
    </view>
  </view>
</template>

<script>
import { orders } from '@/api/index.js'

export default {
  data() {
    return {
      currentTab: 'all',
      tabs: [
        { key: 'all', label: '全部' },
        { key: 'pending', label: '待付款' },
        { key: 'paid', label: '已付款' },
        { key: 'in_progress', label: '进行中' },
        { key: 'delivered', label: '已交付' },
        { key: 'completed', label: '已完成' },
      ],
      orderList: [],
      page: 1,
      loading: false,
      hasMore: true,
    }
  },
  onLoad() {
    this.loadOrders()
  },
  onShow() {
    this.page = 1
    this.loadOrders()
  },
  methods: {
    async loadOrders() {
      if (this.loading) return
      this.loading = true
      const params = { page: this.page, page_size: 20 }
      if (this.currentTab !== 'all') params.status = this.currentTab
      try {
        const res = await orders.listMy(params)
        const items = Array.isArray(res) ? res : (res.items || res.data || [])
        if (this.page === 1) this.orderList = items
        else this.orderList = [...this.orderList, ...items]
        this.hasMore = items.length >= 20
      } catch (e) {
        uni.showToast({ title: '加载失败', icon: 'none' })
      } finally {
        this.loading = false
      }
    },
    switchTab(key) {
      this.currentTab = key
      this.page = 1
      this.hasMore = true
      this.loadOrders()
    },
    loadMore() {
      this.page++
      this.loadOrders()
    },
    goDetail(id) {
      uni.navigateTo({ url: '/pages/orders/detail?id=' + id })
    },
    async acceptDelivery(orderId) {
      try {
        await orders.acceptDelivery(orderId)
        uni.showToast({ title: '验收通过', icon: 'success' })
        this.page = 1
        this.loadOrders()
      } catch (e) {
        uni.showToast({ title: e.message || '验收失败', icon: 'none' })
      }
    },
    showReject(orderId) {
      uni.showModal({
        title: '拒绝验收',
        content: '请输入拒绝原因',
        editable: true,
        placeholderText: '原因...',
        success: async (m) => {
          if (m.confirm && m.content) {
            try {
              await orders.rejectDelivery(orderId, m.content)
              uni.showToast({ title: '已拒绝', icon: 'success' })
              this.page = 1
              this.loadOrders()
            } catch (e) {
              uni.showToast({ title: e.message || '操作失败', icon: 'none' })
            }
          }
        },
      })
    },
    statusText(status) {
      const map = {
        pending: '待付款',
        paid: '已付款',
        in_progress: '进行中',
        delivered: '已交付',
        completed: '已完成',
        cancelled: '已取消',
        accepted: '已验收',
      }
      return map[status] || status || '未知'
    },
    formatTime(ts) {
      if (!ts) return ''
      const d = new Date(ts)
      return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    },
  },
}
</script>

<style scoped>
.orders-page {
  min-height: 100vh;
  background: #f5f5f5;
}

.orders-tabs {
  display: flex;
  background: #fff;
  padding: 0 10rpx;
  overflow-x: auto;
}

.tab-item {
  flex-shrink: 0;
  padding: 24rpx 28rpx;
  font-size: 28rpx;
  color: #666;
  border-bottom: 4rpx solid transparent;
}

.tab-item.active {
  color: #007aff;
  font-weight: bold;
  border-bottom-color: #007aff;
}

.order-list {
  padding: 20rpx;
  display: flex;
  flex-direction: column;
  gap: 20rpx;
}

.empty-orders {
  text-align: center;
  padding: 120rpx;
  color: #999;
  font-size: 28rpx;
}

.order-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 30rpx;
}

.order-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16rpx;
}

.order-title {
  font-size: 30rpx;
  font-weight: bold;
  color: #333;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.order-status {
  font-size: 24rpx;
  padding: 4rpx 16rpx;
  border-radius: 20rpx;
  flex-shrink: 0;
}

.status-pending { background: #fffbe6; color: #faad14; }
.status-paid { background: #e6f4ff; color: #1890ff; }
.status-in_progress { background: #e6f4ff; color: #1890ff; }
.status-delivered { background: #f9f0ff; color: #722ed1; }
.status-completed { background: #e6f7e6; color: #52c41a; }
.status-cancelled { background: #fff1f0; color: #ff4d4f; }
.status-accepted { background: #e6f7e6; color: #52c41a; }

.order-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 16rpx;
}

.budget {
  font-size: 32rpx;
  color: #ff6b00;
  font-weight: bold;
}

.time {
  font-size: 24rpx;
  color: #999;
}

.order-actions {
  display: flex;
  gap: 20rpx;
  justify-content: flex-end;
}

.btn-accept {
  background: #52c41a;
  color: #fff;
  font-size: 26rpx;
  padding: 12rpx 30rpx;
  border-radius: 30rpx;
}

.btn-reject {
  background: #fff;
  color: #ff4d4f;
  border: 1px solid #ff4d4f;
  font-size: 26rpx;
  padding: 12rpx 30rpx;
  border-radius: 30rpx;
}

.load-more {
  text-align: center;
  padding: 30rpx;
  color: #007aff;
  font-size: 28rpx;
}
</style>