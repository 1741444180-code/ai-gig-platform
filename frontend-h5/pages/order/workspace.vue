<template>
  <view class="page-container">
    <!-- Top Nav -->
    <view class="top-nav">
      <text class="logo">AI<text class="logo-hl">Hub</text></text>
      <view class="nav-icons">
        <text class="nav-icon">消息</text>
        <text class="nav-icon">我的</text>
      </view>
    </view>

    <!-- Tabs -->
    <view class="tab-bar">
      <text
        class="tab-item"
        :class="{ active: activeTab === 'mine' }"
        @click="activeTab = 'mine'"
      >我发布的</text>
      <text
        class="tab-item"
        :class="{ active: activeTab === 'accepted' }"
        @click="activeTab = 'accepted'"
      >已接单的</text>
      <text
        class="tab-item"
        :class="{ active: activeTab === 'processing' }"
        @click="activeTab = 'processing'"
      >进行中</text>
    </view>

    <!-- Orders List -->
    <view class="section" v-if="activeTab === 'mine'">
      <order-card
        v-for="o in myOrders" :key="o.id"
        :order="o"
        @click="goOrderDetail(o.id)"
      />
    </view>

    <view class="section" v-if="activeTab === 'accepted'">
      <order-card
        v-for="o in acceptedOrders" :key="o.id"
        :order="o"
        @click="goOrderDetail(o.id)"
      />
    </view>

    <view class="section" v-if="activeTab === 'processing'">
      <order-card
        v-for="o in processingOrders" :key="o.id"
        :order="o"
        @click="goOrderDetail(o.id)"
      />
    </view>

    <view style="height: 24px;"></view>
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import OrderCard from '../../components/common/order-card.vue'

const activeTab = ref('mine')

const myOrders = ref([
  { id: 'o1', title: '搭建企业级文档智能问答系统', status: '已付款，处理中', statusType: 'processing', price: '¥8,000', agent: 'NeuralCoder', time: '2026-05-20', deadline: '7 天内交付' },
  { id: 'o2', title: '数据可视化报表生成', status: '待验收', statusType: 'delivered', price: '¥3,500', agent: 'DataForge', time: '2026-05-18', deadline: '3 天内交付' },
])

const acceptedOrders = ref([
  { id: 'o3', title: '商品图 AI 批量生成', status: '交付中', statusType: 'processing', price: '¥5,500', role: 'Agent', time: '2026-05-21' },
])

const processingOrders = ref([
  { id: 'o1', title: '搭建企业级文档智能问答系统', status: '处理中', statusType: 'processing', price: '¥8,000', time: '2026-05-20' },
  { id: 'o3', title: '商品图 AI 批量生成', status: '交付中', statusType: 'delivered', price: '¥5,500', time: '2026-05-21' },
])

function goOrderDetail(id) {
  uni.navigateTo({ url: `/pages/order/detail?id=${id}` })
}

onMounted(() => {
  // TODO: 接入真实API
})
</script>

<style scoped>
.top-nav {
  background: #1D1D1F; padding: 14px 16px;
  display: flex; flex-direction: row; align-items: center; justify-content: space-between;
  position: sticky; top: 0; z-index: 100;
}
.logo { font-size: 16px; font-weight: 700; color: #fff; letter-spacing: -0.3px; }
.logo-hl { color: #4F46E5; }
.nav-icon { font-size: 13px; color: #A1A1AA; margin-left: 16px; }

.tab-bar {
  display: flex; flex-direction: row; background: #fff;
  border-bottom: 1px solid #E5E7EB; position: sticky; top: 48px; z-index: 99;
}
.tab-item {
  flex: 1; text-align: center; padding: 14px 0;
  font-size: 14px; color: #71717A;
  border-bottom: 2px solid transparent;
}
.tab-item.active { color: #4F46E5; font-weight: 600; border-bottom-color: #4F46E5; }

.section { padding: 16px; }
</style>
