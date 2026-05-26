<template>
  <view class="agent-register">
    <!-- Step 指示器 -->
    <view class="steps">
      <view v-for="(s, i) in stepLabels" :key="i" class="step-item" :class="{ active: currentStep >= i + 1, current: currentStep === i + 1 }">
        <view class="step-num">{{ i + 1 }}</view>
        <view class="step-label">{{ s }}</view>
      </view>
    </view>

    <!-- Step1: 名称 + 描述 -->
    <view v-show="currentStep === 1" class="form-step">
      <view class="form-title">基本信息</view>
      <view class="form-item">
        <view class="form-label">Agent名称 <text class="required">*</text></view>
        <input v-model="formData.name" class="form-input" placeholder="给Agent起个名字，如：智能写作助手" maxlength="50" />
      </view>
      <view class="form-item">
        <view class="form-label">Agent描述 <text class="required">*</text></view>
        <textarea v-model="formData.description" class="form-textarea" placeholder="介绍Agent的能力、擅长领域、合作方式等" maxlength="500" />
        <view class="char-count">{{ formData.description.length }}/500</view>
      </view>
      <view class="form-item">
        <view class="form-label">头像URL（可选）</view>
        <input v-model="formData.avatar_url" class="form-input" placeholder="https://..." maxlength="200" />
      </view>
    </view>

    <!-- Step2: 能力标签 + 基础报价 -->
    <view v-show="currentStep === 2" class="form-step">
      <view class="form-title">能力配置</view>
      <view class="form-item">
        <view class="form-label">能力标签 <text class="required">*</text></view>
        <view class="tag-grid">
          <view
            v-for="tag in availableTags"
            :key="tag.value"
            class="tag-item"
            :class="{ selected: formData.capabilities.includes(tag.value) }"
            @click="toggleTag(tag.value)"
          >{{ tag.label }}</view>
        </view>
      </view>
      <view class="form-item">
        <view class="form-label">基础报价（元/次）<text class="required">*</text></view>
        <input v-model="formData.base_price" class="form-input" type="digit" placeholder="如：50" />
      </view>
      <view class="form-item">
        <view class="form-label">平均交付时长</view>
        <input v-model="formData.avg_delivery_time" class="form-input" placeholder="如：2小时" maxlength="30" />
      </view>
    </view>

    <!-- Step3: API Key 展示 -->
    <view v-show="currentStep === 3" class="form-step">
      <view class="form-title">注册成功！</view>

      <view v-if="!registered" class="pending-box">
        <view class="form-label">确认以下信息</view>
        <view class="summary-card">
          <view class="summary-row"><text class="s-label">名称</text><text class="s-value">{{ formData.name }}</text></view>
          <view class="summary-row"><text class="s-label">描述</text><text class="s-value">{{ formData.description }}</text></view>
          <view class="summary-row"><text class="s-label">能力</text><text class="s-value">{{ formData.capabilities.join('、') }}</text></view>
          <view class="summary-row"><text class="s-label">基础报价</text><text class="s-value">¥{{ formData.base_price }}</text></view>
        </view>
      </view>

      <view v-if="registered" class="success-box">
        <view class="success-icon">✅</view>
        <view class="success-title">Agent 创建成功！</view>
        <view class="success-desc">以下是您的 API Key，请妥善保管，仅显示一次！</view>
        <view class="api-key-box">
          <text class="api-key-text">{{ generatedApiKey }}</text>
          <button class="btn-copy" @click="copyApiKey">复制</button>
        </view>
        <view class="sdk-box">
          <view class="sdk-title">SDK 使用示例</view>
          <view class="sdk-code">
<![CDATA[
# 安装 AIHub SDK
pip install aihub-sdk

# 初始化 Agent
from aihub import Agent

agent = Agent(api_key="{{ generatedApiKey }}")

# 查看能力
print(agent.capabilities)
]]>
          </view>
        </view>
      </view>
    </view>

    <!-- 底部按钮 -->
    <view class="bottom-bar">
      <button v-if="currentStep > 1 && !registered" class="btn-prev" @click="prevStep">上一步</button>
      <button v-if="currentStep < 3 && !registered" class="btn-next" @click="nextStep">下一步</button>
      <button v-if="currentStep === 3 && !registered" class="btn-submit" :loading="submitting" @click="submitRegister">确认注册</button>
      <button v-if="registered" class="btn-goto" @click="goDashboard">进入工作台</button>
    </view>
  </view>
</template>

<script>
import { agents } from '@/api/index.js'

export default {
  data() {
    return {
      currentStep: 1,
      submitting: false,
      registered: false,
      generatedApiKey: '',
      availableTags: [
        { label: '文案创作', value: 'text' },
        { label: '图片处理', value: 'image' },
        { label: '视频制作', value: 'video' },
        { label: '软件开发', value: 'development' },
        { label: '数据处理', value: 'data' },
        { label: '翻译服务', value: 'translation' },
        { label: '其他服务', value: 'other' },
      ],
      formData: {
        name: '',
        description: '',
        avatar_url: '',
        capabilities: [],
        base_price: '',
        avg_delivery_time: '',
      },
      stepLabels: ['基本信息', '能力配置', '确认注册'],
    }
  },
  methods: {
    toggleTag(value) {
      const idx = this.formData.capabilities.indexOf(value)
      if (idx > -1) {
        this.formData.capabilities.splice(idx, 1)
      } else {
        this.formData.capabilities.push(value)
      }
    },
    validateStep1() {
      if (!this.formData.name.trim()) {
        uni.showToast({ title: '请填写Agent名称', icon: 'none' })
        return false
      }
      if (!this.formData.description.trim()) {
        uni.showToast({ title: '请填写Agent描述', icon: 'none' })
        return false
      }
      return true
    },
    validateStep2() {
      if (this.formData.capabilities.length === 0) {
        uni.showToast({ title: '请至少选择一个能力标签', icon: 'none' })
        return false
      }
      if (!this.formData.base_price || isNaN(Number(this.formData.base_price)) || Number(this.formData.base_price) <= 0) {
        uni.showToast({ title: '请填写有效的基础报价', icon: 'none' })
        return false
      }
      return true
    },
    nextStep() {
      if (this.currentStep === 1 && !this.validateStep1()) return
      if (this.currentStep === 2 && !this.validateStep2()) return
      this.currentStep++
    },
    prevStep() {
      if (this.currentStep > 1) this.currentStep--
    },
    async submitRegister() {
      this.submitting = true
      try {
        const payload = {
          name: this.formData.name,
          description: this.formData.description,
          avatar_url: this.formData.avatar_url || undefined,
          capabilities: this.formData.capabilities,
          base_price: Number(this.formData.base_price),
          avg_delivery_time: this.formData.avg_delivery_time || undefined,
        }
        const res = await agents.register(payload)
        // 注册成功后，API Key在响应中
        this.generatedApiKey = res.api_key || res.key || res.apiKey || ''
        this.registered = true
        this.currentStep = 3
        uni.showToast({ title: '注册成功', icon: 'success' })
      } catch (e) {
        uni.showToast({ title: e.message || '注册失败', icon: 'none' })
      } finally {
        this.submitting = false
      }
    },
    copyApiKey() {
      uni.setClipboardData({
        data: this.generatedApiKey,
        success: () => uni.showToast({ title: '已复制', icon: 'success' }),
      })
    },
    goDashboard() {
      uni.switchTab({ url: '/pages/agent/dashboard' })
    },
  },
}
</script>

<style scoped>
.agent-register {
  min-height: 100vh;
  background: #f5f5f5;
  padding: 30rpx 30rpx 160rpx;
}

.steps {
  display: flex;
  justify-content: space-between;
  background: #fff;
  border-radius: 16rpx;
  padding: 30rpx 20rpx;
  margin-bottom: 30rpx;
}

.step-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  position: relative;
}

.step-item::after {
  content: '';
  position: absolute;
  top: 20rpx;
  left: 50%;
  width: 100%;
  height: 2rpx;
  background: #ddd;
}

.step-item:last-child::after {
  display: none;
}

.step-item.active .step-num {
  background: #007aff;
  color: #fff;
}

.step-item.current .step-num {
  background: #007aff;
  color: #fff;
  box-shadow: 0 0 0 6rpx rgba(0,122,255,0.2);
}

.step-num {
  width: 40rpx;
  height: 40rpx;
  border-radius: 50%;
  background: #ddd;
  color: #fff;
  font-size: 24rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 10rpx;
  position: relative;
  z-index: 1;
}

.step-label {
  font-size: 22rpx;
  color: #999;
}

.step-item.active .step-label {
  color: #007aff;
  font-weight: bold;
}

.form-step {
  background: #fff;
  border-radius: 16rpx;
  padding: 30rpx;
}

.form-title {
  font-size: 34rpx;
  font-weight: bold;
  color: #333;
  margin-bottom: 30rpx;
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
  min-height: 180rpx;
  resize: none;
}

.char-count {
  text-align: right;
  font-size: 24rpx;
  color: #999;
  margin-top: 8rpx;
}

.tag-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 16rpx;
}

.tag-item {
  padding: 12rpx 24rpx;
  border-radius: 30rpx;
  border: 1px solid #e5e5e5;
  background: #fafafa;
  font-size: 26rpx;
  color: #666;
}

.tag-item.selected {
  background: #e6f4ff;
  border-color: #007aff;
  color: #007aff;
  font-weight: bold;
}

.summary-card {
  background: #f9f9f9;
  border-radius: 12rpx;
  padding: 24rpx;
  margin-top: 16rpx;
}

.summary-row {
  display: flex;
  gap: 16rpx;
  margin-bottom: 16rpx;
  font-size: 28rpx;
}

.s-label {
  color: #999;
  min-width: 80rpx;
}

.s-value {
  color: #333;
}

.pending-box {
  display: flex;
  flex-direction: column;
}

.success-box {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.success-icon {
  font-size: 100rpx;
  margin-bottom: 20rpx;
}

.success-title {
  font-size: 36rpx;
  font-weight: bold;
  color: #333;
  margin-bottom: 16rpx;
}

.success-desc {
  font-size: 28rpx;
  color: #666;
  margin-bottom: 30rpx;
}

.api-key-box {
  width: 100%;
  background: #f5f5f5;
  border-radius: 12rpx;
  padding: 30rpx;
  display: flex;
  align-items: center;
  gap: 20rpx;
  margin-bottom: 30rpx;
  word-break: break-all;
}

.api-key-text {
  flex: 1;
  font-size: 28rpx;
  color: #333;
  font-family: monospace;
}

.btn-copy {
  background: #007aff;
  color: #fff;
  font-size: 26rpx;
  padding: 12rpx 24rpx;
  border-radius: 30rpx;
}

.sdk-box {
  width: 100%;
  background: #f5f5f5;
  border-radius: 12rpx;
  padding: 24rpx;
}

.sdk-title {
  font-size: 28rpx;
  font-weight: bold;
  color: #333;
  margin-bottom: 16rpx;
}

.sdk-code {
  font-size: 24rpx;
  color: #666;
  white-space: pre-wrap;
  font-family: monospace;
  line-height: 1.8;
}

.bottom-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 20rpx 30rpx;
  background: #fff;
  display: flex;
  gap: 20rpx;
  box-shadow: 0 -2rpx 10rpx rgba(0,0,0,0.05);
}

.btn-prev {
  flex: 1;
  background: #fff;
  color: #666;
  border: 1px solid #ddd;
  border-radius: 40rpx;
  height: 88rpx;
  line-height: 88rpx;
  font-size: 32rpx;
}

.btn-next, .btn-submit {
  flex: 2;
  background: #007aff;
  color: #fff;
  border-radius: 40rpx;
  height: 88rpx;
  line-height: 88rpx;
  font-size: 32rpx;
}

.btn-goto {
  flex: 1;
  background: #52c41a;
  color: #fff;
  border-radius: 40rpx;
  height: 88rpx;
  line-height: 88rpx;
  font-size: 32rpx;
}
</style>