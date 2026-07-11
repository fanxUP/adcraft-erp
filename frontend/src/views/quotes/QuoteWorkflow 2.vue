<template>
  <div class="qw-bar">
    <div class="qw-flow">
      <!-- 列1: 草稿 -->
      <div class="qw-col">
        <div class="qw-card" :class="cardClass('draft')" @click="handleCardClick('draft')">
          <div class="qw-icon" :class="iconClass('draft')">
            <el-icon v-if="isPast('draft')" :size="16"><Check /></el-icon>
            <span v-else>1</span>
          </div>
          <div class="qw-text">
            <div class="qw-label">保存草稿</div>
            <div v-if="'draft' === currentStatus" class="qw-tag cur-tag">当前</div>
            <div v-else-if="isPast('draft')" class="qw-tag done-tag">已完成</div>
            <div v-else class="qw-tag future-tag">待开始</div>
          </div>
        </div>
      </div>

      <!-- 箭头1 -->
      <div class="qw-conn" :class="{ 'conn-done': isPast('confirmed') }">
        <div class="qw-line"></div>
        <div class="qw-point">▶</div>
      </div>

      <!-- 列2: 已确认 -->
      <div class="qw-col">
        <div class="qw-card" :class="cardClass('confirmed')" @click="handleCardClick('confirmed')">
          <div class="qw-icon" :class="iconClass('confirmed')">
            <el-icon v-if="isPast('confirmed')" :size="16"><Check /></el-icon>
            <span v-else>2</span>
          </div>
          <div class="qw-text">
            <div class="qw-label">确认报价</div>
            <div v-if="'confirmed' === currentStatus" class="qw-tag cur-tag">当前</div>
            <div v-else-if="isPast('confirmed')" class="qw-tag done-tag">已完成</div>
            <div v-else class="qw-tag future-tag">待开始</div>
          </div>
        </div>
      </div>

      <!-- 箭头2 -->
      <div class="qw-conn" :class="{ 'conn-done': isPast('converted') }">
        <div class="qw-line"></div>
        <div class="qw-point">▶</div>
      </div>

      <!-- 列3: 已转订单 -->
      <div class="qw-col">
        <div class="qw-card" :class="cardClass('converted')" @click="handleCardClick('converted')">
          <div class="qw-icon" :class="iconClass('converted')">
            <el-icon v-if="isPast('converted')" :size="16"><Check /></el-icon>
            <span v-else>3</span>
          </div>
          <div class="qw-text">
            <div class="qw-label">转为订单</div>
            <div v-if="'converted' === currentStatus" class="qw-tag cur-tag">当前</div>
            <div v-else-if="isPast('converted')" class="qw-tag done-tag">已完成</div>
            <div v-else class="qw-tag future-tag">待开始</div>
          </div>
        </div>
      </div>

    </div>

    <!-- 预览按钮独立行 -->
    <div class="qw-preview-row">
      <button class="qw-preview-btn" @click="$emit('preview')">
        <el-icon :size="20"><View /></el-icon>
        <span>预览报价单</span>
      </button>
    </div>

    <!-- 提示文字 -->
    <div class="qw-hint">
      <template v-if="currentStatus === 'draft' && isExisting">
        点击「保存草稿」保存，点击「确认报价」确认报价
      </template>
      <template v-else-if="currentStatus === 'draft' && !isExisting">
        点击「保存草稿」保存草稿
      </template>
      <template v-else-if="currentStatus === 'confirmed'">
        点击「确认报价」撤回草稿，点击「转为订单」转订单
      </template>
      <template v-else-if="currentStatus === 'converted'">
        该报价已转为订单，不可再修改
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Check, View } from '@element-plus/icons-vue'

const props = defineProps<{
  currentStatus: string
  isExisting: boolean
  saving: boolean
  converting: boolean
  reverting: boolean
}>()

const emit = defineEmits<{
  save: []
  confirm: []
  convert: []
  revert: []
  preview: []
}>()

const statusOrder = ['draft', 'confirmed', 'converted']

const currentIdx = computed(() => {
  const idx = statusOrder.indexOf(props.currentStatus)
  return idx >= 0 ? idx : -1
})

const reachableTargets = computed(() => {
  const cur = props.currentStatus
  const idx = currentIdx.value
  if (idx < 0 || cur === 'converted') return []
  return statusOrder.slice(idx + 1)
})

function isPast(status: string): boolean {
  const idx = statusOrder.indexOf(status)
  return idx >= 0 && idx < currentIdx.value
}

function isReachable(status: string): boolean {
  return reachableTargets.value.includes(status)
}

function handleCardClick(status: string) {
  if (props.saving || props.converting) return

  // 保存草稿卡片点击 → 保存草稿（仅在草稿状态）
  if (status === 'draft' && props.currentStatus === 'draft') {
    emit('save')
    return
  }

  // 确认报价卡片点击
  if (status === 'confirmed') {
    // 保存草稿 → 确认报价：确认报价
    if (props.currentStatus === 'draft') {
      if (!props.isExisting) return
      emit('confirm')
      return
    }
    // 确认报价 → 保存草稿：撤回
    if (props.currentStatus === 'confirmed') {
      emit('revert')
      return
    }
    return
  }

  // 转为订单卡片点击：从确认报价转订单
  if (status === 'converted' && props.currentStatus === 'confirmed') {
    emit('convert')
    return
  }
}

function cardClass(status: string) {
  if (status === props.currentStatus) return 'card-current'
  if (isPast(status)) return 'card-done'
  if (isReachable(status)) return 'card-ready'
  return 'card-disabled'
}

function iconClass(status: string) {
  if (status === props.currentStatus) return 'icon-current'
  if (isPast(status)) return 'icon-done'
  if (isReachable(status)) return 'icon-ready'
  return 'icon-disabled'
}
</script>

<style scoped>
/* ===== 容器 ===== */
.qw-bar {
  border: 1px solid var(--ad-border);
  border-radius: 12px;
  padding: 24px 24px 16px;
  margin: 16px 0;
  background: var(--ad-card);
}

.qw-flow {
  display: flex;
  align-items: flex-start;
  gap: 0;
}

.qw-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
}

/* ===== 卡片 ===== */
.qw-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 20px;
  border-radius: 10px;
  border: 2px solid transparent;
  transition: all 0.25s ease;
  cursor: default;
  min-width: 100px;
  min-height: 48px;
  box-sizing: border-box;
}

.qw-icon {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  flex-shrink: 0;
  transition: all 0.25s ease;
}

.qw-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.qw-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--ad-text);
  white-space: nowrap;
  letter-spacing: 0.5px;
}

.qw-tag {
  font-size: 10px;
  font-weight: 500;
  white-space: nowrap;
}
.cur-tag { color: #409eff; }
.done-tag { color: #52c41a; }
.future-tag { color: #d9d9d9; }

/* ===== 连接箭头 ===== */
.qw-conn {
  display: flex;
  align-items: center;
  padding: 0 4px;
  flex-shrink: 0;
  margin-top: 24px;
}

.qw-line {
  width: 48px;
  height: 2px;
  background: #e8e8e8;
  border-radius: 2px;
  transition: all 0.3s ease;
}

.conn-done .qw-line {
  background: linear-gradient(to right, #52c41a, #73d13d);
  height: 3px;
}

.qw-point {
  font-size: 12px;
  color: #d9d9d9;
  margin-left: -2px;
  transition: all 0.3s ease;
}

.conn-done .qw-point {
  color: #73d13d;
}

/* ===== 卡片状态 ===== */

/* 当前 */
.card-current {
  border-color: #409eff;
  background: linear-gradient(135deg, rgba(64,158,255,0.07), rgba(64,158,255,0.03));
  box-shadow: 0 0 0 4px rgba(64,158,255,0.08);
  cursor: pointer;
}
.card-current:hover {
  background: linear-gradient(135deg, rgba(64,158,255,0.12), rgba(64,158,255,0.06));
  box-shadow: 0 2px 12px rgba(64,158,255,0.15);
}
.card-current .qw-label { color: #409eff; }

.icon-current {
  background: linear-gradient(135deg, #409eff, #66b1ff);
  color: #fff;
  box-shadow: 0 2px 8px rgba(64,158,255,0.35);
}

/* 已完成 */
.card-done { border-color: transparent; }
.card-done .qw-label { color: #52c41a; }

.icon-done {
  background: linear-gradient(135deg, #52c41a, #73d13d);
  color: #fff;
  box-shadow: 0 2px 6px rgba(82,196,26,0.3);
}

/* 可点击 */
.card-ready {
  border-color: #409eff;
  border-style: dashed;
  background: rgba(64,158,255,0.03);
  cursor: pointer;
}
.card-ready:hover {
  background: rgba(64,158,255,0.08);
  box-shadow: 0 2px 10px rgba(64,158,255,0.1);
  transform: translateX(3px);
}
.card-ready:active { transform: translateX(0); }
.card-ready .qw-label { color: #409eff; }

.icon-ready {
  background: #f0f5ff;
  color: #409eff;
  border: 2px solid #409eff;
  cursor: pointer;
}
.icon-ready:hover {
  background: #e6f0ff;
  box-shadow: 0 0 0 4px rgba(64,158,255,0.15);
}

/* 不可达 */
.card-disabled { border-color: #f0f0f0; background: #fafafa; }
.card-disabled .qw-label { color: #d9d9d9; }

.icon-disabled {
  background: #f5f5f5;
  color: #d9d9d9;
  border: 2px solid #e8e8e8;
}

/* ===== 预览按钮独立行 ===== */
.qw-preview-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid var(--ad-border);
}

.qw-preview-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 24px;
  border: none;
  border-radius: 10px;
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s ease;
  box-shadow: 0 3px 10px rgba(64,158,255,0.3);
  letter-spacing: 0.5px;
}

.qw-preview-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 18px rgba(64,158,255,0.4);
}

.qw-preview-btn:active {
  transform: translateY(0);
  box-shadow: 0 2px 6px rgba(64,158,255,0.25);
}

/* ===== 提示文字 ===== */
.qw-hint {
  margin-top: 12px;
  font-size: 12px;
  color: var(--ad-text-secondary);
  text-align: center;
}

/* ===== 暗色主题 ===== */
:root[data-theme="dark"] .icon-disabled {
  background: #262626; color: #434343; border-color: #434343;
}
:root[data-theme="dark"] .icon-ready {
  background: rgba(64,158,255,0.12);
}
:root[data-theme="dark"] .icon-ready:hover {
  background: rgba(64,158,255,0.2);
}
:root[data-theme="dark"] .card-disabled {
  border-color: #262626; background: #1a1a1a;
}
:root[data-theme="dark"] .card-disabled .qw-label { color: #434343; }
:root[data-theme="dark"] .card-disabled .future-tag { color: #434343; }
:root[data-theme="dark"] .card-current {
  background: rgba(64,158,255,0.1);
  box-shadow: 0 0 0 4px rgba(64,158,255,0.12);
}
:root[data-theme="dark"] .card-ready {
  background: rgba(64,158,255,0.06);
}
:root[data-theme="dark"] .card-ready:hover {
  background: rgba(64,158,255,0.15);
}
:root[data-theme="dark"] .qw-line { background: #434343; }
:root[data-theme="dark"] .qw-point { color: #595959; }
:root[data-theme="dark"] .qw-preview-btn {
  background: linear-gradient(135deg, #1677ff 0%, #409eff 100%);
  box-shadow: 0 3px 10px rgba(22,119,255,0.3);
}
:root[data-theme="dark"] .qw-preview-btn:hover {
  box-shadow: 0 6px 18px rgba(22,119,255,0.45);
}

/* ===== 小屏 ===== */
@media (max-width: 800px) {
  .qw-bar { padding: 14px; }
  .qw-card { padding: 8px 12px; min-width: 60px; min-height: 40px; gap: 8px; }
  .qw-line { width: 20px; }
  .qw-conn { padding: 0 2px; }
  .qw-tag { display: none; }
  .qw-preview-row { margin-top: 12px; padding-top: 10px; }
  .qw-preview-btn { width: 100%; justify-content: center; padding: 8px 16px; font-size: 13px; }
}
</style>
