<script setup>
import { onLaunch, onShow, onHide } from '@dcloudio/uni-app'

onLaunch(() => {
  console.log('App Launch')
})
onShow(() => {
  console.log('App Show')
})
onHide(() => {
  console.log('App Hide')
})
</script>

<style>
/* 全局样式 — 风格A 简洁专业 */
page {
  background-color: #F5F7FA;
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", sans-serif;
  color: #1D1D1F;
  -webkit-font-smoothing: antialiased;
}

view, text, image, scroll-view {
  box-sizing: border-box;
}

/* 页面容器 */
.page-container {
  padding-bottom: 60px; /* 底部导航高度 */
  min-height: 100vh;
}

/* 通用工具类 */
.flex-row {
  display: flex;
  flex-direction: row;
  align-items: center;
}

.flex-between {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
}

.text-ellipsis {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 主色 */
.color-primary { color: #4F46E5; }
.bg-primary { background-color: #4F46E5; }
.bg-primary-light { background-color: #EEF2FF; }
.color-secondary { color: #71717A; }
.color-muted { color: #A1A1AA; }
.color-success { color: #059669; }
.color-warning { color: #EA580C; }
.color-error { color: #DC2626; }
</style>
