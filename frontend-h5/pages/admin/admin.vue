<template>
  <view class="page-container admin-page">
    <view class="admin-header">
      <text class="admin-title">管理中心</text>
      <text class="admin-subtitle">A00062 AIHub</text>
    </view>
    <view class="tab-bar">
      <view v-for="tab in tabs" :key="tab.key" :class="['tab-item', { active: currentTab === tab.key }]" @click="switchTab(tab.key)">
        <text>{{ tab.label }}</text>
      </view>
    </view>

    <!-- 数据看板 -->
    <view v-if="currentTab === 'dashboard'" class="tab-content">
      <view v-if="loading" class="loading-state"><text>加载中...</text></view>
      <view v-else class="dashboard-grid">
        <view class="stat-card stat-primary"><text class="stat-num">{{ dashboard.total_users || 0 }}</text><text class="stat-label">用户总数</text></view>
        <view class="stat-card stat-primary"><text class="stat-num">{{ dashboard.total_agents || 0 }}</text><text class="stat-label">Agent总数</text></view>
        <view class="stat-card stat-primary"><text class="stat-num">{{ dashboard.total_demands || 0 }}</text><text class="stat-label">需求总数</text></view>
        <view class="stat-card stat-primary"><text class="stat-num">{{ dashboard.total_orders || 0 }}</text><text class="stat-label">订单总数</text></view>
        <view class="stat-card stat-accent"><text class="stat-num">{{ dashboard.today_new_demands || 0 }}</text><text class="stat-label">今日新增需求</text></view>
        <view class="stat-card stat-accent"><text class="stat-num">{{ dashboard.today_new_orders || 0 }}</text><text class="stat-label">今日新增订单</text></view>
        <view class="stat-card stat-success"><text class="stat-num">{{ dashboard.completion_rate || 0 }}%</text><text class="stat-label">完成率</text></view>
        <view class="stat-card stat-success"><text class="stat-num">¥{{ dashboard.avg_price || 0 }}</text><text class="stat-label">平均客单价</text></view>
        <view class="stat-card stat-warning"><text class="stat-num">{{ dashboard.pending_arbitration || 0 }}</text><text class="stat-label">待处理仲裁</text></view>
      </view>
    </view>

    <!-- 用户管理 -->
    <view v-if="currentTab === 'users'" class="tab-content">
      <view class="search-bar">
        <input v-model="userSearch" class="search-input" placeholder="搜索用户手机/昵称" @confirm="searchUsers" />
        <view class="search-btn" @click="searchUsers"><text>搜索</text></view>
      </view>
      <view class="list-container">
        <view v-if="loading" class="loading-state"><text>加载中...</text></view>
        <view v-else-if="users.length === 0" class="empty-state"><text>暂无用户</text></view>
        <view v-else v-for="user in users" :key="user.id" class="list-item">
          <view class="item-info">
            <text class="item-title">{{ user.nickname || '未命名' }}</text>
            <text class="item-sub">{{ user.phone || '未绑定手机' }}</text>
            <view class="item-tags">
              <text :class="['tag', getUserStatusTagClass(user.status)]">{{ getUserStatusText(user.status) }}</text>
              <text class="tag tag-default">{{ user.role || 'user' }}</text>
            </view>
            <text class="item-date">注册: {{ formatDate(user.created_at) }}</text>
          </view>
          <view class="item-actions">
            <view v-if="user.status !== 'banned'" class="action-btn action-danger" @click="showBanForm(user)"><text>封禁</text></view>
            <view v-else class="action-btn action-success" @click="unbanUser(user.id)"><text>解封</text></view>
          </view>
        </view>
      </view>
      <view class="pagination">
        <view class="page-btn" @click="prevUserPage"><text>上一页</text></view>
        <text class="page-info">{{ userPage }}/{{ userTotalPages || 1 }}</text>
        <view class="page-btn" @click="nextUserPage"><text>下一页</text></view>
      </view>
    </view>

    <!-- Agent管理 -->
    <view v-if="currentTab === 'agents'" class="tab-content">
      <view class="filter-bar">
        <view v-for="s in agentStatuses" :key="s.value" :class="['filter-chip', { active: agentStatusFilter === s.value }]" @click="agentStatusFilter = s.value; loadAgents(1)">
          <text>{{ s.label }}</text>
        </view>
      </view>
      <view class="search-bar">
        <input v-model="agentSearch" class="search-input" placeholder="搜索Agent名称" @confirm="searchAgents" />
        <view class="search-btn" @click="searchAgents"><text>搜索</text></view>
      </view>
      <view class="list-container">
        <view v-if="loading" class="loading-state"><text>加载中...</text></view>
        <view v-else-if="agents.length === 0" class="empty-state"><text>暂无Agent</text></view>
        <view v-else v-for="agent in agents" :key="agent.id" class="list-item">
          <view class="item-info">
            <text class="item-title">{{ agent.name || '未命名' }}</text>
            <view class="item-tags">
              <text :class="['tag', getAgentStatusTagClass(agent.status)]">{{ getAgentStatusText(agent.status) }}</text>
              <text class="tag tag-primary">完成 {{ agent.completed_count || 0 }} 单</text>
              <text class="tag tag-default">信用 {{ agent.credit_score || 0 }}</text>
              <text v-if="agent.is_owner_agent" class="tag tag-warning">官方</text>
            </view>
            <text class="item-date">创建: {{ formatDate(agent.created_at) }}</text>
          </view>
          <view class="item-actions">
            <view v-if="agent.status !== 'banned'" class="action-btn action-danger" @click="showBanAgentForm(agent)"><text>封禁</text></view>
            <view v-else class="action-btn action-success" @click="unbanAgent(agent.id)"><text>解封</text></view>
          </view>
        </view>
      </view>
      <view class="pagination">
        <view class="page-btn" @click="prevAgentPage"><text>上一页</text></view>
        <text class="page-info">{{ agentPage }}/{{ agentTotalPages || 1 }}</text>
        <view class="page-btn" @click="nextAgentPage"><text>下一页</text></view>
      </view>
    </view>

    <!-- 订单管理 -->
    <view v-if="currentTab === 'orders'" class="tab-content">
      <view class="filter-bar">
        <view v-for="s in orderStatuses" :key="s.value" :class="['filter-chip', { active: orderStatusFilter === s.value }]" @click="orderStatusFilter = s.value; loadOrders(1)">
          <text>{{ s.label }}</text>
        </view>
      </view>
      <view class="list-container">
        <view v-if="loading" class="loading-state"><text>加载中...</text></view>
        <view v-else-if="orders.length === 0" class="empty-state"><text>暂无订单</text></view>
        <view v-else v-for="order in orders" :key="order.id" class="list-item">
          <view class="item-info">
            <text class="item-title">订单 #{{ order.id }}</text>
            <text class="item-sub">需求 #{{ order.demand_id }} | Agent #{{ order.agent_id }}</text>
            <view class="item-tags">
              <text :class="['tag', getOrderStatusTagClass(order.status)]">{{ getOrderStatusText(order.status) }}</text>
              <text class="tag tag-primary">¥{{ order.price || 0 }}</text>
            </view>
            <text class="item-date">创建: {{ formatDate(order.created_at) }}</text>
          </view>
          <view class="item-actions">
            <view v-if="order.status !== 'cancelled' && order.status !== 'completed'" class="action-btn action-danger" @click="showForceActionForm(order, 'cancel')"><text>取消</text></view>
            <view v-if="order.status !== 'cancelled' && order.status !== 'completed'" class="action-btn action-success" @click="showForceActionForm(order, 'complete')"><text>完成</text></view>
          </view>
        </view>
      </view>
      <view class="pagination">
        <view class="page-btn" @click="prevOrderPage"><text>上一页</text></view>
        <text class="page-info">{{ orderPage }}/{{ orderTotalPages || 1 }}</text>
        <view class="page-btn" @click="nextOrderPage"><text>下一页</text></view>
      </view>
    </view>

    <!-- 仲裁管理 -->
    <view v-if="currentTab === 'arbitration'" class="tab-content">
      <view class="filter-bar">
        <view v-for="s in arbitrationStatuses" :key="s.value" :class="['filter-chip', { active: arbitrationStatusFilter === s.value }]" @click="arbitrationStatusFilter = s.value; loadArbitration()">
          <text>{{ s.label }}</text>
        </view>
      </view>
      <view class="list-container">
        <view v-if="loading" class="loading-state"><text>加载中...</text></view>
        <view v-else-if="arbitrations.length === 0" class="empty-state"><text>暂无仲裁</text></view>
        <view v-else v-for="arb in arbitrations" :key="arb.id" class="list-item dispute-item">
          <view class="item-info">
            <text class="item-title">订单 #{{ arb.id }}</text>
            <text class="item-sub">当前状态: {{ getOrderStatusText(arb.status) }}</text>
            <view class="item-tags">
              <text class="tag tag-warning">{{ getArbitrationStatusText(arb.arbitration_status) }}</text>
              <text class="tag tag-default">拒绝 {{ arb.reject_count || 0 }} 次</text>
            </view>
            <text class="item-date">创建: {{ formatDate(arb.created_at) }}</text>
          </view>
          <view class="item-actions">
            <view v-if="arb.arbitration_status === 'pending'" class="action-btn action-primary" @click="showResolveForm(arb)"><text>裁决</text></view>
          </view>
        </view>
      </view>
      <view v-if="resolveFormVisible" class="modal-overlay" @click="resolveFormVisible = false">
        <view class="modal-content" @click.stop>
          <text class="modal-title">裁决订单 #{{ currentArbitration?.id }}</text>
          <text class="modal-label">裁决结果</text>
          <view class="radio-group">
            <view v-for="opt in resolutionOptions" :key="opt.value" :class="['radio-item', { active: resolveForm.resolution === opt.value }]" @click="resolveForm.resolution = opt.value"><text>{{ opt.label }}</text></view>
          </view>
          <text class="modal-label" style="margin-top: 12px;">退款金额（可选）</text>
          <input v-model="resolveForm.refund_amount" class="modal-input" type="number" placeholder="如需退款，输入金额" />
          <text class="modal-label" style="margin-top: 12px;">裁决理由</text>
          <textarea v-model="resolveForm.reason" class="modal-textarea" placeholder="请输入裁决理由" rows="4" />
          <view class="modal-actions">
            <view class="modal-btn modal-btn-cancel" @click="resolveFormVisible = false"><text>取消</text></view>
            <view class="modal-btn modal-btn-confirm" @click="submitResolve" :disabled="resolveLoading"><text>{{ resolveLoading ? '提交中...' : '确认裁决' }}</text></view>
          </view>
        </view>
      </view>
    </view>

    <!-- 支付确认 -->
    <view v-if="currentTab === 'payments'" class="tab-content">
      <view class="filter-bar">
        <view v-for="s in paymentStatuses" :key="s.value" :class="['filter-chip', { active: paymentStatusFilter === s.value }]" @click="paymentStatusFilter = s.value; loadPayments(1)">
          <text>{{ s.label }}</text>
        </view>
      </view>
      <view class="list-container">
        <view v-if="loading" class="loading-state"><text>加载中...</text></view>
        <view v-else-if="payments.length === 0" class="empty-state"><text>暂无支付记录</text></view>
        <view v-else v-for="p in payments" :key="p.id" class="list-item">
          <view class="item-info">
            <text class="item-title">支付 #{{ p.id }}</text>
            <text class="item-sub">订单 #{{ p.order_id }} | {{ p.payment_method || '转账' }}</text>
            <view class="item-tags">
              <text :class="['tag', getPaymentStatusTagClass(p.status)]">{{ getPaymentStatusText(p.status) }}</text>
              <text class="tag tag-primary">¥{{ p.amount || 0 }}</text>
              <text class="tag tag-default">{{ p.type || '收入' }}</text>
            </view>
            <text class="item-date">{{ formatDate(p.created_at) }}</text>
          </view>
          <view class="item-actions">
            <view v-if="p.status === 'pending'" class="action-btn action-success" @click="confirmPayment(p.id)"><text>通过</text></view>
            <view v-if="p.status === 'pending'" class="action-btn action-danger" @click="rejectPayment(p.id)"><text>拒绝</text></view>
          </view>
        </view>
      </view>
      <view class="pagination">
        <view class="page-btn" @click="prevPaymentPage"><text>上一页</text></view>
        <text class="page-info">{{ paymentPage }}/{{ paymentTotalPages || 1 }}</text>
        <view class="page-btn" @click="nextPaymentPage"><text>下一页</text></view>
      </view>
    </view>

    <!-- 提现审核 -->
    <view v-if="currentTab === 'withdraws'" class="tab-content">
      <view class="filter-bar">
        <view v-for="s in withdrawStatuses" :key="s.value" :class="['filter-chip', { active: withdrawStatusFilter === s.value }]" @click="withdrawStatusFilter = s.value; loadWithdraws(1)">
          <text>{{ s.label }}</text>
        </view>
      </view>
      <view class="list-container">
        <view v-if="loading" class="loading-state"><text>加载中...</text></view>
        <view v-else-if="withdraws.length === 0" class="empty-state"><text>暂无提现记录</text></view>
        <view v-else v-for="w in withdraws" :key="w.id" class="list-item">
          <view class="item-info">
            <text class="item-title">提现 #{{ w.id }}</text>
            <text class="item-sub">{{ w.method || '银行卡' }} - {{ w.account || '' }}</text>
            <view class="item-tags">
              <text :class="['tag', getWithdrawStatusTagClass(w.status)]">{{ getWithdrawStatusText(w.status) }}</text>
              <text class="tag tag-warning">¥{{ w.amount || 0 }}</text>
            </view>
            <text class="item-date">{{ formatDate(w.created_at) }}</text>
          </view>
          <view v-if="w.status === 'pending'" class="item-actions">
            <view class="action-btn action-success" @click="approveWithdraw(w.id)"><text>批准</text></view>
            <view class="action-btn action-danger" @click="rejectWithdraw(w.id)"><text>拒绝</text></view>
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

    <!-- 封禁用户弹窗 -->
    <view v-if="banFormVisible" class="modal-overlay" @click="banFormVisible = false">
      <view class="modal-content" @click.stop>
        <text class="modal-title">封禁用户</text>
        <text class="modal-sub">用户: {{ banTargetUser?.nickname || banTargetUser?.phone }}</text>
        <input v-model="banForm.reason" class="modal-input" placeholder="封禁原因（必填）" style="margin-top: 12px;" />
        <view class="modal-actions">
          <view class="modal-btn modal-btn-cancel" @click="banFormVisible = false"><text>取消</text></view>
          <view class="modal-btn modal-btn-confirm" @click="submitBanUser" :disabled="banLoading"><text>{{ banLoading ? '提交中...' : '确认封禁' }}</text></view>
        </view>
      </view>
    </view>

    <!-- 封禁Agent弹窗 -->
    <view v-if="banAgentFormVisible" class="modal-overlay" @click="banAgentFormVisible = false">
      <view class="modal-content" @click.stop>
        <text class="modal-title">封禁Agent</text>
        <text class="modal-sub">Agent: {{ banTargetAgent?.name }}</text>
        <input v-model="banAgentForm.reason" class="modal-input" placeholder="封禁原因（必填）" style="margin-top: 12px;" />
        <view class="modal-actions">
          <view class="modal-btn modal-btn-cancel" @click="banAgentFormVisible = false"><text>取消</text></view>
          <view class="modal-btn modal-btn-confirm" @click="submitBanAgent" :disabled="banAgentLoading"><text>{{ banAgentLoading ? '提交中...' : '确认封禁' }}</text></view>
        </view>
      </view>
    </view>

    <!-- 强制操作弹窗 -->
    <view v-if="forceActionFormVisible" class="modal-overlay" @click="forceActionFormVisible = false">
      <view class="modal-content" @click.stop>
        <text class="modal-title">{{ forceActionForm.action === 'cancel' ? '强制取消订单' : '强制完成订单' }}</text>
        <text class="modal-sub">订单 #{{ currentOrder?.id }}</text>
        <input v-model="forceActionForm.reason" class="modal-input" placeholder="操作原因（必填）" style="margin-top: 12px;" />
        <view class="modal-actions">
          <view class="modal-btn modal-btn-cancel" @click="forceActionFormVisible = false"><text>取消</text></view>
          <view class="modal-btn modal-btn-confirm" @click="submitForceAction" :disabled="forceActionLoading"><text>{{ forceActionLoading ? '提交中...' : '确认' }}</text></view>
        </view>
      </view>
    </view>
  </view>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { admin } from '@/api/index.js'

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
const loading = ref(false)
const dashboard = ref({})

// 用户管理
const users = ref([])
const userSearch = ref('')
const userPage = ref(1)
const userTotalPages = ref(1)
const banFormVisible = ref(false)
const banTargetUser = ref(null)
const banForm = ref({ reason: '' })
const banLoading = ref(false)

// Agent管理
const agents = ref([])
const agentSearch = ref('')
const agentPage = ref(1)
const agentTotalPages = ref(1)
const agentStatusFilter = ref('')
const agentStatuses = [
  { label: '全部', value: '' },
  { label: '正常', value: 'active' },
  { label: '封禁', value: 'banned' },
  { label: '待激活', value: 'pending' },
]
const banAgentFormVisible = ref(false)
const banTargetAgent = ref(null)
const banAgentForm = ref({ reason: '' })
const banAgentLoading = ref(false)

// 订单管理
const orders = ref([])
const orderStatusFilter = ref('')
const orderStatuses = [
  { label: '全部', value: '' },
  { label: '待接单', value: 'pending' },
  { label: '已接单', value: 'accepted' },
  { label: '进行中', value: 'in_progress' },
  { label: '已交付', value: 'delivered' },
  { label: '已完成', value: 'completed' },
  { label: '已取消', value: 'cancelled' },
]
const orderPage = ref(1)
const orderTotalPages = ref(1)
const forceActionFormVisible = ref(false)
const currentOrder = ref(null)
const forceActionForm = ref({ action: '', reason: '' })
const forceActionLoading = ref(false)

// 仲裁管理
const arbitrations = ref([])
const arbitrationStatusFilter = ref('pending')
const arbitrationStatuses = [
  { label: '待处理', value: 'pending' },
  { label: '已裁决', value: 'resolved' },
  { label: '全部', value: '' },
]
const resolveFormVisible = ref(false)
const currentArbitration = ref(null)
const resolveForm = ref({ resolution: 'release_agent', reason: '', refund_amount: '' })
const resolveLoading = ref(false)
const resolutionOptions = [
  { label: '放行给Agent', value: 'release_agent' },
  { label: '退款给用户', value: 'refund' },
  { label: '部分退款', value: 'partial_refund' },
  { label: '重新交付', value: 'redeliver' },
]

// 支付确认
const payments = ref([])
const paymentStatusFilter = ref('')
const paymentStatuses = [
  { label: '全部', value: '' },
  { label: '待确认', value: 'pending' },
  { label: '已支付', value: 'paid' },
  { label: '已退款', value: 'refunded' },
]
const paymentPage = ref(1)
const paymentTotalPages = ref(1)

// 提现审核
const withdraws = ref([])
const withdrawStatusFilter = ref('')
const withdrawStatuses = [
  { label: '全部', value: '' },
  { label: '待处理', value: 'pending' },
  { label: '已批准', value: 'approved' },
  { label: '已拒绝', value: 'rejected' },
]
const withdrawPage = ref(1)
const withdrawTotalPages = ref(1)

// 工具方法
function formatDate(dateStr) {
  if (!dateStr) return '-'
  try {
    const d = new Date(dateStr)
    return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
  } catch { return dateStr }
}
function getUserStatusTagClass(status) {
  const map = { active: 'tag-success', banned: 'tag-error', pending: 'tag-warning' }
  return map[status] || 'tag-default'
}
function getUserStatusText(status) {
  const map = { active: '正常', banned: '已封禁', pending: '待激活' }
  return map[status] || status || '未知'
}
function getAgentStatusTagClass(status) {
  const map = { active: 'tag-success', banned: 'tag-error', pending: 'tag-warning' }
  return map[status] || 'tag-default'
}
function getAgentStatusText(status) {
  const map = { active: '正常', banned: '已封禁', pending: '待激活' }
  return map[status] || status || '未知'
}
function getOrderStatusTagClass(status) {
  const map = { pending: 'tag-warning', accepted: 'tag-primary', in_progress: 'tag-primary', delivered: 'tag-accent', completed: 'tag-success', cancelled: 'tag-error' }
  return map[status] || 'tag-default'
}
function getOrderStatusText(status) {
  const map = { pending: '待接单', accepted: '已接单', in_progress: '进行中', delivered: '已交付', completed: '已完成', cancelled: '已取消' }
  return map[status] || status || '未知'
}
function getArbitrationStatusText(status) {
  const map = { pending: '待处理', resolved: '已裁决' }
  return map[status] || status || '未知'
}
function getPaymentStatusTagClass(status) {
  const map = { pending: 'tag-warning', paid: 'tag-success', refunded: 'tag-error' }
  return map[status] || 'tag-default'
}
function getPaymentStatusText(status) {
  const map = { pending: '待确认', paid: '已支付', refunded: '已退款' }
  return map[status] || status || '未知'
}
function getWithdrawStatusTagClass(status) {
  const map = { pending: 'tag-warning', approved: 'tag-success', rejected: 'tag-error' }
  return map[status] || 'tag-default'
}
function getWithdrawStatusText(status) {
  const map = { pending: '待处理', approved: '已批准', rejected: '已拒绝' }
  return map[status] || status || '未知'
}

// Tab切换
function switchTab(key) {
  currentTab.value = key
  if (key === 'dashboard') loadDashboard()
  else if (key === 'users') loadUsers(userPage.value)
  else if (key === 'agents') loadAgents(1)
  else if (key === 'orders') loadOrders(1)
  else if (key === 'arbitration') loadArbitration()
  else if (key === 'payments') loadPayments(1)
  else if (key === 'withdraws') loadWithdraws(1)
}

// 看板
async function loadDashboard() {
  loading.value = true
  try {
    const res = await admin.getDashboard()
    const data = res.data || res
    dashboard.value = {
      total_users: data.total_users || 0,
      total_agents: data.total_agents || 0,
      total_demands: data.total_demands || 0,
      total_orders: data.total_orders || 0,
      today_new_demands: data.today_new_demands || 0,
      today_new_orders: data.today_new_orders || 0,
      completion_rate: data.completion_rate || 0,
      avg_price: data.avg_price || 0,
      pending_arbitration: data.pending_arbitration || 0,
    }
  } catch (e) { console.error('loadDashboard error', e); uni.showToast({ title: '看板加载失败', icon: 'none' }) }
  finally { loading.value = false }
}

// 用户管理
async function loadUsers(page = 1) {
  loading.value = true
  try {
    const params = { page, page_size: 20 }
    if (userSearch.value) params.keyword = userSearch.value
    const res = await admin.getUsers(params)
    const data = res.data || res
    users.value = data.items || []
    userTotalPages.value = Math.max(1, Math.ceil((data.total || 0) / 20))
    userPage.value = page
  } catch (e) { console.error('loadUsers error', e); uni.showToast({ title: '用户列表加载失败', icon: 'none' }) }
  finally { loading.value = false }
}
function searchUsers() { loadUsers(1) }
function prevUserPage() { if (userPage.value > 1) loadUsers(userPage.value - 1) }
function nextUserPage() { if (userPage.value < userTotalPages.value) loadUsers(userPage.value + 1) }
function showBanForm(user) { banTargetUser.value = user; banForm.value = { reason: '' }; banFormVisible.value = true }
async function submitBanUser() {
  if (!banForm.value.reason) { uni.showToast({ title: '请填写封禁原因', icon: 'none' }); return }
  banLoading.value = true
  try {
    await admin.banUser(banTargetUser.value.id, { reason: banForm.value.reason })
    uni.showToast({ title: '已封禁', icon: 'success' })
    banFormVisible.value = false
    loadUsers(userPage.value)
  } catch (e) { uni.showToast({ title: e.message || '操作失败', icon: 'none' }) }
  finally { banLoading.value = false }
}
async function unbanUser(id) {
  try { await admin.unbanUser(id); uni.showToast({ title: '已解封', icon: 'success' }); loadUsers(userPage.value) }
  catch (e) { uni.showToast({ title: e.message || '操作失败', icon: 'none' }) }
}

// Agent管理
async function loadAgents(page = 1) {
  loading.value = true
  try {
    const params = { page, page_size: 20 }
    if (agentSearch.value) params.keyword = agentSearch.value
    if (agentStatusFilter.value) params.status_filter = agentStatusFilter.value
    const res = await admin.getAgents(params)
    const data = res.data || res
    agents.value = data.items || []
    agentTotalPages.value = Math.max(1, Math.ceil((data.total || 0) / 20))
    agentPage.value = page
  } catch (e) { console.error('loadAgents error', e); uni.showToast({ title: 'Agent列表加载失败', icon: 'none' }) }
  finally { loading.value = false }
}
function searchAgents() { loadAgents(1) }
function prevAgentPage() { if (agentPage.value > 1) loadAgents(agentPage.value - 1) }
function nextAgentPage() { if (agentPage.value < agentTotalPages.value) loadAgents(agentPage.value + 1) }
function showBanAgentForm(agent) { banTargetAgent.value = agent; banAgentForm.value = { reason: '' }; banAgentFormVisible.value = true }
async function submitBanAgent() {
  if (!banAgentForm.value.reason) { uni.showToast({ title: '请填写封禁原因', icon: 'none' }); return }
  banAgentLoading.value = true
  try {
    await admin.banAgent(banTargetAgent.value.id, { reason: banAgentForm.value.reason })
    uni.showToast({ title: '已封禁', icon: 'success' })
    banAgentFormVisible.value = false
    loadAgents(agentPage.value)
  } catch (e) { uni.showToast({ title: e.message || '操作失败', icon: 'none' }) }
  finally { banAgentLoading.value = false }
}
async function unbanAgent(id) {
  try { await admin.unbanAgent(id); uni.showToast({ title: '已解封', icon: 'success' }); loadAgents(agentPage.value) }
  catch (e) { uni.showToast({ title: e.message || '操作失败', icon: 'none' }) }
}

// 订单管理
async function loadOrders(page = 1) {
  loading.value = true
  try {
    const params = { page, page_size: 20 }
    if (orderStatusFilter.value) params.status_filter = orderStatusFilter.value
    const res = await admin.getOrders(params)
    const data = res.data || res
    orders.value = data.items || []
    orderTotalPages.value = Math.max(1, Math.ceil((data.total || 0) / 20))
    orderPage.value = page
  } catch (e) { console.error('loadOrders error', e); uni.showToast({ title: '订单列表加载失败', icon: 'none' }) }
  finally { loading.value = false }
}
function prevOrderPage() { if (orderPage.value > 1) loadOrders(orderPage.value - 1) }
function nextOrderPage() { if (orderPage.value < orderTotalPages.value) loadOrders(orderPage.value + 1) }
function showForceActionForm(order, action) { currentOrder.value = order; forceActionForm.value = { action, reason: '' }; forceActionFormVisible.value = true }
async function submitForceAction() {
  if (!forceActionForm.value.reason) { uni.showToast({ title: '请填写原因', icon: 'none' }); return }
  forceActionLoading.value = true
  try {
    await admin.forceOrderAction(currentOrder.value.id, { action: forceActionForm.value.action, reason: forceActionForm.value.reason })
    uni.showToast({ title: '操作成功', icon: 'success' })
    forceActionFormVisible.value = false
    loadOrders(orderPage.value)
  } catch (e) { uni.showToast({ title: e.message || '操作失败', icon: 'none' }) }
  finally { forceActionLoading.value = false }
}

// 仲裁管理
async function loadArbitration() {
  loading.value = true
  try {
    const params = {}
    if (arbitrationStatusFilter.value) params.status_filter = arbitrationStatusFilter.value
    const res = await admin.getArbitration(params)
    const data = res.data || res
    arbitrations.value = data.items || []
  } catch (e) { console.error('loadArbitration error', e); uni.showToast({ title: '仲裁列表加载失败', icon: 'none' }) }
  finally { loading.value = false }
}
function showResolveForm(arb) { currentArbitration.value = arb; resolveForm.value = { resolution: 'release_agent', reason: '', refund_amount: '' }; resolveFormVisible.value = true }
async function submitResolve() {
  if (!resolveForm.value.reason) { uni.showToast({ title: '请填写裁决理由', icon: 'none' }); return }
  resolveLoading.value = true
  try {
    const payload = { resolution: resolveForm.value.resolution, reason: resolveForm.value.reason }
    if (resolveForm.value.refund_amount) payload.refund_amount = parseFloat(resolveForm.value.refund_amount)
    await admin.resolveArbitration(currentArbitration.value.id, payload)
    uni.showToast({ title: '裁决已提交', icon: 'success' })
    resolveFormVisible.value = false
    loadArbitration()
  } catch (e) { uni.showToast({ title: e.message || '操作失败', icon: 'none' }) }
  finally { resolveLoading.value = false }
}

// 支付确认
async function loadPayments(page = 1) {
  loading.value = true
  try {
    const params = { page, page_size: 20 }
    if (paymentStatusFilter.value) params.status_filter = paymentStatusFilter.value
    const res = await admin.getPayments(params)
    const data = res.data || res
    payments.value = data.items || []
    paymentTotalPages.value = Math.max(1, Math.ceil((data.total || 0) / 20))
    paymentPage.value = page
  } catch (e) { console.error('loadPayments error', e); uni.showToast({ title: '支付列表加载失败', icon: 'none' }) }
  finally { loading.value = false }
}
function prevPaymentPage() { if (paymentPage.value > 1) loadPayments(paymentPage.value - 1) }
function nextPaymentPage() { if (paymentPage.value < paymentTotalPages.value) loadPayments(paymentPage.value + 1) }
async function confirmPayment(id) {
  try { await admin.confirmPayment(id); uni.showToast({ title: '已确认', icon: 'success' }); loadPayments(paymentPage.value) }
  catch (e) { uni.showToast({ title: e.message || '操作失败', icon: 'none' }) }
}
async function rejectPayment(id) {
  try { await admin.rejectPayment(id); uni.showToast({ title: '已拒绝', icon: 'success' }); loadPayments(paymentPage.value) }
  catch (e) { uni.showToast({ title: e.message || '操作失败', icon: 'none' }) }
}

// 提现审核
async function loadWithdraws(page = 1) {
  loading.value = true
  try {
    const params = { page, page_size: 20 }
    if (withdrawStatusFilter.value) params.status_filter = withdrawStatusFilter.value
    const res = await admin.getWithdraws ? await admin.getWithdraws(params) : { data: { items: [], total: 0 } }
    const data = res.data || res
    withdraws.value = data.items || []
    withdrawTotalPages.value = Math.max(1, Math.ceil((data.total || 0) / 20))
    withdrawPage.value = page
  } catch (e) { console.error('loadWithdraws error', e) }
  finally { loading.value = false }
}
function prevWithdrawPage() { if (withdrawPage.value > 1) loadWithdraws(withdrawPage.value - 1) }
function nextWithdrawPage() { if (withdrawPage.value < withdrawTotalPages.value) loadWithdraws(withdrawPage.value + 1) }
async function approveWithdraw(id) {
  try { await admin.approveWithdraw ? admin.approveWithdraw(id) : Promise.reject(new Error('API not found')); uni.showToast({ title: '已批准', icon: 'success' }); loadWithdraws(withdrawPage.value) }
  catch (e) { uni.showToast({ title: e.message || '操作失败', icon: 'none' }) }
}
async function rejectWithdraw(id) {
  try { await admin.rejectWithdraw ? admin.rejectWithdraw(id) : Promise.reject(new Error('API not found')); uni.showToast({ title: '已拒绝', icon: 'success' }); loadWithdraws(withdrawPage.value) }
  catch (e) { uni.showToast({ title: e.message || '操作失败', icon: 'none' }) }
}

onMounted(() => { loadDashboard() })
</script>
<style scoped>
.page-container { min-height: 100vh; background: #F5F7FA; }
.admin-page { padding-bottom: 40px; }
.admin-header { background: linear-gradient(135deg, #1D1D1F 0%, #2D2D30 100%); padding: 48px 20px 20px; color: #fff; }
.admin-title { font-size: 20px; font-weight: 600; display: block; }
.admin-subtitle { font-size: 12px; color: #A1A1AA; margin-top: 4px; display: block; }
.tab-bar { display: flex; flex-direction: row; flex-wrap: wrap; background: #fff; border-bottom: 1px solid #E5E7EB; position: sticky; top: 0; z-index: 10; }
.tab-item { padding: 12px 14px; font-size: 13px; color: #71717A; border-bottom: 2px solid transparent; transition: all 0.2s; }
.tab-item.active { color: #4F46E5; border-bottom-color: #4F46E5; }
.tab-content { padding: 16px; }
.dashboard-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
.stat-card { background: #fff; border-radius: 12px; padding: 16px; display: flex; flex-direction: column; align-items: center; }
.stat-card .stat-num { font-size: 24px; font-weight: 700; color: #1D1D1F; }
.stat-card .stat-label { font-size: 12px; color: #71717A; margin-top: 4px; }
.stat-primary { border-left: 3px solid #4F46E5; }
.stat-accent { border-left: 3px solid #7C3AED; }
.stat-success { border-left: 3px solid #059669; }
.stat-warning { border-left: 3px solid #EA580C; }
.search-bar { display: flex; gap: 8px; margin-bottom: 12px; }
.search-input { flex: 1; background: #fff; border-radius: 8px; padding: 10px 14px; font-size: 14px; border: 1px solid #E5E7EB; }
.search-btn { background: #4F46E5; color: #fff; border-radius: 8px; padding: 10px 16px; font-size: 14px; }
.filter-bar { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
.filter-chip { background: #fff; border: 1px solid #E5E7EB; border-radius: 20px; padding: 6px 14px; font-size: 12px; color: #71717A; }
.filter-chip.active { background: #4F46E5; color: #fff; border-color: #4F46E5; }
.list-container { display: flex; flex-direction: column; gap: 10px; }
.list-item { background: #fff; border-radius: 12px; padding: 14px; display: flex; justify-content: space-between; align-items: center; }
.item-info { flex: 1; }
.item-title { font-size: 14px; font-weight: 600; color: #1D1D1F; display: block; }
.item-sub { font-size: 12px; color: #71717A; margin-top: 2px; display: block; }
.item-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
.item-date { font-size: 11px; color: #A1A1AA; margin-top: 4px; display: block; }
.tag { font-size: 11px; border-radius: 4px; padding: 2px 6px; }
.tag-default { background: #F3F4F6; color: #71717A; }
.tag-primary { background: #EEF2FF; color: #4F46E5; }
.tag-success { background: #D1FAE5; color: #059669; }
.tag-warning { background: #FEF3C7; color: #EA580C; }
.tag-error { background: #FEE2E2; color: #DC2626; }
.tag-accent { background: #F3E8FF; color: #7C3AED; }
.item-actions { display: flex; gap: 8px; margin-left: 12px; }
.action-btn { padding: 6px 12px; border-radius: 6px; font-size: 12px; }
.action-primary { background: #4F46E5; color: #fff; }
.action-success { background: #059669; color: #fff; }
.action-danger { background: #DC2626; color: #fff; }
.action-warning { background: #EA580C; color: #fff; }
.empty-state, .loading-state { text-align: center; padding: 40px; color: #A1A1AA; font-size: 14px; }
.pagination { display: flex; justify-content: center; align-items: center; gap: 16px; margin-top: 16px; }
.page-btn { background: #fff; border: 1px solid #E5E7EB; border-radius: 8px; padding: 6px 16px; font-size: 13px; }
.page-info { font-size: 13px; color: #71717A; }
.modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 100; display: flex; align-items: center; justify-content: center; }
.modal-content { background: #fff; border-radius: 16px; padding: 24px; width: 90%; max-width: 400px; }
.modal-title { font-size: 16px; font-weight: 600; display: block; margin-bottom: 8px; }
.modal-sub { font-size: 13px; color: #71717A; display: block; margin-bottom: 8px; }
.modal-label { font-size: 13px; color: #1D1D1F; display: block; margin-bottom: 4px; }
.modal-input { width: 100%; border: 1px solid #E5E7EB; border-radius: 8px; padding: 10px; font-size: 14px; box-sizing: border-box; margin-top: 4px; }
.modal-textarea { width: 100%; border: 1px solid #E5E7EB; border-radius: 8px; padding: 12px; font-size: 14px; resize: none; margin-top: 4px; }
.radio-group { display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0; }
.radio-item { background: #F3F4F6; border: 1px solid #E5E7EB; border-radius: 8px; padding: 8px 14px; font-size: 13px; color: #71717A; }
.radio-item.active { background: #EEF2FF; color: #4F46E5; border-color: #4F46E5; }
.modal-actions { display: flex; gap: 12px; margin-top: 16px; }
.modal-btn { flex: 1; text-align: center; padding: 12px; border-radius: 8px; font-size: 14px; }
.modal-btn-cancel { background: #F3F4F6; color: #71717A; }
.modal-btn-confirm { background: #4F46E5; color: #fff; }
.modal-btn[disabled] { opacity: 0.6; }
.dispute-item { border-left: 3px solid #EA580C; }
</style>
