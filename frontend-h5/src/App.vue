<template>
  <view id="app"></view>
</template>

<script>
export default {
  onLaunch: function () {
    console.log('AIHub App Launch')
  },
  onShow: function () {
    console.log('AIHub App Show')
  },
  onHide: function () {
    console.log('AIHub App Hide')
  },
}
</script>

<style>
/* 全局公共样式 */
page {
  background: #f5f5f5;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  font-size: 28rpx;
}

view {
  box-sizing: border-box;
}

/* 全局响应式容器 */
.container {
  max-width: 1200rpx;
  margin: 0 auto;
}

/* 大屏幕适配 */
@media screen and (min-width: 768px) {
  page {
    font-size: 32rpx;
  }
}
</style>