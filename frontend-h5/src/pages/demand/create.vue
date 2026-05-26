<template>
  <view class="create-demand-page">
    <view class="page-title">发布需求</view>
    <view class="form-card">
      <view class="form-item">
        <view class="form-label">需求标题 <text class="required">*</text></view>
        <input v-model="form.title" class="form-input" placeholder="简要描述你的需求" maxlength="100" />
      </view>
      <view class="form-item">
        <view class="form-label">需求分类</view>
        <picker :range="categories" range-key="label" @change="onCategoryChange">
          <view class="form-input">{{ form.category_label || '请选择分类' }}</view>
        </picker>
      </view>
      <view class="form-item">
        <view class="form-label">预算范围（元）<text class="required">*</text></view>
        <input v-model="form.budget" class="form-input" type="digit" placeholder="如：100" />
      </view>
      <view class="form-item">
        <view class="form-label">详细描述</view>
        <textarea v-model="form.description" class="form-textarea" placeholder="详细描述你的需求，越详细越好" maxlength="1000" />
      </view>
      <view class="form-item">
        <button class="btn-submit" :loading="submitting" @click="submitDemand">发布需求</button>
      </view>
    </view>
  </view>
</template>

<script>
import { demands } from '@/api/index.js'

export default {
  data() {
    return {
      submitting: false,
      categories: [
        { label: '文案创作', value: 'text' },
        { label: '图片处理', value: 'image' },
        { label: '视频制作', value: 'video' },
        { label: '软件开发', value: 'development' },
        { label: '数据处理', value: 'data' },
        { label: '翻译服务', value: 'translation' },
        { label: '其他', value: 'other' },
      ],
      form: {
        title: '',
        category: '',
        category_label: '',
        budget: '',
        description: '',
      },
    }
  },
  methods: {
    onCategoryChange(e) {
      const idx = e.detail.value
      this.form.category = this.categories[idx].value
      this.form.category_label = this.categories[idx].label
    },
    async submitDemand() {
      if (!this.form.title.trim()) {
        uni.showToast({ title: '请填写标题', icon: 'none' })
        return
      }
      if (!this.form.budget || isNaN(Number(this.form.budget))) {
        uni.showToast({ title: '请填写有效预算', icon: 'none' })
        return
      }
      this.submitting = true
      try {
        await demands.create({
          title: this.form.title,
          category: this.form.category || 'other',
          budget: Number(this.form.budget),
          description: this.form.description,
        })
        uni.showToast({ title: '发布成功', icon: 'success' })
        setTimeout(() => uni.switchTab({ url: '/pages/orders/list' }), 1500)
      } catch (e) {
        uni.showToast({ title: e.message || '发布失败', icon: 'none' })
      } finally {
        this.submitting = false
      }
    },
  },
}
</script>

<style scoped>
.create-demand-page {
  min-height: 100vh;
  background: #f5f5f5;
  padding: 20rpx;
}

.page-title {
  font-size: 40rpx;
  font-weight: bold;
  color: #333;
  padding: 20rpx 10rpx 30rpx;
}

.form-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 30rpx;
}

.form-item {
  margin-bottom: 30rpx;
}

.form-label {
  font-size: 28rpx;
  color: #333;
  margin-bottom: 16rpx;
  font-weight: 500;
}

.required {
  color: #ff4d4f;
}

.form-input {
  border: 1px solid #e5e5e5;
  border-radius: 12rpx;
  padding: 20rpx 24rpx;
  font-size: 30rpx;
  background: #fafafa;
}

.form-textarea {
  border: 1px solid #e5e5e5;
  border-radius: 12rpx;
  padding: 20rpx 24rpx;
  font-size: 30rpx;
  background: #fafafa;
  width: 100%;
  box-sizing: border-box;
  min-height: 200rpx;
  resize: none;
}

.btn-submit {
  background: #007aff;
  color: #fff;
  border-radius: 40rpx;
  height: 88rpx;
  line-height: 88rpx;
  font-size: 32rpx;
}
</style>