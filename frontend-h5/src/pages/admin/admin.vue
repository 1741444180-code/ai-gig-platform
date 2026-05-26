<template>
  <view class="admin-page">
    <!-- 权限校验 -->
    <view v-if="!isAdmin" class="no-permission">
      <view class="no-perm-icon">🔒</view>
      <view class="no-perm-title">无权访问</view>
      <view class="no-perm-desc">此页面仅限管理员访问</view>
    </view>

    <view v-else class="admin-content">
      <!-- Tab切换 -->
      <scroll-view scroll-x class="admin-tabs">
        <view
          v-for="tab in adminTabs"
          :key="tab.key"
          class="admin-tab"
          :class="{ active: currentTab === tab.key }"
          @click="switchTab(tab.key)"
        >{{ tab.label }}</view>
      </scroll-view>

      <!-- 数据看板 -->
      <view v-show="currentTab === 'dashboard'" class="tab-panel">
        <view class="stat-cards">
          <view class="stat-card">
            <view class="stat-value">{{ dashData.total_users || 0 }}</view>
            <view class="stat-label">用户数</view>
          </view>
          <view class="stat-card">
            <view class="stat-value">{{ dashData.total_agents || 0 }}</view>
            <view class="stat-label">Agent数</view>
          </view>
          <view class="stat-card">
            <view class="stat-value">{{ dashData.total_orders || 0 }}</view>
            <view class="stat-label">订单数</view>
          </view>
          <view class="stat-card">
            <view class="stat-value">{{ dashData.completion_rate || '0%' }}</view>
            <view class="stat-label">完成率</view>
          </view>
          <view class="stat-card">
            <view class="stat-value">¥{{ dashData.avg_order_price || 0 }}</view>
            <view class="stat-label">均价(元)</view>
          </view>
        </view>
        <view class="refresh-bar">
          <button class="btn-refresh" @click="loadDashboard">刷新看板</button>
        </view>
      </view>

      <!-- 用户管理 -->
      <view v-show="currentTab === 'users'" class="tab-panel">
        <view v-if="userList.length === 0 && !loadingUsers" class="empty-table">
          <text>暂无用户数据</text>
        </view>
        <view v-else class="table-list">
          <view class="table-header">
            <text class="th" style="flex:1">用户ID</text>
            <text class="th" style="flex:1">手机号</text>
            <text class="th" style="flex:1">角色</text>
            <text class="th" style="flex:1">状态</text>
            <text class="th" style="flex:1.5">操作</text>
          </view>
          <view v-for="u in userList" :key="u.id" class="table-row">
            <text class="td" style="flex:1">{{ u.id }}</text>
            <text class="td" style="flex:1">{{ u.phone || 'N/A' }}</text>
            <text class="td" style="flex:1">{{ u.role || 'user' }}</text>
            <text class="td" style="flex:1">
              <text :class="'status-tag status-' + (u.status || 'active')">{{ u.status === 'banned' ? '已封禁' : '正常' }}</text>
            </text>
            <view class="td" style="flex:1.5">
              <button v-if="u.status !== 'banned'" class="btn-tiny btn-ban" @click="banUser(u.id)">封禁</button>
              <button v-else class="btn-tiny btn-unban" @click="unbanUser(u.id)">解封</button>
            </view>
          </view>
        </view>
        <view v-if="hasMoreUsers" class="load-more" @click="loadMoreUsers">
          <text>加载更多</text>
        </view>
      </view>

      <!-- 订单管理 -->
      <view v-show="currentTab === 'orders'" class="tab-panel">
        <view v-if="orderList.length === 0 && !loadingOrders" class="empty-table">
          <text>暂无订单数据</text>
        </view>
        <view v-else class="table-list">
          <view class="table-header">
            <text class="th" style="flex:0.5">ID</text>
            <text class="th" style="flex:1">需求</text>
            <text class="th" style="flex:0.7">金额</text>
            <text class="th" style="flex:0.8">状态</text>
            <text class="th" style="flex:1.5">操作</text>
          </view>
          <view v-for="o in orderList" :key="o.id" class="table-row">
            <text class="td" style="flex:0.5">{{ o.id }}</text>
            <text class="td" style="flex:1" class="td-text-overflow">{{ o.demand_title || '-' }}</text>
            <text class="td" style="flex:0.7">¥{{ o.budget }}</text>
            <text class="td" style="flex:0.8">{{ o.status }}</text>
            <view class="td" style="flex:1.5">
              <button v-if="o.status !== 'completed' && o.status !== 'cancelled'" class="btn-tiny btn-force" @click="forceComplete(o.id)">强制完成</button>
              <button class="btn-tiny btn-cancel-order" @click="forceCancel(o.id)">强制取消</button>
            </view>
          </view>
        </view>
        <view v-if="hasMoreOrders" class="load-more" @click="loadMoreOrders">
          <text>加载更多</text>
        </view>
      </view>

      <!-- Agent管理 -->
      <view v-show="currentTab === 'agents'" class="tab-panel">
        <view v-if="agentList.length === 0 && !loadingAgents" class="empty-table">
          <text>暂无Agent数据</text>
        </view>
        <view v-else class="table-list">
          <view class="table-header">
            <text class="th" style="flex:0.5">ID</text>
            <text class="th" style="flex:1">名称</text>
            <text class="th" style="flex:0.8">状态</text>
            <text class="th" style="flex:0.8">信用分</text>
            <text class="th" style="flex:0.8">报价</text>
          </view>
          <view v-for="a in agentList" :key="a.id" class="table-row">
            <text class="td" style="flex:0.5">{{ a.id }}</text>
            <text class="td" style="flex:1" class="td-text-overflow">{{ a.name }}</text>
            <text class="td" style="flex:0.8">{{ a.status }}</text>
            <text class="td" style="flex:0.8">{{ a.credit_score ?? 'N/A' }}</text>
            <text class="td" style="flex:0.8">¥{{ a.base_price }}</text>
          </view>
        </view>
        <view v-if="hasMoreAgents" class="load-more" @click="loadMoreAgents">
          <text>加载更多</text>
        </view>
      </view>

      <!-- 支付确认 -->
      <view v-show="currentTab === 'payments'" class="tab-panel">
        <view v-if="paymentList.length === 0 && !loadingPayments" class="empty-table">
          <text>暂无待确认的支付</text>
        </view>
        <view v-else class="table-list">
          <view v-for="p in paymentList" :key="p.id" class="payment-card">
            <view class="payment-header">
              <text class="payment-title">订单 #{{ p.order_id }}</text>
              <text class="payment-amount">¥{{ p.amount }}</text>
            </view>
            <view v-if="p.screenshot_url" class="payment-screenshot">
              <image :src="p.screenshot_url" mode="widthFix" @click="previewImage(p.screenshot_url)" />
            </view>
            <view class="payment-actions">
              <button class="btn-tiny btn-confirm" @click="confirmPayment(p.id)">确认</button>
              <button class="btn-tiny btn-reject" @click="rejectPayment(p.id)">拒绝</button>
            </view>
          </view>
        </view>
        <view v-if="hasMorePayments" class="load-more" @click="loadMorePayments">
          <text>加载更多</text>
        </view>
      </view>

      <!-- 仲裁管理 -->
      <view v-show="currentTab === 'arbitration'" class="tab-panel">
        <view v-if="disputeList.length === 0 && !loadingDisputes" class="empty-table">
          <text>暂无争议订单</text>
        </view>
        <view v-else class="table-list">
          <view v-for="d in disputeList" :key="d.id" class="dispute-card">
            <view class="dispute-header">
              <text class="dispute-title">订单 #{{ d.order_id }}</text>
              <text class="dispute-status">{{ d.status }}</text>
            </view>
            <view class="dispute-desc">{{ d.description || '用户对此订单有争议' }}</view>
            <view class="dispute-actions">
              <button class="btn-tiny btn-confirm" @click="resolveDispute(d.id, 'refund')">退款给用户</button>
              <button class="btn-tiny btn-deliver" @click="resolveDispute(d.id, 'release')">放款给Agent</button>
            </view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { admin } from '@/api/index.js'

export default {
  data() {
    return {
      currentTab: 'dashboard',
      adminTabs: [
        { key: 'dashboard', label: '数据看板' },
        { key: 'users', label: '用户管理' },
        { key: 'orders', label: '订单管理' },
        { key: 'agents', label: 'Agent管理' },
        { key: 'payments', label: '支付确认' },
        { key: 'arbitration', label: '仲裁管理' },
      ],
      isAdmin: false,
      // Dashboard
      dashData: {},
      // Users
      userList: [],
      userPage: 1,
      loadingUsers: false,
      hasMoreUsers: true,
      // Orders
      orderList: [],
      orderPage: 1,
      loadingOrders: false,
      hasMoreOrders: true,
      // Agents
      agentList: [],
      agentPage: 1,
      loadingAgents: false,
      hasMoreAgents: true,
      // Payments
      paymentList: [],
      paymentPage: 1,
      loadingPayments: false,
      hasMorePayments: true,
      // Disputes
      disputeList: [],
      loadingDisputes: false,
    }
  },
  onLoad() {
    this.checkAdmin()
  },
  methods: {
    checkAdmin() {
      const userInfo = uni.getStorageSync('user_info')
      if (userInfo && userInfo.role === 'admin') {
        this.isAdmin = true
        this.loadDashboard()
      } else {
        this.isAdmin = false
      }
    },
    switchTab(key) {
      this.currentTab = key
      if (key === 'users' && this.userList.length === 0) this.loadUsers()
      else if (key === 'orders' && this.orderList.length === 0) this.loadOrders()
      else if (key === 'agents' && this.agentList.length === 0) this.loadAgents()
      else if (key === 'payments' && this.paymentList.length === 0) this.loadPayments()
      else if (key === 'arbitration' && this.disputeList.length === 0) this.loadDisputes()
    },
    async loadDashboard() {
      try {
        this.dashData = await admin.getDashboard()
      } catch (e) {
        uni.showToast({ title: '加载看板失败', icon: 'none' })
      }
    },
    async loadUsers() {
      if (this.loadingUsers) return
      this.loadingUsers = true
      try {
        const res = await admin.getUsers({ page: this.userPage, page_size: 20 })
        const items = Array.isArray(res) ? res : (res.items || res.data || [])
        if (this.userPage === 1) this.userList = items
        else this.userList = [...this.userList, ...items]
        this.hasMoreUsers = items.length >= 20
      } catch (e) {
        uni.showToast({ title: '加载用户失败', icon: 'none' })
      } finally {
        this.loadingUsers = false
      }
    },
    loadMoreUsers() {
      this.userPage++
      this.loadUsers()
    },
    async banUser(userId) {
      try {
        await admin.banUser(userId)
        uni.showToast({ title: '已封禁' })
        this.userPage = 1
        this.loadUsers()
      } catch (e) {
        uni.showToast({ title: e.message || '操作失败', icon: 'none' })
      }
    },
    async unbanUser(userId) {
      try {
        await admin.unbanUser(userId)
        uni.showToast({ title: '已解封' })
        this.userPage = 1
        this.loadUsers()
      } catch (e) {
        uni.showToast({ title: e.message || '操作失败', icon: 'none' })
      }
    },
    async loadOrders() {
      if (this.loadingOrders) return
      this.loadingOrders = true
      try {
        const res = await admin.getOrders({ page: this.orderPage, page_size: 20 })
        const items = Array.isArray(res) ? res : (res.items || res.data || [])
        if (this.orderPage === 1) this.orderList = items
        else this.orderList = [...this.orderList, ...items]
        this.hasMoreOrders = items.length >= 20
      } catch (e) {
        uni.showToast({ title: '加载订单失败', icon: 'none' })
      } finally {
        this.loadingOrders = false
      }
    },
    loadMoreOrders() {
      this.orderPage++
      this.loadOrders()
    },
    async forceComplete(orderId) {
      uni.showModal({
        title: '确认',
        content: '确定要强制完成此订单吗？',
        success: async (m) => {
          if (m.confirm) {
            try {
              await admin.releaseOrder(orderId)
              uni.showToast({ title: '已强制完成' })
              this.orderPage = 1
              this.loadOrders()
            } catch (e) {
              uni.showToast({ title: e.message || '操作失败', icon: 'none' })
            }
          }
        },
      })
    },
    async forceCancel(orderId) {
      uni.showModal({
        title: '确认',
        content: '确定要强制取消此订单吗？',
        success: async (m) => {
          if (m.confirm) {
            try {
              await admin.cancelOrder(orderId)
              uni.showToast({ title: '已强制取消' })
              this.orderPage = 1
              this.loadOrders()
            } catch (e) {
              uni.showToast({ title: e.message || '操作失败', icon: 'none' })
            }
          }
        },
      })
    },
    async loadAgents() {
      if (this.loadingAgents) return
      this.loadingAgents = true
      try {
        const res = await admin.getAgents({ page: this.agentPage, page_size: 20 })
        const items = Array.isArray(res) ? res : (res.items || res.data || [])
        if (this.agentPage === 1) this.agentList = items
        else this.agentList = [...this.agentList, ...items]
        this.hasMoreAgents = items.length >= 20
      } catch (e) {
        uni.showToast({ title: '加载Agent失败', icon: 'none' })
      } finally {
        this.loadingAgents = false
      }
    },
    loadMoreAgents() {
      this.agentPage++
      this.loadAgents()
    },
    async loadPayments() {
      if (this.loadingPayments) return
      this.loadingPayments = true
      try {
        const res = await admin.getPayments({ page: this.paymentPage, page_size: 20 })
        const items = Array.isArray(res) ? res : (res.items || res.data || [])
        if (this.paymentPage === 1) this.paymentList = items
        else this.paymentList = [...this.paymentList, ...items]
        this.hasMorePayments = items.length >= 20
      } catch (e) {
        uni.showToast({ title: '加载支付记录失败', icon: 'none' })
      } finally {
        this.loadingPayments = false
      }
    },
    loadMorePayments() {
      this.paymentPage++
      this.loadPayments()
    },
    previewImage(url) {
      uni.previewImage({ urls: [url] })
    },
    async confirmPayment(paymentId) {
      try {
        await admin.confirmPayment(paymentId)
        uni.showToast({ title: '已确认' })
        this.paymentPage = 1
        this.loadPayments()
      } catch (e) {
        uni.showToast({ title: e.message || '确认失败', icon: 'none' })
      }
    },
    async rejectPayment(paymentId) {
      try {
        await admin.rejectPayment(paymentId)
        uni.showToast({ title: '已拒绝' })
        this.paymentPage = 1
        this.loadPayments()
      } catch (e) {
        uni.showToast({ title: e.message || '操作失败', icon: 'none' })
      }
    },
    async loadDisputes() {
      this.loadingDisputes = true
      try {
        const res = await admin.getDisputes()
        this.disputeList = Array.isArray(res) ? res : (res.items || [])
      } catch (e) {
        // 忽略
      } finally {
        this.loadingDisputes = false
      }
    },
    async resolveDispute(disputeId, verdict) {
      uni.showModal({
        title: '确认裁决',
        content: `确定要${verdict === 'refund' ? '退款给用户' : '放款给Agent'}吗？`,
        success: async (m) => {
          if (m.confirm) {
            try {
              await admin.resolveDispute(disputeId, { verdict })
              uni.showToast({ title: '裁决完成' })
              this.loadDisputes()
            } catch (e) {
              uni.showToast({ title: e.message || '裁决失败', icon: 'none' })
            }
          }
        },
      })
    },
  },
}
</script>

<style scoped>
.admin-page {
  min-height: 100vh;
  background: #f5f5f5;
}

.no-permission {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 200rpx;
}

.no-perm-icon {
  font-size: 120rpx;
  margin-bottom: 30rpx;
}

.no-perm-title {
  font-size: 36rpx;
  font-weight: bold;
  color: #333;
  margin-bottom: 16rpx;
}

.no-perm-desc {
  font-size: 28rpx;
  color: #999;
}

.admin-content {
  display: flex;
  flex-direction: column;
}

.admin-tabs {
  display: flex;
  white-space: nowrap;
  background: #fff;
  border-bottom: 1px solid #e5e5e5;
  position: sticky;
  top: 0;
  z-index: 100;
}

.admin-tab {
  display: inline-block;
  padding: 24rpx 30rpx;
  font-size: 28rpx;
  color: #666;
  border-bottom: 4rpx solid transparent;
}

.admin-tab.active {
  color: #007aff;
  border-bottom-color: #007aff;
  font-weight: bold;
}

.tab-panel {
  padding: 20rpx;
}

.stat-cards {
  display: flex;
  flex-wrap: wrap;
  gap: 20rpx;
}

.stat-card {
  width: calc(50% - 10rpx);
  background: #fff;
  border-radius: 16rpx;
  padding: 30rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-value {
  font-size: 48rpx;
  font-weight: bold;
  color: #333;
  margin-bottom: 10rpx;
}

.stat-label {
  font-size: 26rpx;
  color: #999;
}

.refresh-bar {
  margin-top: 20rpx;
  display: flex;
  justify-content: center;
}

.btn-refresh {
  background: #fff;
  color: #007aff;
  border: 1px solid #007aff;
  border-radius: 30rpx;
  font-size: 28rpx;
  padding: 16rpx 40rpx;
}

.empty-table {
  text-align: center;
  padding: 80rpx;
  color: #999;
  font-size: 28rpx;
}

.table-list {
  background: #fff;
  border-radius: 16rpx;
  overflow: hidden;
}

.table-header {
  display: flex;
  padding: 20rpx 16rpx;
  background: #f5f5f5;
}

.th {
  font-size: 24rpx;
  color: #999;
  font-weight: bold;
}

.table-row {
  display: flex;
  align-items: center;
  padding: 20rpx 16rpx;
  border-bottom: 1px solid #f0f0f0;
}

.table-row:last-child {
  border-bottom: none;
}

.td {
  font-size: 26rpx;
  color: #333;
}

.td-text-overflow {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-tag {
  font-size: 22rpx;
  padding: 4rpx 12rpx;
  border-radius: 20rpx;
}

.status-active { background: #e6f7e6; color: #52c41a; }
.status-banned { background: #fff1f0; color: #ff4d4f; }
.status-pending { background: #fffbe6; color: #faad14; }
.status-in_progress { background: #e6f4ff; color: #1890ff; }
.status-completed { background: #e6f7e6; color: #52c41a; }
.status-cancelled { background: #fff1f0; color: #ff4d4f; }

.btn-tiny {
  font-size: 22rpx;
  padding: 8rpx 16rpx;
  border-radius: 24rpx;
  line-height: 1.5;
  margin: 0 4rpx;
}

.btn-ban { background: #ff4d4f; color: #fff; }
.btn-unban { background: #52c41a; color: #fff; }
.btn-force { background: #52c41a; color: #fff; }
.btn-cancel-order { background: #faad14; color: #fff; }
.btn-confirm { background: #52c41a; color: #fff; }
.btn-reject { background: #ff4d4f; color: #fff; }
.btn-deliver { background: #1890ff; color: #fff; }

.load-more {
  text-align: center;
  padding: 30rpx;
  color: #007aff;
  font-size: 28rpx;
}

.payment-card, .dispute-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 20rpx;
}

.payment-header, .dispute-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16rpx;
}

.payment-title, .dispute-title {
  font-size: 30rpx;
  font-weight: bold;
  color: #333;
}

.payment-amount {
  font-size: 32rpx;
  color: #ff6b00;
  font-weight: bold;
}

.dispute-status {
  font-size: 24rpx;
  padding: 4rpx 16rpx;
  background: #fffbe6;
  color: #faad14;
  border-radius: 20rpx;
}

.payment-screenshot {
  margin-bottom: 16rpx;
}

.payment-screenshot image {
  width: 100%;
  border-radius: 12rpx;
}

.payment-actions, .dispute-actions {
  display: flex;
  gap: 20rpx;
  justify-content: flex-end;
}

.dispute-desc {
  font-size: 26rpx;
  color: #666;
  margin-bottom: 16rpx;
}
</style>