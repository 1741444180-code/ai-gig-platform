<template>
  <view class="page-container">
    <!-- Top Nav -->
    <view class="top-nav">
      <view class="back-btn" @click="goBack">
        <text class="back-icon">‹</text>
      </view>
      <text class="nav-title">发布需求</text>
    </view>

    <!-- Form -->
    <view class="form-section">
      <view class="form-label">
        <text>需求标题</text>
        <text class="required">*</text>
      </view>
      <input
        class="form-input"
        placeholder="简洁描述你的需求，例如：搭建企业文档问答系统"
        v-model="form.title"
        maxlength="100"
      />
    </view>

    <view class="form-section">
      <view class="form-label">
        <text>需求分类</text>
        <text class="required">*</text>
      </view>
      <picker mode="selector" :range="categories" @change="onCategoryChange" :value="categoryIndex">
        <view class="form-input picker-input">
          <text :class="{ placeholder: !form.category }">
            {{ form.category || '选择分类' }}
          </text>
          <text class="picker-arrow">▾</text>
        </view>
      </picker>
    </view>

    <view class="form-section">
      <view class="form-label">
        <text>技术栈标签</text>
        <text class="hint">可选</text>
      </view>
      <view class="tags-container">
        <view class="tag-pill" v-for="(tag, i) in form.tags" :key="i">
          <text>{{ tag }}</text>
          <text class="tag-remove" @click="removeTag(i)">×</text>
        </view>
        <input
          class="tag-input"
          v-model="newTag"
          placeholder="输入后回车添加标签"
          @confirm="addTag"
          @blur="addTag"
        />
      </view>
    </view>

    <view class="form-section">
      <view class="form-label">
        <text>需求描述</text>
        <text class="required">*</text>
        <text class="hint">建议200字以上</text>
      </view>
      <textarea
        class="form-input form-textarea"
        placeholder="详细描述你的需求：&#10;• 项目背景和目标&#10;• 技术要求&#10;• 交付物要求&#10;• 时间预期"
        v-model="form.description"
        maxlength="2000"
      />
    </view>

    <view class="form-section">
      <view class="form-label">
        <text>预算方式</text>
        <text class="required">*</text>
      </view>
      <view class="price-type">
        <view
          class="price-option"
          :class="{ active: budgetMode === 'fixed' }"
          @click="budgetMode = 'fixed'"
        >固定价格</view>
        <view
          class="price-option"
          :class="{ active: budgetMode === 'range' }"
          @click="budgetMode = 'range'"
        >价格区间</view>
        <view
          class="price-option"
          :class="{ active: budgetMode === 'negotiable' }"
          @click="budgetMode = 'negotiable'"
        >面议</view>
      </view>

      <view class="budget-row" v-if="budgetMode === 'fixed'">
        <input class="form-input" type="digit" placeholder="预算金额（¥）" v-model="form.budget" />
        <input class="form-input budget-deadline" type="number" placeholder="截止日期（天）" v-model="form.deadline" />
      </view>
      <view class="budget-row" v-if="budgetMode === 'range'">
        <input class="form-input" type="digit" placeholder="最低价" v-model="form.budgetMin" />
        <input class="form-input" type="digit" placeholder="最高价" v-model="form.budgetMax" />
      </view>
    </view>

    <view style="height: 20px;"></view>

    <!-- Submit Bar -->
    <view class="submit-bar">
      <button class="btn-draft" @click="saveDraft">存草稿</button>
      <button class="btn-submit" @click="publishDemand">发布需求</button>
    </view>
  </view>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { demands } from '../../api/index.js'

const categories = [
  'NLP / 自然语言处理',
  '图像生成 / 计算机视觉',
  '语音处理',
  '数据分析',
  'API 开发 / 对接',
  '自动化 / Agent 编排',
  '其他',
]
const categoryIndex = ref(0)

const form = reactive({
  title: '',
  category: '',
  tags: [],
  description: '',
  budget: '',
  budgetMin: '',
  budgetMax: '',
  deadline: '',
})

const budgetMode = ref('fixed')
const newTag = ref('')

function goBack() {
  uni.navigateBack()
}

function onCategoryChange(e) {
  categoryIndex.value = e.detail.value
  form.category = categories[e.detail.value]
}

function addTag() {
  const tag = newTag.value.trim()
  if (tag && !form.tags.includes(tag)) {
    form.tags.push(tag)
  }
  newTag.value = ''
}

function removeTag(index) {
  form.tags.splice(index, 1)
}

function saveDraft() {
  uni.setStorageSync('demand_draft', JSON.stringify(form))
  uni.showToast({ title: '已存草稿', icon: 'success' })
}

async function publishDemand() {
  if (!form.title) {
    uni.showToast({ title: '请填写需求标题', icon: 'none' })
    return
  }
  if (!form.category) {
    uni.showToast({ title: '请选择需求分类', icon: 'none' })
    return
  }
  if (!form.description) {
    uni.showToast({ title: '请填写需求描述', icon: 'none' })
    return
  }

  const budget = budgetMode.value === 'fixed'
    ? parseFloat(form.budget) || null
    : budgetMode.value === 'range'
      ? { min: parseFloat(form.budgetMin) || null, max: parseFloat(form.budgetMax) || null }
      : null

  try {
    await demands.create({
      title: form.title,
      category: form.category,
      tags: form.tags,
      description: form.description,
      budget: typeof budget === 'number' ? budget : null,
      deadline: form.deadline ? parseInt(form.deadline) : null,
    })
    uni.showToast({ title: '发布成功', icon: 'success' })
    setTimeout(() => {
      uni.switchTab({ url: '/pages/demand/home' })
    }, 500)
  } catch (e) {
    uni.showToast({ title: e.message || '发布失败', icon: 'none' })
  }
}
</script>

<style scoped>
.top-nav {
  background: #fff;
  padding: 12px 16px;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid #E5E7EB;
  position: sticky;
  top: 0;
  z-index: 100;
}
.back-btn {
  width: 32px; height: 32px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 8px;
}
.back-icon { font-size: 24px; color: #1D1D1F; line-height: 1; }
.nav-title { font-size: 17px; font-weight: 600; }

.form-section {
  background: #fff;
  padding: 20px 16px;
  margin-top: 10px;
  border-top: 1px solid #E5E7EB;
  border-bottom: 1px solid #E5E7EB;
}
.form-section + .form-section { margin-top: 0; border-top: none; }
.form-label {
  font-size: 14px; font-weight: 600; color: #1D1D1F;
  display: flex; flex-direction: row; align-items: center;
  margin-bottom: 8px;
}
.required { color: #DC2626; font-size: 12px; margin-left: 4px; }
.hint { font-size: 11px; color: #A1A1AA; font-weight: 400; margin-left: auto; }
.form-input {
  width: 100%;
  border: 1px solid #D4D4D8;
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 14px;
  background: #FAFAFA;
}
.form-textarea { min-height: 120px; resize: none; line-height: 1.5; }
.picker-input {
  display: flex; flex-direction: row; align-items: center; justify-content: space-between;
}
.picker-arrow { color: #A1A1AA; font-size: 12px; }
.placeholder { color: #A1A1AA; }

.tags-container {
  display: flex; flex-direction: row; flex-wrap: wrap;
  gap: 6px; padding: 8px;
  border: 1px solid #D4D4D8;
  border-radius: 8px;
  background: #FAFAFA;
  min-height: 44px;
}
.tag-pill {
  display: flex; flex-direction: row; align-items: center; gap: 4px;
  padding: 4px 10px;
  background: #EEF2FF; color: #4F46E5;
  border-radius: 4px;
  font-size: 12px; font-weight: 500;
}
.tag-remove { cursor: pointer; opacity: 0.6; font-size: 14px; }
.tag-input {
  flex: 1; min-width: 80px;
  border: none; outline: none;
  font-size: 14px; background: transparent;
}

.price-type { display: flex; flex-direction: row; gap: 8px; margin-bottom: 12px; }
.price-option {
  flex: 1; padding: 10px; text-align: center;
  border: 1px solid #D4D4D8; border-radius: 8px;
  font-size: 13px; font-weight: 500; color: #71717A;
  background: #FAFAFA;
}
.price-option.active {
  border-color: #4F46E5; background: #EEF2FF; color: #4F46E5;
}
.budget-row { display: flex; flex-direction: row; gap: 10px; }
.budget-deadline { flex: 0 0 140px; }

.submit-bar {
  position: fixed;
  bottom: 0;
  width: 100%;
  background: #fff;
  border-top: 1px solid #E5E7EB;
  padding: 12px 16px;
  display: flex;
  flex-direction: row;
  gap: 10px;
  z-index: 100;
}
.btn-draft {
  flex: 0 0 80px;
  padding: 12px;
  border: 1px solid #D4D4D8; border-radius: 8px;
  background: #fff;
  font-size: 14px; font-weight: 500; color: #71717A;
}
.btn-submit {
  flex: 1;
  padding: 12px;
  border: none; border-radius: 8px;
  background: #4F46E5;
  font-size: 14px; font-weight: 600; color: #fff;
}
</style>
