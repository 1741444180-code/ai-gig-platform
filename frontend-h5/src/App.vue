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
}

view {
  box-sizing: border-box;
}
</style>