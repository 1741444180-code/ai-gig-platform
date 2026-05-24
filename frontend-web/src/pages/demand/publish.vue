<template>
  <view class="publish-page">
    <form @submit="onSubmit">
      <!-- 标题 -->
      <view class="form-item">
        <text class="label">需求标题 <text class="required">*</text></text>
        <input
          class="input"
          v-model="form.title"
          placeholder="请输入需求标题（最多50字）"
          maxlength="50"
        />
      </view>

      <!-- 描述 -->
      <view class="form-item">
        <text class="label">需求描述 <text class="required">*</text></text>
        <textarea
          class="textarea"
          v-model="form.description"
          placeholder="请详细描述你的需求，包括具体要求、交付格式、期望效果等"
          maxlength="2000"
          :auto-height="false"
        />
        <text class="char-count">{{ form.description.length }}/2000</text>
      </view>

      <!-- 分类 -->
      <view class="form-item">
        <text class="label">需求分类 <text class="required">*</text></text>
        <picker mode="selector" :value="categoryIndex" :range="categories" range-key="label" @change="onCategoryChange">
          <view class="picker-wrap">
            <text :class="['picker-text', { placeholder: !form.category }]">
              {{ form.category ? categories.find(c => c.value === form.category)?.label : '请选择分类' }}
            </text>
            <text class="picker-arrow">▼</text>
          </view>
        </picker>
      </view>

      <!-- 预算 -->
      <view class="form-item">
        <text class="label">预算金额（元）<text class="required">*</text></text>
        <input
          class="input"
          type="digit"
          v-model="form.budget"
          placeholder="请输入预算金额"
        />
      </view>

      <!-- 截止日期 -->
      <view class="form-item">
        <text class="label">截止日期 <text class="required">*</text></text>
        <picker mode="date" :value="form.deadline" @change="onDeadlineChange">
          <view class="picker-wrap">
            <text :class="['picker-text', { placeholder: !form.deadline }]">
              {{ form.deadline || '请选择截止日期' }}
            </text>
            <text class="picker-arrow">▼</text>
          </view>
        </picker>
      </view>

      <!-- 附件上传 -->
      <view class="form-item">
        <text class="label">附件（可选）</text>
        <view class="image-list">
          <view v-for="(img, idx) in form.images" :key="idx" class="image-item">
            <image :src="img" mode="aspectFill" class="upload-image" />
            <view class="image-delete" @click="removeImage(idx)">✕</view>
          </view>
          <view v-if="form.images.length < 5" class="upload-btn" @click="chooseImage">
            <text class="upload-plus">+</text>
            <text class="upload-hint">上传图片</text>
          </view>
        </view>
      </view>

      <!-- 提交按钮 -->
      <button class="submit-btn" formType="submit" :loading="submitting" :disabled="submitting">
        {{ submitting ? '提交中...' : '发布需求' }}
      </button>
    </form>
  </view>
</template>

<script>
import demandApi from '@/api/demand.js';

const CATEGORIES = [
  { label: '文案', value: 'copywriting' },
  { label: '设计', value: 'design' },
  { label: '开发', value: 'development' },
  { label: '运营', value: 'operation' },
  { label: '翻译', value: 'translation' },
  { label: '视频', value: 'video' },
  { label: '其他', value: 'other' }
];

export default {
  data() {
    return {
      categories: CATEGORIES,
      categoryIndex: -1,
      form: {
        title: '',
        description: '',
        category: '',
        budget: '',
        deadline: '',
        images: []
      },
      submitting: false
    };
  },

  methods: {
    onCategoryChange(e) {
      this.categoryIndex = e.detail.value;
      this.form.category = CATEGORIES[this.categoryIndex].value;
    },

    onDeadlineChange(e) {
      this.form.deadline = e.detail.value;
    },

    chooseImage() {
      const remain = 5 - this.form.images.length;
      uni.chooseImage({
        count: remain,
        sizeType: ['compressed'],
        sourceType: ['album', 'camera'],
        success: (res) => {
          this.form.images = [...this.form.images, ...res.tempFilePaths];
        }
      });
    },

    removeImage(idx) {
      this.form.images.splice(idx, 1);
    },

    validate() {
      if (!this.form.title.trim()) {
        uni.showToast({ title: '请输入需求标题', icon: 'none' });
        return false;
      }
      if (this.form.title.trim().length < 5) {
        uni.showToast({ title: '标题至少5个字符', icon: 'none' });
        return false;
      }
      if (!this.form.description.trim()) {
        uni.showToast({ title: '请输入需求描述', icon: 'none' });
        return false;
      }
      if (this.form.description.trim().length < 10) {
        uni.showToast({ title: '描述至少10个字符', icon: 'none' });
        return false;
      }
      if (!this.form.category) {
        uni.showToast({ title: '请选择需求分类', icon: 'none' });
        return false;
      }
      if (!this.form.budget || Number(this.form.budget) <= 0) {
        uni.showToast({ title: '请输入有效预算金额', icon: 'none' });
        return false;
      }
      if (!this.form.deadline) {
        uni.showToast({ title: '请选择截止日期', icon: 'none' });
        return false;
      }
      const today = new Date().toISOString().split('T')[0];
      if (this.form.deadline < today) {
        uni.showToast({ title: '截止日期不能早于今天', icon: 'none' });
        return false;
      }
      return true;
    },

    async onSubmit() {
      if (!this.validate()) return;

      this.submitting = true;
      try {
        // TODO: 图片上传到服务器拿到URL
        const payload = {
          title: this.form.title.trim(),
          description: this.form.description.trim(),
          category: this.form.category,
          budget: Number(this.form.budget),
          deadline: this.form.deadline,
          attachments: this.form.images // mock：本地路径
        };

        const res = await demandApi.publish(payload);
        const demandId = res.data?.id || res.id;

        uni.showToast({ title: '发布成功', icon: 'success' });
        setTimeout(() => {
          uni.redirectTo({ url: `/pages/demand/detail?id=${demandId}` });
        }, 800);
      } catch (e) {
        console.error('publish error:', e);
      } finally {
        this.submitting = false;
      }
    }
  }
};
</script>

<style scoped>
.publish-page {
  min-height: 100vh;
  background-color: #F5F7FA;
  padding: 24rpx;
  box-sizing: border-box;
}

.form-item {
  background-color: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 24rpx;
}

.label {
  font-size: 28rpx;
  font-weight: bold;
  color: #333;
  display: block;
  margin-bottom: 16rpx;
}

.required {
  color: #EF4444;
}

.input, .textarea {
  width: 100%;
  box-sizing: border-box;
  font-size: 28rpx;
  color: #333;
}

.input {
  padding: 16rpx 0;
  border-bottom: 1rpx solid #eee;
}

.textarea {
  min-height: 200rpx;
  padding: 16rpx 0;
  line-height: 1.6;
}

.char-count {
  text-align: right;
  font-size: 22rpx;
  color: #999;
  display: block;
  margin-top: 8rpx;
}

.picker-wrap {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16rpx 0;
  border-bottom: 1rpx solid #eee;
}

.picker-text {
  font-size: 28rpx;
  color: #333;
}

.picker-text.placeholder {
  color: #999;
}

.picker-arrow {
  font-size: 20rpx;
  color: #999;
}

.image-list {
  display: flex;
  flex-wrap: wrap;
  gap: 16rpx;
}

.image-item {
  position: relative;
  width: 160rpx;
  height: 160rpx;
}

.upload-image {
  width: 100%;
  height: 100%;
  border-radius: 12rpx;
}

.image-delete {
  position: absolute;
  top: -12rpx;
  right: -12rpx;
  width: 40rpx;
  height: 40rpx;
  background-color: rgba(0, 0, 0, 0.6);
  color: #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24rpx;
}

.upload-btn {
  width: 160rpx;
  height: 160rpx;
  border: 2rpx dashed #ccc;
  border-radius: 12rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8rpx;
}

.upload-plus {
  font-size: 48rpx;
  color: #999;
  line-height: 1;
}

.upload-hint {
  font-size: 22rpx;
  color: #999;
}

.submit-btn {
  margin-top: 48rpx;
  background-color: #3B82F6;
  color: #fff;
  border-radius: 48rpx;
  font-size: 32rpx;
  font-weight: bold;
  border: none;
}

.submit-btn[disabled] {
  background-color: #93C5FD;
  color: #fff;
}
</style>
