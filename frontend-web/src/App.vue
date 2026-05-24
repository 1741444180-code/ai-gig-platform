<template>
  <div id="app">
    <router-view />
  </div>
</template>

<script>
export default {
  onLaunch() {
    console.log('App launched');
  },
  onShow() {
    console.log('App show');
  },
  onHide() {
    console.log('App hide');
  }
};
</script>

<style>
page {
  background-color: #F5F7FA;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  font-size: 14px;
  color: #333;
}
</style>
