<template>
  <view class="agent-dashboard">
    <!-- 未创建Agent引导页 -->
    <view v-if="!myAgent && !loading" class="empty-agent">
      <view class="empty-icon">🤖</view>
      <view class="empty-title">还没有创建Agent</view>
      <view class="empty-desc">成为AI服务的提供者，开启接单赚钱之旅</view>
      <button class="btn-create" @click="goRegister">创建我的Agent</button>
    </view>

    <!-- Agent工作台 -->
    <view v-else class="dashboard-content">
      <!-- Agent卡片 -->
      <view class="agent-card" @click="goEditProfile">
        <view class="agent-header">
          <view class="agent-name">{{ myAgent.name }}</view>
          <view class="agent-status" :class="'status-' + myAgent.status">{{ statusText }}</view>
        </view>
        <view class="agent-desc">{{ myAgent.description || '暂无描述' }}</view>
        <view class="agent-footer">
          <view class="credit-score">
            <text class="label">信用分</text>
            <text class="value">{{ myAgent.credit_score ?? 'N/A' }}</text>
          </view>
          <view class="api-key-hint" v-if="apiKeyMasked">API Key: {{ apiKeyMasked }}</view>
        </view>
        <view class="edit-hint">点击编辑能力卡 &gt;</view>
      </view>

      <!-- 收益统计卡片 -->
      <view class="income-cards">
        <view class="income-item">
          <view class="income-value">¥{{ incomeData.total_income || 0 }}</view>
          <view class="income-label">总收益</view>
        </view>
        <view class="income-item">
          <view class="income-value">¥{{ incomeData.pending_settlement || 0 }}</view>
          <view class="income-label">待结算</view>
        </view>
        <view class="income-item">
          <view class="income-value">¥{{ incomeData.withdrawn || 0 }}</view>
          <view class="income-label">已提现</view>
        </view>
      </view>

      <!-- 订单Tab切换 -->
      <view class="order-tabs">
        <view
          v-for="tab in orderTabs"
          :key="tab.key"
          class="tab-item"
          :class="{ active: currentTab === tab.key }"
          @click="switchTab(tab.key)"
        >{{ tab.label }}</view>
      </view>

      <!-- 订单列表 -->
      <view class="order-list">
        <view v-if="orderList.length === 0" class="empty-orders">
          <text>暂无订单</text>
        </view>
        <view
          v-for="order in orderList"
          :key="order.id"
          class="order-card"
          @click="goOrderDetail(order.id)"
        >
          <view class="order-header">
            <text class="order-title">{{ order.demand_title || '订单 #' + order.id }}</text>
            <text class="order-status" :class="'order-status-' + order.status">{{ orderStatusText(order.status) }}</text>
          </view>
          <view class="order-info">
            <text class="order-budget">¥{{ order.budget }}</text>
            <text class="order-time">{{ formatTime(order.created_at) }}</text>
          </view>
          <view class="order-actions" v-if="currentTab === 'pending'">
            <button class="btn-small btn-accept" @click.stop="acceptOrder(order.id)">接单</button>
            <button class="btn-small btn-cancel" @click.stop="cancelOrder(order.id)">取消</button>
          </view>
          <view class="order-actions" v-if="currentTab === 'in_progress'">
            <button class="btn-small btn-deliver" @click.stop="deliverOrder(order.id)">交付</button>
          </view>
        </view>
      </view>

      <!-- 加载更多 -->
      <view v-if="orderList.length > 0 && hasMore" class="load-more" @click="loadMoreOrders">
        <text>加载更多</text>
      </view>
    </view>

    <!-- 加载状态 -->
    <view v-if="loading" class="loading-mask">
      <text>加载中...</text>
    </view>
  </view>
</template>

<script>
import { agents, wallet } from '@/api/index.js'

export default {
  data() {
    return {
      loading: true,
      myAgent: null,
      apiKeyMasked: '',
      incomeData: {
        total_income: 0,
        pending_settlement: 0,
        withdrawn: 0,
      },
      currentTab: 'pending',
      orderTabs: [
        { key: 'pending', label: '待接单' },
        { key: 'in_progress', label: '进行中' },
        { key: 'completed', label: '已完成' },
      ],
      orderList: [],
      orderPage: 1,
      orderPageSize: 10,
      hasMore: true,
    }
  },
  computed: {
    statusText() {
      const map = { active: '工作中', idle: '空闲', suspended: '已暂停' }
      return map[this.myAgent?.status] || this.myAgent?.status || '未知'
    },
  },
  onLoad() {
    this.loadData()
  },
  onShow() {
    // 每次显示时刷新数据
    this.loadData()
  },
  methods: {
    async loadData() {
      this.loading = true
      try {
        await Promise.all([
          this.loadMyAgent(),
          this.loadIncome(),
        ])
        await this.loadOrders()
      } catch (e) {
        console.error('loadData error:', e)
        uni.showToast({ title: '加载失败', icon: 'none' })
      } finally {
        this.loading = false
      }
    },
    async loadMyAgent() {
      try {
        const res = await agents.getMyAgents()
        // res可能是数组或单个对象
        if (Array.isArray(res)) {
          this.myAgent = res[0] || null
        } else {
          this.myAgent = res
        }
        // 尝试获取API Key列表（脱敏）
        try {
          const keys = await agents.listKeys()
          if (keys && keys.length > 0) {
            const k = keys[0]
            this.apiKeyMasked = k.key_prefix + '****' + (k.key_suffix || '')
          }
        } catch (e) {}
      } catch (e) {
        this.myAgent = null
      }
    },
    async loadIncome() {
      try {
        const res = await wallet.getIncome()
        this.incomeData = res
      } catch (e) {
        // 忽略
      }
    },
    async loadOrders() {
      if (!this.myAgent) {
        this.orderList = []
        return
      }
      // 获取API Key来调用agent端API
      let apiKey = ''
      try {
        const keys = await agents.listKeys()
        if (keys && keys.length > 0) apiKey = keys[0].api_key || ''
      } catch (e) {}

      try {
        const res = await agents.getOrders({
          status: this.currentTab,
          page: this.orderPage,
          page_size: this.orderPageSize,
        }, apiKey)
        const orders = Array.isArray(res) ? res : (res.items || res.data || [])
        if (this.orderPage === 1) {
          this.orderList = orders
        } else {
          this.orderList = [...this.orderList, ...orders]
        }
        this.hasMore = orders.length >= this.orderPageSize
      } catch (e) {
        console.error('loadOrders error:', e)
      }
    },
    switchTab(key) {
      this.currentTab = key
      this.orderPage = 1
      this.hasMore = true
      this.loadOrders()
    },
    loadMoreOrders() {
      this.orderPage++
      this.loadOrders()
    },
    goRegister() {
      uni.navigateTo({ url: '/pages/agent/register' })
    },
    goEditProfile() {
      uni.navigateTo({ url: '/pages/agent/profile' })
    },
    goOrderDetail(orderId) {
      uni.navigateTo({ url: '/pages/agent/order-detail?id=' + orderId })
    },
    async acceptOrder(orderId) {
      // 接单需要先获取API Key
      let apiKey = ''
      try {
        const keys = await agents.listKeys()
        if (keys && keys.length > 0) apiKey = keys[0].api_key || ''
      } catch (e) {}
      try {
        await agents.acceptOrder(orderId, {}, apiKey)
        uni.showToast({ title: '接单成功' })
        this.loadOrders()
      } catch (e) {
        uni.showToast({ title: e.message || '接单失败', icon: 'none' })
      }
    },
    async cancelOrder(orderId) {
      let apiKey = ''
      try {
        const keys = await agents.listKeys()
        if (keys && keys.length > 0) apiKey = keys[0].api_key || ''
      } catch (e) {}
      try {
        await agents.cancelOrder(orderId, apiKey)
        uni.showToast({ title: '已取消接单' })
        this.loadOrders()
      } catch (e) {
        uni.showToast({ title: e.message || '取消失败', icon: 'none' })
      }
    },
    async deliverOrder(orderId) {
      let apiKey = ''
      try {
        const keys = await agents.listKeys()
        if (keys && keys.length > 0) apiKey = keys[0].api_key || ''
      } catch (e) {}
      uni.navigateTo({ url: '/pages/agent/deliver?id=' + orderId + '&apiKey=' + encodeURIComponent(apiKey) })
    },
    orderStatusText(status) {
      const map = {
        pending: '待接单',
        in_progress: '进行中',
        completed: '已完成',
        cancelled: '已取消',
        delivered: '已交付',
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
.agent-dashboard {
  min-height: 100vh;
  background: #f5f5f5;
  padding: 20rpx;
}

.empty-agent {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 200rpx;
}

.empty-icon {
  font-size: 120rpx;
  margin-bottom: 30rpx;
}

.empty-title {
  font-size: 36rpx;
  font-weight: bold;
  color: #333;
  margin-bottom: 16rpx;
}

.empty-desc {
  font-size: 28rpx;
  color: #999;
  margin-bottom: 60rpx;
}

.btn-create {
  background: #007aff;
  color: #fff;
  border-radius: 40rpx;
  padding: 0 60rpx;
  height: 80rpx;
  line-height: 80rpx;
  font-size: 32rpx;
}

.dashboard-content {
  display: flex;
  flex-direction: column;
  gap: 20rpx;
}

.agent-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 30rpx;
  position: relative;
}

.agent-header {
  display: flex;
  align-items: center;
  gap: 20rpx;
  margin-bottom: 16rpx;
}

.agent-name {
  font-size: 36rpx;
  font-weight: bold;
  color: #333;
}

.agent-status {
  font-size: 24rpx;
  padding: 4rpx 16rpx;
  border-radius: 20rpx;
}

.status-active { background: #e6f7e6; color: #52c41a; }
.status-idle { background: #fffbe6; color: #faad14; }
.status-suspended { background: #fff1f0; color: #ff4d4f; }

.agent-desc {
  font-size: 28rpx;
  color: #666;
  margin-bottom: 20rpx;
}

.agent-footer {
  display: flex;
  align-items: center;
  gap: 30rpx;
  margin-bottom: 10rpx;
}

.credit-score {
  display: flex;
  align-items: center;
  gap: 8rpx;
}

.credit-score .label {
  font-size: 24rpx;
  color: #999;
}

.credit-score .value {
  font-size: 28rpx;
  color: #007aff;
  font-weight: bold;
}

.api-key-hint {
  font-size: 24rpx;
  color: #999;
}

.edit-hint {
  font-size: 24rpx;
  color: #007aff;
  text-align: right;
}

.income-cards {
  display: flex;
  gap: 20rpx;
}

@media screen and (max-width: 375px) {
  .income-cards {
    gap: 10rpx;
  }
  .income-value {
    font-size: 32rpx;
  }
}

.income-item {
  flex: 1;
  background: #fff;
  border-radius: 16rpx;
  padding: 30rpx 20rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.income-value {
  font-size: 40rpx;
  font-weight: bold;
  color: #333;
  margin-bottom: 10rpx;
}

.income-label {
  font-size: 24rpx;
  color: #999;
}

.order-tabs {
  display: flex;
  background: #fff;
  border-radius: 16rpx;
  padding: 0 10rpx;
}

@media screen and (min-width: 768px) {
  .order-tabs {
    max-width: 600px;
    margin: 0 auto;
  }
}

.tab-item {
  flex: 1;
  text-align: center;
  padding: 24rpx 0;
  font-size: 28rpx;
  color: #666;
}

.tab-item.active {
  color: #007aff;
  font-weight: bold;
  border-bottom: 4rpx solid #007aff;
}

.order-list {
  display: flex;
  flex-direction: column;
  gap: 20rpx;
}

.empty-orders {
  text-align: center;
  padding: 60rpx;
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
}

.order-status {
  font-size: 24rpx;
  padding: 4rpx 16rpx;
  border-radius: 20rpx;
}

.order-status-pending { background: #fffbe6; color: #faad14; }
.order-status-in_progress { background: #e6f4ff; color: #1890ff; }
.order-status-completed { background: #e6f7e6; color: #52c41a; }
.order-status-delivered { background: #f9f0ff; color: #722ed1; }
.order-status-accepted { background: #e6f7e6; color: #52c41a; }
.order-status-cancelled { background: #fff1f0; color: #ff4d4f; }

.order-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 16rpx;
}

.order-budget {
  font-size: 32rpx;
  color: #ff6b00;
  font-weight: bold;
}

.order-time {
  font-size: 24rpx;
  color: #999;
}

.order-actions {
  display: flex;
  gap: 20rpx;
  justify-content: flex-end;
}

.btn-small {
  font-size: 24rpx;
  padding: 10rpx 24rpx;
  border-radius: 30rpx;
  line-height: 1.5;
}

.btn-accept { background: #007aff; color: #fff; }
.btn-cancel { background: #fff; color: #999; border: 1px solid #ddd; }
.btn-deliver { background: #52c41a; color: #fff; }

.load-more {
  text-align: center;
  padding: 30rpx;
  color: #007aff;
  font-size: 28rpx;
}

.loading-mask {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(255,255,255,0.8);
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>