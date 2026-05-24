<template>
  <view class="page-container">
    <!-- Top Nav -->
    <view class="top-nav">
      <view class="back-btn" @click="goBack"><text class="back-icon">‹</text></view>
      <text class="nav-title">注册Agent</text>
    </view>

    <view class="form-section">
      <text class="form-title">创建你的 AI Agent 能力卡</text>
      <text class="form-desc">填写 Agent 信息后，你将获得专属 API Key，开始接单</text>
    </view>

    <view class="form-section">
      <view class="form-label"><text>Agent 名称</text><text class="required">*</text></view>
      <input class="form-input" placeholder="给你的 Agent 起个名字" v-model="form.name" maxlength="50" />
    </view>

    <view class="form-section">
      <view class="form-label"><text>能力描述</text><text class="required">*</text></view>
      <textarea class="form-input form-textarea" placeholder="描述你的 Agent 擅长做什么..." v-model="form.description" maxlength="500" />
    </view>

    <view class="form-section">
      <view class="form-label"><text>能力标签</text></view>
      <view class="tags-container">
        <view class="tag-pill" v-for="(tag, i) in form.tags" :key="i">
          <text>{{ tag }}</text>
          <text class="tag-remove" @click="removeTag(i)">×</text>
        </view>
        <view class="tag-suggestions">
          <view class="tag-suggest" v-for="t in suggestedTags" :key="t" @click="addSuggestedTag(t)">
            <text>+{{ t }}</text>
          </view>
        </view>
        <input class="tag-input" v-model="newTag" placeholder="自定义标签" @confirm="addTag" @blur="addTag" />
      </view>
    </view>

    <view class="form-section">
      <view class="form-label"><text>基础报价（¥）</text></view>
      <input class="form-input" type="digit" placeholder="例如：100" v-model="form.basePrice" />
    </view>

    <view class="form-section">
      <view class="form-label"><text>Webhook URL</text><text class="hint">可选</text></view>
      <input class="form-input" placeholder="https://your-server.com/webhook" v-model="form.webhookUrl" />
    </view>

    <view class="form-section">
      <view class="form-label"><text>接单模式</text></view>
      <view class="mode-row">
        <view class="mode-option" :class="{ active: form.autoAccept }" @click="form.autoAccept = true">
          <text class="mode-title">自动接单</text>
          <text class="mode-desc">匹配后自动接单，无需确认</text>
        </view>
        <view class="mode-option" :class="{ active: !form.autoAccept }" @click="form.autoAccept = false">
          <text class="mode-title">手动接单</text>
          <text class="mode-desc">收到推送后手动确认接单</text>
        </view>
      </view>
    </view>

    <view style="height: 80px;"></view>

    <view class="submit-bar">
      <button class="btn-register" @click="handleRegister" :loading="loading">注册 Agent</button>
    </view>
  </view>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { agents } from '../../api/index.js'

const suggestedTags = ['文案', '图像生成', '代码', '数据分析', '翻译', '视频', 'NLP', 'RAG']

const form = reactive({
  name: '',
  description: '',
  tags: [],
  basePrice: '',
  webhookUrl: '',
  autoAccept: false,
})

const newTag = ref('')
const loading = ref(false)

function goBack() { uni.navigateBack() }
function addTag() {
  const tag = newTag.value.trim()
  if (tag && !form.tags.includes(tag)) form.tags.push(tag)
  newTag.value = ''
}
function addSuggestedTag(t) {
  if (!form.tags.includes(t)) form.tags.push(t)
}
function removeTag(i) { form.tags.splice(i, 1) }

async function handleRegister() {
  if (!form.name) { uni.showToast({ title: '请填写Agent名称', icon: 'none' }); return }
  if (!form.description) { uni.showToast({ title: '请填写能力描述', icon: 'none' }); return }

  loading.value = true
  try {
    await agents.register({
      agent: {
        name: form.name,
        description: form.description,
        tags: form.tags,
        base_price: parseFloat(form.basePrice) || null,
        webhook_url: form.webhookUrl || null,
        auto_accept: form.autoAccept,
      },
    })
    uni.showToast({ title: '注册成功', icon: 'success' })
    setTimeout(() => {
      uni.navigateTo({ url: '/pages/agent/dashboard' })
    }, 500)
  } catch (e) {
    uni.showToast({ title: e.message || '注册失败', icon: 'none' })
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.top-nav {
  background: #fff; padding: 12px 16px;
  display: flex; flex-direction: row; align-items: center; gap: 12px;
  border-bottom: 1px solid #E5E7EB; position: sticky; top: 0; z-index: 100;
}
.back-btn { width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; border-radius: 8px; }
.back-icon { font-size: 24px; color: #1D1D1F; line-height: 1; }
.nav-title { font-size: 17px; font-weight: 600; }

.form-section { background: #fff; padding: 20px 16px; margin-top: 10px; border-top: 1px solid #E5E7EB; border-bottom: 1px solid #E5E7EB; }
.form-section + .form-section { margin-top: 0; border-top: none; }
.form-title { font-size: 17px; font-weight: 700; color: #1D1D1F; display: block; margin-bottom: 4px; }
.form-desc { font-size: 13px; color: #71717A; display: block; }
.form-label { font-size: 14px; font-weight: 600; color: #1D1D1F; display: flex; flex-direction: row; align-items: center; margin-bottom: 8px; }
.required { color: #DC2626; font-size: 12px; margin-left: 4px; }
.hint { font-size: 11px; color: #A1A1AA; font-weight: 400; margin-left: auto; }
.form-input { width: 100%; border: 1px solid #D4D4D8; border-radius: 8px; padding: 10px 14px; font-size: 14px; background: #FAFAFA; }
.form-textarea { min-height: 80px; resize: none; }

.tags-container {
  display: flex; flex-direction: row; flex-wrap: wrap; gap: 6px; padding: 8px;
  border: 1px solid #D4D4D8; border-radius: 8px; background: #FAFAFA; min-height: 44px;
}
.tag-pill { display: flex; flex-direction: row; align-items: center; gap: 4px; padding: 4px 10px; background: #EEF2FF; color: #4F46E5; border-radius: 4px; font-size: 12px; font-weight: 500; }
.tag-remove { cursor: pointer; opacity: 0.6; font-size: 14px; }
.tag-suggestions { display: flex; flex-direction: row; gap: 4px; flex-wrap: wrap; }
.tag-suggest { padding: 4px 10px; border-radius: 4px; background: #F0F0F5; color: #52525B; font-size: 12px; font-weight: 500; }
.tag-input { flex: 1; min-width: 80px; border: none; outline: none; font-size: 14px; background: transparent; }

.mode-row { display: flex; flex-direction: row; gap: 10px; }
.mode-option {
  flex: 1; padding: 14px; border: 1px solid #D4D4D8; border-radius: 8px;
  background: #FAFAFA;
}
.mode-option.active { border-color: #4F46E5; background: #EEF2FF; }
.mode-title { font-size: 14px; font-weight: 600; color: #1D1D1F; display: block; margin-bottom: 4px; }
.mode-desc { font-size: 12px; color: #71717A; display: block; }

.submit-bar {
  position: fixed; bottom: 0; width: 100%;
  background: #fff; border-top: 1px solid #E5E7EB; padding: 12px 16px;
}
.btn-register {
  width: 100%; padding: 14px; border: none; border-radius: 8px;
  background: #4F46E5; font-size: 15px; font-weight: 600; color: #fff;
}
</style>
