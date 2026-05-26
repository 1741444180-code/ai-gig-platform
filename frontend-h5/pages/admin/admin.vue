<template>
  <view class="page-container admin-page">
    <!-- Header -->
    <view class="admin-header">
      <text class="admin-title">管理中心</text>
      <text class="admin-subtitle">A00062 AIHub</text>
    </view>

    <!-- Tab Bar -->
    <view class="tab-bar">
      <view
        v-for="tab in tabs"
        :key="tab.key"
        :class="['tab-item', { active: currentTab === tab.key }]"
        @click="switchTab(tab.key)"
      >
        <text>{{ tab.label }}</text>
      </view>
    </view>

    <!-- ======== 数据看板 ======== -->
    <view v-if="currentTab === 'dashboard'" class="tab-content">
      <view class="dashboard-grid">
        <view class="stat-card">
          <text class="stat-num">{{ dashboard.users || 0 }}</text>
          <text class="stat-label">用户总数</text>
        </view>
        <view class="stat-card">
          <text class="stat-num">{{ dashboard.agents || 0 }}</text>
          <text class="stat-label">Agent总数</text>
        </view>
        <view class="stat-card">
          <text class="stat-num">{{ dashboard.orders || 0 }}</text>
          <text class="stat-label">订单总数</text>
        </view>
        <view class="stat-card">
          <text class="stat-num">{{ dashboard.active_orders || 0 }}</text>
          <text class="stat-label">进行中</text>
        </view>
        <view class="stat-card">
          <text class="stat-num">{{ dashboard.completed_orders || 0 }}</text>
          <text class="stat-label">已完成</text>
        </view>
        <view class="stat-card">
          <text class="stat-num">¥{{ dashboard.total_amount || 0 }}</text>
          <text class="stat-label">总交易额</text>
        </view>
        <view class="stat-card">
          <text class="stat-num">{{ dashboard.pending_withdraws || 0 }}</text>
          <text class="stat-label">待处理提现</text>
        </view>
        <view class="stat-card">
          <text class="stat-num">{{ dashboard.pending_disputes || 0 }}</text>
          <text class="stat-label">待处理仲裁</text>
        </view>
      </view>
    </view>

    <!-- ======== 用户管理 ======== -->
    <view v-if="currentTab === 'users'" class="tab-content">
      <!-- 搜索栏 -->
      <view class="search-bar">
        <input
          v-model="userSearch"
          class="search-input"
          placeholder="搜索用户手机/昵称"
          @confirm="searchUsers"
        />
        <view class="search-btn" @click="searchUsers"><text>搜索</text></view>
      </view>

      <!-- 用户列表 -->
      <view class="list-container">
        <view v-if="loading" class="loading-state"><text>加载中...</text></view>
        <view v-else-if="users.length === 0" class="empty-state"><text>暂无用户</text></view>
        <view v-else v-for="user in users" :key="user.id" class="list-item">
          <view class="item-info">
            <text class="item-title">{{ user.nickname || '未命名' }}</text>
            <text class="item-sub">{{ user.phone || '未绑定手机' }}</text>
            <view class="item-tags">
              <text :class="['tag', user.is_banned ? 'tag-error' : 'tag-success']">
                {{ user.is_banned ? '已封禁' : '正常' }}
              </text>
              <text class="tag tag-default">信用 {{ user.credit_score || 100 }}</text>
            </view>
          </view>
          <view class="item-actions">
            <view
              v-if="!user.is_banned"
              class="action-btn action-danger"
              @click="banUser(user.id)"
            >
              <text>封禁</text>
            </view>
            <view
              v-else
              class="action-btn action-success"
              @click="unbanUser(user.id)"
            >
              <text>解封</text>
            </view>
          </view>
        </view>
      </view>

      <!-- 分页 -->
      <view class="pagination">
        <view class="page-btn" @click="prevUserPage"><text>上一页</text></view>
        <text class="page-info">{{ userPage }}/{{ userTotalPages || 1 }}</text>
        <view class="page-btn" @click="nextUserPage"><text>下一页</text></view>
      </view>
    </view>

    <!-- ======== Agent管理 ======== -->
    <view v-if="currentTab === 'agents'" class="tab-content">
      <view class="search-bar">
        <input
          v-model="agentSearch"
          class="search-input"
          placeholder="搜索Agent名称/描述"
          @confirm="searchAgents"
        />
        <view class="search-btn" @click="searchAgents"><text>搜索</text></view>
      </view>

      <view class="list-container">
        <view v-if="loading" class="loading-state"><text>加载中...</text></view>
        <view v-else-if="agents.length === 0" class="empty-state"><text>暂无Agent</text></view>
        <view v-else v-for="agent in agents" :key="agent.id" class="list-item">
          <view class="item-info">
            <text class="item-title">{{ agent.name || '未命名' }}</text>
            <text class="item-sub">{{ agent.description || '无描述' }}</text>
            <view class="item-tags">
              <text :class="['tag', agent.is_banned ? 'tag-error' : 'tag-success']">
                {{ agent.is_banned ? '已封禁' : '正常' }}
              </text>
              <text class="tag tag-primary">评分 {{ agent.rating || 'N/A' }}</text>
            </view>
          </view>
          <view class="item-actions">
            <view
              v-if="!agent.is_banned"
              class="action-btn action-danger"
              @click="banAgent(agent.id)"
            >
              <text>封禁</text>
            </view>
            <view v-else class="action-btn action-success" @click="unbanAgent(agent.id)">
              <text>解封</text>
            </view>
          </view>
        </view>
      </view>

      <view class="pagination">
        <view class="page-btn" @click="prevAgentPage"><text>上一页</text></view>
        <text class="page-info">{{ agentPage }}/{{ agentTotalPages || 1 }}</text>
        <view class="page-btn" @click="nextAgentPage"><text>下一页</text></view>
      </view>
    </view>

    <!-- ======== 订单管理 ======== -->
    <view v-if="currentTab === 'orders'" class="tab-content">
      <!-- 状态筛选 -->
      <view class="filter-bar">
        <view
          v-for="s in orderStatuses"
          :key="s.value"
          :class="['filter-chip', { active: orderStatusFilter === s.value }]"
          @click="orderStatusFilter = s.value; loadOrders()"
        >
          <text>{{ s.label }}</text>
        </view>
      </view>

      <view class="list-container">
        <view v-if="loading" class="loading-state"><text>加载中...</text></view>
        <view v-else-if="orders.length === 0" class="empty-state"><text>暂无订单</text></view>
        <view v-else v-for="order in orders" :key="order.id" class="list-item">
          <view class="item-info">
            <text class="item-title">订单 #{{ order.id }}</text>
            <text class="item-sub">{{ order.demand_title || order.title || '需求' }}</text>
            <view class="item-tags">
              <text :class="['tag', getStatusTagClass(order.status)]">{{ order.status_text || order.status }}</text>
              <text class="tag tag-default">¥{{ order.amount || 0 }}</text>
            </view>
          </view>
          <view class="item-actions">
            <view class="action-btn action-warning" @click="forceCancelOrder(order.id)">
              <text>取消</text>
            </view>
            <view class="action-btn action-primary" @click="forceCompleteOrder(order.id)">
              <text>完成</text>
            </view>
          </view>
        </view>
      </view>

      <view class="pagination">
        <view class="page-btn" @click="prevOrderPage"><text>上一页</text></view>
        <text class="page-info">{{ orderPage }}/{{ orderTotalPages || 1 }}</text>
        <view class="page-btn" @click="nextOrderPage"><text>下一页</text></view>
      </view>
    </view>

    <!-- ======== 仲裁管理 ======== -->
    <view v-if="currentTab === 'arbitration'" class="tab-content">
      <view class="list-container">
        <view v-if="loading" class="loading-state"><text>加载中...</text></view>
        <view v-else-if="disputes.length === 0" class="empty-state"><text>暂无仲裁</text></view>
        <view v-else v-for="d in disputes" :key="d.id" class="list-item dispute-item">
          <view class="item-info">
            <text class="item-title">仲裁 #{{ d.id }}</text>
            <text class="item-sub">订单 #{{ d.order_id }} - {{ d.reason || '争议' }}</text>
            <view class="item-tags">
              <text class="tag tag-warning">{{ d.status || '待处理' }}</text>
              <text class="tag tag-default">{{ d.created_at || '' }}</text>
            </view>
          </view>
          <view class="item-actions">
            <view class="action-btn action-primary" @click="showResolveForm(d)">
              <text>裁决</text>
            </view>
          </view>
        </view>
      </view>

      <!-- 裁决弹窗 -->
      <view v-if="resolveFormVisible" class="modal-overlay" @click="resolveFormVisible = false">
        <view class="modal-content" @click.stop>
          <text class="modal-title">裁决仲裁 #{{ currentDispute?.id }}</text>
          <textarea
            v-model="resolveForm.reason"
            class="modal-textarea"
            placeholder="裁决理由"
            rows="4"
          />
          <view class="modal-actions">
            <view class="modal-btn modal-btn-cancel" @click="resolveFormVisible = false">
              <text>取消</text>
            </view>
            <view
              class="modal-btn modal-btn-confirm"
              @click="submitResolve"
              :disabled="resolveLoading"
            >
              <text>{{ resolveLoading ? '提交中...' : '确认裁决' }}</text>
            </view>
          </view>
        </view>
      </view>
    </view>

    <!-- ======== 支付确认 ======== -->
    <view v-if="currentTab === 'payments'" class="tab-content">
      <view class="list-container">
        <view v-if="loading" class="loading-state"><text>加载中...</text></view>
        <view v-else-if="payments.length === 0" class="empty-state"><text>暂无待确认支付</text></view>
        <view v-else v-for="p in payments" :key="p.id" class="list-item">
          <view class="item-info">
            <text class="item-title">支付 #{{ p.id }}</text>
            <text class="item-sub">订单 #{{ p.order_id }} - {{ p.method || '转账' }}</text>
            <view class="item-tags">
              <text class="tag tag-warning">{{ p.amount || 0 }}元</text>
              <text class="tag tag-default">{{ p.created_at || '' }}</text>
            </view>
            <view v-if="p.screenshot" class="payment-screenshot">
              <image :src="p.screenshot" mode="aspectFit" class="screenshot-img" @click="previewImage(p.screenshot)" />
            </view>
          </view>
          <view class="item-actions">
            <view class="action-btn action-success" @click="confirmPayment(p.id)">
              <text>通过</text>
            </view>
            <view class="action-btn action-danger" @click="rejectPayment(p.id)">
              <text>拒绝</text>
            </view>
          </view>
        </view>
      </view>

      <view class="pagination">
        <view class="page-btn" @click="prevPaymentPage"><text>上一页</text></view>
        <text class="page-info">{{ paymentPage }}/{{ paymentTotalPages || 1 }}</text>
        <view class="page-btn" @click="nextPaymentPage"><text>下一页</text></view>
      </view>
    </view>

    <!-- ======== 提现审核 ======== -->
    <view v-if="currentTab === 'withdraws'" class="tab-content">
      <view class="list-container">
        <view v-if="loading" class="loading-state"><text>加载中...</text></view>
        <view v-else-if="withdraws.length === 0" class="empty-state"><text>暂无待处理提现</text></view>
        <view v-else v-for="w in withdraws" :key="w.id" class="list-item">
          <view class="item-info">
            <text class="item-title">提现 #{{ w.id }}</text>
            <text class="item-sub">{{ w.method || '银行卡' }} - {{ w.account || w.bank_account || '' }}</text>
            <view class="item-tags">
              <text class="tag tag-warning">¥{{ w.amount || 0 }}</text>
              <text :class="['tag', w.status === 'approved' ? 'tag-success' : w.status === 'rejected' ? 'tag-error' : 'tag-default']">
                {{ w.status_text || w.status }}
              </text>
            </view>
          </view>
          <view v-if="w.status === 'pending'" class="item-actions">
            <view class="action-btn action-success" @click="approveWithdraw(w.id)">
              <text>批准</text>
            </view>
            <view class="action-btn action-danger" @click="rejectWithdraw(w.id)">
              <text>拒绝</text>
            </view>
          </view>
        </view>
      </view>

      <view class="pagination">
        <view class="page-btn" @click="prevWithdrawPage"><text>上一页</text></view>
        <text class="page-info">{{ withdrawPage }}/{{ withdrawTotalPages || 1 }}</text>
        <view class="page-btn" @click="nextWithdrawPage"><text>下一页</text></view>
      </view>
    </view>

    <view style="height: 40px;"></view>
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { admin } from '@/api/index.js'

// ---------- Tab配置 ----------
const tabs = [
  { key: 'dashboard', label: '看板' },
  { key: 'users', label: '用户' },
  { key: 'agents', label: 'Agent' },
  { key: 'orders', label: '订单' },
  { key: 'arbitration', label: '仲裁' },
  { key: 'payments', label: '支付' },
  { key: 'withdraws', label: '提现' },
]
const currentTab = ref('dashboard')

// ---------- 通用状态 ----------
const loading = ref(false)

// ---------- 看板 ----------
const dashboard = ref({})

// ---------- 用户管理 ----------
const users = ref([])
const userSearch = ref('')
const userPage = ref(1)
const userTotalPages = ref(1)

// ---------- Agent管理 ----------
const agents = ref([])
const agentSearch = ref('')
const agentPage = ref(1)
const agentTotalPages = ref(1)

// ---------- 订单管理 ----------
const orders = ref([])
const orderStatusFilter = ref('')
const orderStatuses = [
  { label: '全部', value: '' },
  { label: '待接单', value: 'pending' },
  { label: '进行中', value: 'in_progress' },
  { label: '待验收', value: 'delivered' },
  { label: '已完成', value: 'completed' },
  { label: '已取消', value: 'cancelled' },
]
const orderPage = ref(1)
const orderTotalPages = ref(1)

// ---------- 仲裁管理 ----------
const disputes = ref([])
const resolveFormVisible = ref(false)
const currentDispute = ref(null)
const resolveForm = ref({ reason: '' })
const resolveLoading = ref(false)

// ---------- 支付确认 ----------
const payments = ref([])
const paymentPage = ref(1)
const paymentTotalPages = ref(1)

// ---------- 提现审核 ----------
const withdraws = ref([])
const withdrawPage = ref(1)
const withdrawTotalPages = ref(1)

// ---------- 方法 ----------
function switchTab(key) {
  currentTab.value = key
  if (key === 'dashboard') loadDashboard()
  else if (key === 'users') loadUsers()
  else if (key === 'agents') loadAgents()
  else if (key === 'orders') loadOrders()
  else if (key === 'arbitration') loadDisputes()
  else if (key === 'payments') loadPayments()
  else if (key === 'withdraws') loadWithdraws()
}

// 看板
async function loadDashboard() {
  loading.value = true
  try {
    const res = await admin.getDashboard()
    dashboard.value = res.data || res || {}
  } catch (e) {
    console.error('loadDashboard error', e)
  } finally {
    loading.value = false
  }
}

// 用户管理
async function loadUsers(page = 1) {
  loading.value = true
  try {
    const params = { page, page_size: 20 }
    if (userSearch.value) params.keyword = userSearch.value
    const res = await admin.getUsers(params)
    const data = res.data || res
    users.value = data.items || data.list || []
    const total = data.total || data.total_count || 0
    userTotalPages.value = Math.ceil(total / 20) || 1
    userPage.value = page
  } catch (e) {
    console.error('loadUsers error', e)
  } finally {
    loading.value = false
  }
}
function searchUsers() { loadUsers(1) }
function prevUserPage() { if (userPage.value > 1) loadUsers(userPage.value - 1) }
function nextUserPage() { if (userPage.value < userTotalPages.value) loadUsers(userPage.value + 1) }

async function banUser(id) {
  try {
    await admin.banUser(id)
    uni.showToast({ title: '已封禁', icon: 'success' })
    loadUsers(userPage.value)
  } catch (e) {
    uni.showToast({ title: e.message || '操作失败', icon: 'none' })
  }
}
async function unbanUser(id) {
  try {
    await admin.unbanUser(id)
    uni.showToast({ title: '已解封', icon: 'success' })
    loadUsers(userPage.value)
  } catch (e) {
    uni.showToast({ title: e.message || '操作失败', icon: 'none' })
  }
}

// Agent管理
async function loadAgents(page = 1) {
  loading.value = true
  try {
    const params = { page, page_size: 20 }
    if (agentSearch.value) params.keyword = agentSearch.value
    const res = await admin.getAgents(params)
    const data = res.data || res
    agents.value = data.items || data.list || []
    const total = data.total || data.total_count || 0
    agentTotalPages.value = Math.ceil(total / 20) || 1
    agentPage.value = page
  } catch (e) {
    console.error('loadAgents error', e)
  } finally {
    loading.value = false
  }
}
function searchAgents() { loadAgents(1) }
function prevAgentPage() { if (agentPage.value > 1) loadAgents(agentPage.value - 1) }
function nextAgentPage() { if (agentPage.value < agentTotalPages.value) loadAgents(agentPage.value + 1) }

async function banAgent(id) {
  try {
    await admin.banUser(id)
    uni.showToast({ title: '已封禁', icon: 'success' })
    loadAgents(agentPage.value)
  } catch (e) {
    uni.showToast({ title: e.message || '操作失败', icon: 'none' })
  }
}
async function unbanAgent(id) {
  try {
    await admin.unbanUser(id)
    uni.showToast({ title: '已解封', icon: 'success' })
    loadAgents(agentPage.value)
  } catch (e) {
    uni.showToast({ title: e.message || '操作失败', icon: 'none' })
  }
}

// 订单管理
async function loadOrders(page = 1) {
  loading.value = true
  try {
    const params = { page, page_size: 20 }
    if (orderStatusFilter.value) params.status = orderStatusFilter.value
    const res = await admin.getOrders(params)
    const data = res.data || res
    orders.value = data.items || data.list || []
    const total = data.total || data.total_count || 0
    orderTotalPages.value = Math.ceil(total / 20) || 1
    orderPage.value = page
  } catch (e) {
    console.error('loadOrders error', e)
  } finally {
    loading.value = false
  }
}
function prevOrderPage() { if (orderPage.value > 1) loadOrders(orderPage.value - 1) }
function nextOrderPage() { if (orderPage.value < orderTotalPages.value) loadOrders(orderPage.value + 1) }

async function forceCancelOrder(id) {
  try {
    await admin.cancelOrder(id)
    uni.showToast({ title: '已取消', icon: 'success' })
    loadOrders(orderPage.value)
  } catch (e) {
    uni.showToast({ title: e.message || '操作失败', icon: 'none' })
  }
}
async function forceCompleteOrder(id) {
  try {
    await admin.releaseOrder(id)
    uni.showToast({ title: '已完成', icon: 'success' })
    loadOrders(orderPage.value)
  } catch (e) {
    uni.showToast({ title: e.message || '操作失败', icon: 'none' })
  }
}

// 仲裁管理
async function loadDisputes() {
  loading.value = true
  try {
    const res = await admin.getDisputes()
    disputes.value = res.data || res || []
  } catch (e) {
    console.error('loadDisputes error', e)
  } finally {
    loading.value = false
  }
}
function showResolveForm(d) {
  currentDispute.value = d
  resolveForm.value = { reason: '' }
  resolveFormVisible.value = true
}
async function submitResolve() {
  if (!resolveForm.value.reason) {
    uni.showToast({ title: '请填写裁决理由', icon: 'none' })
    return
  }
  resolveLoading.value = true
  try {
    await admin.resolveDispute(currentDispute.value.id, {
      decision: resolveForm.value.reason,
      winner: 'client',
    })
    uni.showToast({ title: '裁决已提交', icon: 'success' })
    resolveFormVisible.value = false
    loadDisputes()
  } catch (e) {
    uni.showToast({ title: e.message || '操作失败', icon: 'none' })
  } finally {
    resolveLoading.value = false
  }
}

// 支付确认
async function loadPayments(page = 1) {
  loading.value = true
  try {
    const res = await admin.getPayments({ page, page_size: 20 })
    const data = res.data || res
    payments.value = data.items || data.list || []
    const total = data.total || data.total_count || 0
    paymentTotalPages.value = Math.ceil(total / 20) || 1
    paymentPage.value = page
  } catch (e) {
    console.error('loadPayments error', e)
  } finally {
    loading.value = false
  }
}
function prevPaymentPage() { if (paymentPage.value > 1) loadPayments(paymentPage.value - 1) }
function nextPaymentPage() { if (paymentPage.value < paymentTotalPages.value) loadPayments(paymentPage.value + 1) }

async function confirmPayment(id) {
  try {
    await admin.confirmPayment(id)
    uni.showToast({ title: '已确认', icon: 'success' })
    loadPayments(paymentPage.value)
  } catch (e) {
    uni.showToast({ title: e.message || '操作失败', icon: 'none' })
  }
}
async function rejectPayment(id) {
  try {
    await admin.rejectPayment(id)
    uni.showToast({ title: '已拒绝', icon: 'success' })
    loadPayments(paymentPage.value)
  } catch (e) {
    uni.showToast({ title: e.message || '操作失败', icon: 'none' })
  }
}

// 提现审核
async function loadWithdraws(page = 1) {
  loading.value = true
  try {
    const res = await admin.getWithdraws({ page, page_size: 20 })
    const data = res.data || res
    withdraws.value = data.items || data.list || []
    const total = data.total || data.total_count || 0
    withdrawTotalPages.value = Math.ceil(total / 20) || 1
    withdrawPage.value = page
  } catch (e) {
    console.error('loadWithdraws error', e)
  } finally {
    loading.value = false
  }
}
function prevWithdrawPage() { if (withdrawPage.value > 1) loadWithdraws(withdrawPage.value - 1) }
function nextWithdrawPage() { if (withdrawPage.value < withdrawTotalPages.value) loadWithdraws(withdrawPage.value + 1) }

async function approveWithdraw(id) {
  try {
    await admin.approveWithdraw ? admin.approveWithdraw(id) : Promise.reject(new Error('API not found'))
    uni.showToast({ title: '已批准', icon: 'success' })
    loadWithdraws(withdrawPage.value)
  } catch (e) {
    uni.showToast({ title: e.message || '操作失败', icon: 'none' })
  }
}
async function rejectWithdraw(id) {
  try {
    await admin.rejectWithdraw ? admin.rejectWithdraw(id) : Promise.reject(new Error('API not found'))
    uni.showToast({ title: '已拒绝', icon: 'success' })
    loadWithdraws(withdrawPage.value)
  } catch (e) {
    uni.showToast({ title: e.message || '操作失败', icon: 'none' })
  }
}

// 工具方法
function getStatusTagClass(status) {
  const map = {
    pending: 'tag-warning',
    in_progress: 'tag-primary',
    delivered: 'tag-primary',
    completed: 'tag-success',
    cancelled: 'tag-error',
  }
  return map[status] || 'tag-default'
}
function previewImage(url) {
  uni.previewImage({ urls: [url] })
}

// 初始化
onMounted(() => {
  loadDashboard()
})
</script>

<style scoped>
/* 通用页面 */
.page-container { min-height: 100vh; background: #F5F7FA; }
.admin-page { padding-bottom: 40px; }

/* Header */
.admin-header {
  background: linear-gradient(135deg, #1D1D1F 0%, #2D2D30 100%);
  padding: 48px 20px 20px;
  color: #fff;
}
.admin-title { font-size: 20px; font-weight: 600; display: block; }
.admin-subtitle { font-size: 12px; color: #A1A1AA; margin-top: 4px; display: block; }

/* Tab Bar */
.tab-bar {
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  background: #fff;
  border-bottom: 1px solid #E5E7EB;
  position: sticky;
  top: 0;
  z-index: 10;
}
.tab-item {
  padding: 12px 14px;
  font-size: 13px;
  color: #71717A;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}
.tab-item.active {
  color: #4F46E5;
  border-bottom-color: #4F46E5;
}

/* Tab Content */
.tab-content { padding: 16px; }

/* 看板 */
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}
.stat-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.stat-card .stat-num {
  font-size: 24px;
  font-weight: 700;
  color: #1D1D1F;
}
.stat-card .stat-label {
  font-size: 12px;
  color: #71717A;
  margin-top: 4px;
}

/* 搜索栏 */
.search-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
.search-input {
  flex: 1;
  background: #fff;
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 14px;
  border: 1px solid #E5E7EB;
}
.search-btn {
  background: #4F46E5;
  color: #fff;
  border-radius: 8px;
  padding: 10px 16px;
  font-size: 14px;
}

/* 筛选栏 */
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}
.filter-chip {
  background: #fff;
  border: 1px solid #E5E7EB;
  border-radius: 20px;
  padding: 6px 14px;
  font-size: 12px;
  color: #71717A;
}
.filter-chip.active {
  background: #4F46E5;
  color: #fff;
  border-color: #4F46E5;
}

/* 列表 */
.list-container { display: flex; flex-direction: column; gap: 10px; }
.list-item {
  background: #fff;
  border-radius: 12px;
  padding: 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.item-info { flex: 1; }
.item-title { font-size: 14px; font-weight: 600; color: #1D1D1F; display: block; }
.item-sub { font-size: 12px; color: #71717A; margin-top: 2px; display: block; }
.item-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
.tag {
  font-size: 11px;
  border-radius: 4px;
  padding: 2px 6px;
}
.tag-default { background: #F3F4F6; color: #71717A; }
.tag-primary { background: #EEF2FF; color: #4F46E5; }
.tag-success { background: #D1FAE5; color: #059669; }
.tag-warning { background: #FEF3C7; color: #EA580C; }
.tag-error { background: #FEE2E2; color: #DC2626; }
.item-actions { display: flex; gap: 8px; margin-left: 12px; }
.action-btn {
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
}
.action-primary { background: #4F46E5; color: #fff; }
.action-success { background: #059669; color: #fff; }
.action-danger { background: #DC2626; color: #fff; }
.action-warning { background: #EA580C; color: #fff; }

/* 空状态/加载 */
.empty-state, .loading-state {
  text-align: center;
  padding: 40px;
  color: #A1A1AA;
  font-size: 14px;
}

/* 分页 */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-top: 16px;
}
.page-btn {
  background: #fff;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  padding: 6px 16px;
  font-size: 13px;
}
.page-info { font-size: 13px; color: #71717A; }

/* 支付截图 */
.payment-screenshot { margin-top: 8px; }
.screenshot-img {
  width: 120px;
  height: 80px;
  border-radius: 6px;
  border: 1px solid #E5E7EB;
}

/* 模态弹窗 */
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.5);
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
}
.modal-content {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  width: 90%;
  max-width: 400px;
}
.modal-title { font-size: 16px; font-weight: 600; display: block; margin-bottom: 16px; }
.modal-textarea {
  width: 100%;
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  padding: 12px;
  font-size: 14px;
  resize: none;
}
.modal-actions { display: flex; gap: 12px; margin-top: 16px; }
.modal-btn {
  flex: 1;
  text-align: center;
  padding: 12px;
  border-radius: 8px;
  font-size: 14px;
}
.modal-btn-cancel { background: #F3F4F6; color: #71717A; }
.modal-btn-confirm { background: #4F46E5; color: #fff; }
.modal-btn[disabled] { opacity: 0.6; }
</style>