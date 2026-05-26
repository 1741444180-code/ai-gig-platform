<template>
  <view class="profile-page">
    <!-- 用户信息卡片 -->
    <view class="user-card">
      <view class="avatar">{{ userInfo.nickname?.[0] || userInfo.phone?.[0] || 'U' }}</view>
      <view class="user-info">
        <view class="nickname">{{ userInfo.nickname || userInfo.phone || '未登录' }}</view>
        <view class="role-tag" v-if="userInfo.role === 'admin'">管理员</view>
      </view>
    </view>

    <!-- 菜单列表 -->
    <view class="menu-list">
      <view class="menu-item" @click="goAgentDashboard">
        <text class="menu-icon">🤖</text>
        <text class="menu-label">Agent工作台</text>
        <text class="menu-arrow">&gt;</text>
      </view>
      <view class="menu-item" @click="goCreateDemand">
        <text class="menu-icon">📝</text>
        <text class="menu-label">发需求</text>
        <text class="menu-arrow">&gt;</text>
      </view>
      <view class="menu-item" @click="goOrderList">
        <text class="menu-icon">📋</text>
        <text class="menu-label">我的订单</text>
        <text class="menu-arrow">&gt;</text>
      </view>
      <view class="menu-item" @click="goAdmin" v-if="userInfo.role === 'admin'">
        <text class="menu-icon">⚙️</text>
        <text class="menu-label">管理后台</text>
        <text class="menu-arrow">&gt;</text>
      </view>
    </view>

    <!-- 退出登录 -->
    <view class="logout-bar">
      <button class="btn-logout" @click="logout">退出登录</button>
    </view>
  </view>
</template>

<script>
export default {
  data() {
    return {
      userInfo: {},
    }
  },
  onShow() {
    this.userInfo = uni.getStorageSync('user_info') || {}
  },
  methods: {
    goAgentDashboard() {
      uni.switchTab({ url: '/pages/agent/dashboard' })
    },
    goCreateDemand() {
      uni.navigateTo({ url: '/pages/demand/create' })
    },
    goOrderList() {
      uni.switchTab({ url: '/pages/orders/list' })
    },
    goAdmin() {
      uni.navigateTo({ url: '/pages/admin/admin' })
    },
    logout() {
      uni.showModal({
        title: '确认退出',
        content: '确定要退出登录吗？',
        success: (m) => {
          if (m.confirm) {
            uni.removeStorageSync('access_token')
            uni.removeStorageSync('user_info')
            uni.reLaunch({ url: '/pages/login/login' })
          }
        },
      })
    },
  },
}
</script>

<style scoped>
.profile-page {
  min-height: 100vh;
  background: #f5f5f5;
  padding: 20rpx;
}

.user-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 40rpx 30rpx;
  display: flex;
  align-items: center;
  gap: 30rpx;
  margin-bottom: 20rpx;
}

.avatar {
  width: 100rpx;
  height: 100rpx;
  border-radius: 50%;
  background: #007aff;
  color: #fff;
  font-size: 48rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
}

.user-info {
  flex: 1;
}

.nickname {
  font-size: 36rpx;
  font-weight: bold;
  color: #333;
  margin-bottom: 10rpx;
}

.role-tag {
  display: inline-block;
  background: #fffbe6;
  color: #faad14;
  font-size: 24rpx;
  padding: 4rpx 16rpx;
  border-radius: 20rpx;
}

.menu-list {
  background: #fff;
  border-radius: 16rpx;
  overflow: hidden;
}

.menu-item {
  display: flex;
  align-items: center;
  padding: 30rpx;
  border-bottom: 1px solid #f0f0f0;
  min-height: 100rpx;
}

@media screen and (min-width: 768px) {
  .menu-item {
    padding: 40rpx 30rpx;
  }
}

.menu-item:last-child {
  border-bottom: none;
}

.menu-icon {
  font-size: 40rpx;
  margin-right: 20rpx;
}

.menu-label {
  flex: 1;
  font-size: 30rpx;
  color: #333;
}

.menu-arrow {
  font-size: 28rpx;
  color: #ccc;
}

.logout-bar {
  margin-top: 40rpx;
  display: flex;
  justify-content: center;
}

.btn-logout {
  background: #fff;
  color: #ff4d4f;
  border: 1px solid #ff4d4f;
  border-radius: 40rpx;
  height: 80rpx;
  line-height: 80rpx;
  font-size: 30rpx;
  padding: 0 80rpx;
}
</style>