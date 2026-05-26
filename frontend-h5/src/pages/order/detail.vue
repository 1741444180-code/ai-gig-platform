<template>
  <view class="order-container" v-if="order">
    <!-- 订单状态 -->
    <view class="status-card">
      <text class="status-text">{{ order.status_text || order.status }}</text>
      <text class="status-desc">{{ statusDesc }}</text>
      <view v-if="countdownText" class="countdown">
        <text class="countdown-label">剩余时间：</text>
        <text class="countdown-value">{{ countdownText }}</text>
      </view>
    </view>

    <!-- 时间线 -->
    <view class="section">
      <text class="section-title">订单进度</text>
      <view class="timeline">
        <view
          v-for="(event, idx) in timeline"
          :key="idx"
          :class="['timeline-item', { done: event.done }]"
        >
          <view class="timeline-dot"></view>
          <view class="timeline-content">
            <text class="timeline-title">{{ event.title }}</text>
            <text class="timeline-time">{{ event.time }}</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 交付物 -->
    <view class="section">
      <text class="section-title">交付物</text>
      <view v-if="!order.delivery" class="empty-delivery">
        <text>暂无交付内容</text>
      </view>
      <view v-else>
        <text v-if="order.delivery.text" class="delivery-text">{{ order.delivery.text }}</text>
        <image
          v-if="order.delivery.images"
          v-for="(img, i) in order.delivery.images"
          :key="i"
          :src="img"
          class="delivery-img"
          mode="widthFix"
        />
      </view>
    </view>

    <!-- 关联需求 -->
    <view class="section">
      <text class="section-title">关联需求</text>
      <view class="demand-link" @click="goDemand(order.demand_id)">
        <text class="demand-title">{{ order.demand_title || '查看需求详情' }}</text>
        <text class="arrow">›</text>
      </view>
    </view>

    <!-- 底部操作 -->
    <view class="bottom-bar" v-if="showActions">
      <button class="btn-reject" @click="showRejectModal = true">拒绝验收</button>
      <button class="btn-accept" @click="doAccept">验收通过</button>
    </view>

    <!-- 拒绝弹窗 -->
    <uni-popup v-if="showRejectModal" type="center" @close="showRejectModal = false">
      <view class="reject-modal">
        <text class="modal-title">拒绝原因</text>
        <textarea v-model="rejectReason" class="reject-input" placeholder="请输入拒绝原因" />
        <view class="modal-btns">
          <button @click="showRejectModal = false">取消</button>
          <button class="btn-confirm-reject" @click="doReject">确认拒绝</button>
        </view>
      </view>
    </uni-popup>
  </view>

  <view v-else class="loading-page">
    <text>加载中...</text>
  </view>
</template>

<script>
import { orders } from '@/api/index.js'

export default {
  data() {
    return {
      id: null,
      order: null,
      timeline: [],
      countdownText: '',
      timer: null,
      showRejectModal: false,
      rejectReason: '',
    }
  },
  computed: {
    statusDesc() {
      const map = {
        pending: '等待Agent接单',
        accepted: 'Agent已接单，开发中',
        delivering: '交付中，等待验收',
        completed: '已验收完成',
        cancelled: '已取消',
        rejected: '验收未通过',
      }
      return map[this.order?.status] || ''
    },
    showActions() {
      return this.order?.status === 'delivering'
    },
  },
  onLoad(query) {
    if (query.id) {
      this.id = query.id
      this.loadDetail()
    }
  },
  onUnload() {
    if (this.timer) clearInterval(this.timer)
  },
  methods: {
    async loadDetail() {
      try {
        uni.showLoading({ title: '加载中...' })
        const [orderRes, timelineRes] = await Promise.all([
          orders.get(this.id),
          orders.getTimeline(this.id).catch(() => []),
        ])
        uni.hideLoading()
        this.order = orderRes
        this.timeline = this.buildTimeline(timelineRes)
        if (orderRes.deadline) this.startCountdown(orderRes.deadline)
      } catch (e) {
        uni.hideLoading()
        uni.showToast({ title: e.message || '加载失败', icon: 'none' })
      }
    },

    buildTimeline(events) {
      if (!Array.isArray(events)) return []
      return events.map(e => ({
        title: e.title || e.event,
        time: e.created_at ? this.formatTime(e.created_at) : '',
        done: true,
      }))
    },

    startCountdown(deadline) {
      const end = new Date(deadline).getTime()
      const update = () => {
        const now = Date.now()
        const diff = end - now
        if (diff <= 0) {
          this.countdownText = '已超时'
          return
        }
        const h = Math.floor(diff / 3600000)
        const m = Math.floor((diff % 3600000) / 60000)
        const s = Math.floor((diff % 60000) / 1000)
        this.countdownText = `${h}小时${m.toString().padStart(2, '0')}分${s.toString().padStart(2, '0')}秒`
      }
      update()
      this.timer = setInterval(update, 1000)
    },

    formatTime(ts) {
      if (!ts) return ''
      const d = new Date(ts)
      return `${d.getFullYear()}-${(d.getMonth() + 1).toString().padStart(2, '0')}-${d.getDate().toString().padStart(2, '0')} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
    },

    async doAccept() {
      try {
        uni.showLoading({ title: '验收中...' })
        await orders.acceptDelivery(this.id)
        uni.hideLoading()
        uni.showToast({ title: '验收通过', icon: 'success' })
        setTimeout(() => uni.navigateBack(), 1500)
      } catch (e) {
        uni.hideLoading()
        uni.showToast({ title: e.message || '验收失败', icon: 'none' })
      }
    },

    async doReject() {
      if (!this.rejectReason.trim()) {
        uni.showToast({ title: '请输入拒绝原因', icon: 'none' })
        return
      }
      try {
        uni.showLoading({ title: '提交中...' })
        await orders.rejectDelivery(this.id, this.rejectReason)
        uni.hideLoading()
        uni.showToast({ title: '已提交', icon: 'success' })
        this.showRejectModal = false
        setTimeout(() => uni.navigateBack(), 1500)
      } catch (e) {
        uni.hideLoading()
        uni.showToast({ title: e.message || '提交失败', icon: 'none' })
      }
    },

    goDemand(id) {
      uni.navigateTo({ url: `/pages/demand/detail?id=${id}` })
    },
  },
}
</script>

<style scoped>
.order-container {
  padding: 20rpx;
  padding-bottom: 140rpx;
  background: #f5f5f5;
  min-height: 100vh;
}
.status-card {
  background: linear-gradient(135deg, #007aff, #0056cc);
  border-radius: 16rpx;
  padding: 40rpx;
  margin-bottom: 20rpx;
  color: #fff;
}
.status-text {
  display: block;
  font-size: 40rpx;
  font-weight: bold;
  margin-bottom: 12rpx;
}
.status-desc {
  display: block;
  font-size: 28rpx;
  opacity: 0.9;
}
.countdown {
  margin-top: 20rpx;
  background: rgba(255,255,255,0.2);
  border-radius: 8rpx;
  padding: 16rpx 24rpx;
  display: inline-block;
}
.countdown-label {
  font-size: 24rpx;
  opacity: 0.8;
}
.countdown-value {
  font-size: 28rpx;
  font-weight: bold;
}
.section {
  background: #fff;
  border-radius: 12rpx;
  padding: 30rpx;
  margin-bottom: 20rpx;
}
.section-title {
  display: block;
  font-size: 30rpx;
  font-weight: bold;
  color: #333;
  margin-bottom: 24rpx;
}
.timeline {}
.timeline-item {
  display: flex;
  align-items: flex-start;
  margin-bottom: 24rpx;
  position: relative;
}
.timeline-item:not(:last-child)::before {
  content: '';
  position: absolute;
  left: 16rpx;
  top: 40rpx;
  bottom: -24rpx;
  width: 2rpx;
  background: #ddd;
}
.timeline-item.done .timeline-dot {
  background: #52c41a;
}
.timeline-dot {
  width: 32rpx;
  height: 32rpx;
  border-radius: 50%;
  background: #ddd;
  flex-shrink: 0;
  margin-right: 20rpx;
  margin-top: 4rpx;
}
.timeline-content {}
.timeline-title {
  display: block;
  font-size: 28rpx;
  color: #333;
  margin-bottom: 8rpx;
}
.timeline-time {
  display: block;
  font-size: 24rpx;
  color: #999;
}
.empty-delivery {
  text-align: center;
  color: #999;
  font-size: 28rpx;
  padding: 40rpx;
}
.delivery-text {
  display: block;
  font-size: 28rpx;
  color: #666;
  line-height: 1.8;
  margin-bottom: 20rpx;
}
.delivery-img {
  width: 100%;
  border-radius: 8rpx;
  margin-bottom: 16rpx;
}
.demand-link {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f8f8f8;
  border-radius: 8rpx;
  padding: 24rpx;
}
.demand-title {
  font-size: 28rpx;
  color: #007aff;
}
.arrow {
  font-size: 40rpx;
  color: #999;
}
.bottom-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  gap: 20rpx;
  padding: 20rpx 40rpx;
  background: #fff;
  border-top: 1px solid #eee;
}
.btn-reject,
.btn-accept {
  flex: 1;
  height: 96rpx;
  line-height: 96rpx;
  border-radius: 48rpx;
  font-size: 32rpx;
  font-weight: bold;
  border: none;
}
.btn-reject {
  background: #fff;
  color: #dd524d;
  border: 2rpx solid #dd524d;
}
.btn-accept {
  background: #52c41a;
  color: #fff;
}
.loading-page {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  color: #999;
}
.reject-modal {
  background: #fff;
  border-radius: 16rpx;
  padding: 40rpx;
  width: 600rpx;
}
.modal-title {
  display: block;
  font-size: 34rpx;
  font-weight: bold;
  color: #333;
  text-align: center;
  margin-bottom: 30rpx;
}
.reject-input {
  width: 100%;
  height: 200rpx;
  background: #f8f8f8;
  border-radius: 8rpx;
  padding: 24rpx;
  font-size: 28rpx;
  box-sizing: border-box;
  margin-bottom: 30rpx;
}
.modal-btns {
  display: flex;
  gap: 20rpx;
}
.modal-btns button {
  flex: 1;
  height: 88rpx;
  line-height: 88rpx;
  border-radius: 44rpx;
  font-size: 30rpx;
  border: none;
  background: #f5f5f5;
  color: #666;
}
.modal-btns .btn-confirm-reject {
  background: #dd524d;
  color: #fff;
}
</style>