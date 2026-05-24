// API 基础配置
const BASE_URL = '/api/v1';

/**
 * 封装 uni.request
 */
function request({ url, method = 'GET', data = {}, header = {} }) {
  const token = uni.getStorageSync('token') || '';
  return new Promise((resolve, reject) => {
    uni.request({
      url: BASE_URL + url,
      method,
      data,
      header: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...header
      },
      success(res) {
        if (res.statusCode === 200) {
          resolve(res.data);
        } else if (res.statusCode === 401) {
          uni.removeStorageSync('token');
          uni.showToast({ title: '请先登录', icon: 'none' });
          reject(new Error('Unauthorized'));
        } else {
          const msg = res.data?.message || '请求失败';
          uni.showToast({ title: msg, icon: 'none' });
          reject(new Error(msg));
        }
      },
      fail(err) {
        uni.showToast({ title: '网络错误', icon: 'none' });
        reject(err);
      }
    });
  });
}

/**
 * 获取当前用户token（mock 用）
 */
function getToken() {
  return uni.getStorageSync('token') || 'demo-token-123';
}

export default {
  BASE_URL,
  request,
  getToken
};
