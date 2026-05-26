<template>
  <view class="publish-container">
    <view class="form">
      <!-- 标题 -->
      <view class="form-item">
        <text class="label">需求标题 <text class="required">*</text></text>
        <input
          v-model="form.title"
          maxlength="50"
          placeholder="简明扼要，5-50字"
          class="input"
        />
        <text class="char-count">{{ form.title.length }}/50</text>
      </view>

      <!-- 描述 -->
      <view class="form-item">
        <text class="label">需求描述 <text class="required">*</text></text>
        <textarea
          v-model="form.description"
          maxlength="500"
          placeholder="详细描述您的需求，10-500字"
          class="textarea"
        />
        <text class="char-count">{{ form.description.length }}/500</text>
      </view>

      <!-- 分类 -->
      <view class="form-item">
        <text class="label">需求分类 <text class="required">*</text></text>
        <picker
          :value="categoryIndex"
          :range="categoryOptions"
          range-key="label"
          @change="onCategoryChange"
        >
          <view class="picker-display">
            <text>{{ categoryOptions[categoryIndex]?.label || '请选择分类' }}</text>
            <text class="arrow">›</text>
          </view>
        </picker>
      </view>

      <!-- 预算 -->
      <view class="form-item">
        <text class="label">预算金额（元）<text class="required">*</text></text>
        <input
          v-model="form.budget"
          type="digit"
          placeholder="请输入预算金额"
          class="input"
        />
      </view>

      <!-- 截止日期 -->
      <view class="form-item">
        <text class="label">截止日期 <text class="required">*</text></text>
        <picker
          mode="date"
          :value="form.deadline"
          :start="minDate"
          @change="onDeadlineChange"
        >
          <view class="picker-display">
            <text>{{ form.deadline || '请选择截止日期' }}</text>
            <text class="arrow">›</text>
          </view>
        </picker>
      </view>

      <!-- 附件上传 -->
      <view class="form-item">
        <text class="label">附件图片（可选）</text>
        <view class="upload-area" @click="chooseImage">
          <text v-if="!form.attachment" class="upload-tip">+ 点击上传图片</text>
          <image
            v-else
            :src="form.attachment"
            class="preview-img"
            mode="aspectFill"
          />
        </view>
        <view v-if="form.attachment" class="clear-img" @click="form.attachment = ''">
          清除图片
        </view>
      </view>

      <button class="submit-btn" @click="doSubmit">提交发布</button>
    </view>
  </view>
</template>

<script>
import { demands } from '@/api/index.js'

const CATEGORIES = [
  { label: '文案', value: 'copywriting' },
  { label: '图片', value: 'image' },
  { label: '视频', value: 'video' },
  { label: '开发', value: 'development' },
  { label: '其他', value: 'other' },
]

export default {
  data() {
    const today = new Date()
    const minDate = today.toISOString().split('T')[0]
    return {
      form: {
        title: '',
        description: '',
        category: '',
        budget: '',
        deadline: '',
        attachment: '',
      },
      categoryOptions: CATEGORIES,
      categoryIndex: 0,
      minDate,
    }
  },
  methods: {
    onCategoryChange(e) {
      this.categoryIndex = e.detail.value
      this.form.category = CATEGORIES[this.categoryIndex].value
    },

    onDeadlineChange(e) {
      this.form.deadline = e.detail.value
    },

    chooseImage() {
      uni.chooseImage({
        count: 1,
        sizeType: ['compressed'],
        sourceType: ['album', 'camera'],
        success: (res) => {
          this.form.attachment = res.tempFilePaths[0]
        },
      })
    },

    validate() {
      if (!this.form.title || this.form.title.length < 5) {
        uni.showToast({ title: '标题需5-50字', icon: 'none' })
        return false
      }
      if (!this.form.description || this.form.description.length < 10) {
        uni.showToast({ title: '描述需10-500字', icon: 'none' })
        return false
      }
      if (!this.form.category) {
        uni.showToast({ title: '请选择分类', icon: 'none' })
        return false
      }
      if (!this.form.budget || isNaN(Number(this.form.budget)) || Number(this.form.budget) <= 0) {
        uni.showToast({ title: '请输入有效预算', icon: 'none' })
        return false
      }
      if (!this.form.deadline) {
        uni.showToast({ title: '请选择截止日期', icon: 'none' })
        return false
      }
      return true
    },

    async doSubmit() {
      if (!this.validate()) return
      try {
        uni.showLoading({ title: '发布中...' })
        const res = await demands.create({
          title: this.form.title,
          description: this.form.description,
          category: this.form.category,
          budget: Number(this.form.budget),
          deadline: this.form.deadline,
          attachment_url: this.form.attachment,
        })
        uni.hideLoading()
        uni.showToast({ title: '发布成功', icon: 'success' })
        setTimeout(() => {
          uni.navigateTo({ url: `/pages/demand/detail?id=${res.id}` })
        }, 1500)
      } catch (e) {
        uni.hideLoading()
        uni.showToast({ title: e.message || '发布失败', icon: 'none' })
      }
    },
  },
}
</script>

<style scoped>
.publish-container {
  padding: 30rpx;
  background: #f5f5f5;
  min-height: 100vh;
}
.form {
  background: #fff;
  border-radius: 16rpx;
  padding: 40rpx;
}
.form-item {
  margin-bottom: 40rpx;
  position: relative;
}
.label {
  display: block;
  font-size: 28rpx;
  color: #333;
  margin-bottom: 16rpx;
  font-weight: 500;
}
.required {
  color: #ff4d4f;
}
.input {
  height: 88rpx;
  background: #f8f8f8;
  border-radius: 8rpx;
  padding: 0 24rpx;
  font-size: 30rpx;
}
.textarea {
  background: #f8f8f8;
  border-radius: 8rpx;
  padding: 24rpx;
  font-size: 30rpx;
  height: 200rpx;
  width: 100%;
  box-sizing: border-box;
}
.char-count {
  position: absolute;
  right: 0;
  top: 0;
  font-size: 24rpx;
  color: #999;
}
.picker-display {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 88rpx;
  background: #f8f8f8;
  border-radius: 8rpx;
  padding: 0 24rpx;
  font-size: 30rpx;
  color: #333;
}
.arrow {
  color: #999;
  font-size: 40rpx;
}
.upload-area {
  border: 2rpx dashed #ccc;
  border-radius: 8rpx;
  height: 200rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}
.upload-tip {
  color: #999;
  font-size: 28rpx;
}
.preview-img {
  width: 200rpx;
  height: 200rpx;
  border-radius: 8rpx;
}
.clear-img {
  font-size: 24rpx;
  color: #007aff;
  text-align: right;
  margin-top: 10rpx;
}
.submit-btn {
  width: 100%;
  height: 96rpx;
  line-height: 96rpx;
  background: #007aff;
  color: #fff;
  font-size: 34rpx;
  font-weight: bold;
  border-radius: 48rpx;
  border: none;
  margin-top: 20rpx;
}
</style>