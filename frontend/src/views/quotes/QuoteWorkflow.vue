<template>
  <div class="qw-bar">
    <div class="qw-flow">
      <!-- 列1: 草稿 -->
      <div class="qw-col">
        <div class="qw-card" :class="cardClass('draft')" @click="tryChange('draft')">
          <div class="qw-icon" :class="iconClass('draft')">
            <el-icon v-if="isPast('draft')" :size="16"><Check /></el-icon>
            <span v-else>1</span>
          </div>
          <div class="qw-text">
            <div class="qw-label">草稿</div>
            <div v-if="'draft' === currentStatus" class="qw-tag cur-tag">当前</div>
            <div v-else-if="isPast('draft')" class="qw-tag done-tag">已完成</div>
          </div>
        </div>
        <!-- 草稿状态下的保存按钮 -->
        <button v-if="currentStatus === 'draft'" class="qw-action primary" :disabled="saving" @click="$emit('save')">
          <el-icon :size="14"><Edit /></el-icon>
          <span>{{ saving ? '保存中…' : '保存草稿' }}</span>
        </button>
      </div>

      <!-- 箭头1 -->
      <div class="qw-conn" :class="{ 'conn-done': isPast('confirmed') }">
        <div class="qw-line"></div>
        <div class="qw-point">▶</div>
        <!-- 确认报价按钮，在草稿状态显示在箭头上 -->
        <button
          v-if="currentStatus === 'draft' && isExisting"
          class="qw-btn-on-arrow success"
          @click="$emit('confirm')"
        >
          <el-icon :size="13"><CircleCheck /></el-icon>
          <span>确认报价</span>
        </button>
        <!-- 撤回草稿按钮，在已确认状态显示在箭头上 -->
        <button
          v-if="currentStatus === 'confirmed'"
          class="qw-btn-on-arrow warning"
          :disabled="reverting"
          @click="$emit('revert')"
        >
          <el-icon :size="13"><Back /></el-icon>
          <span>{{ reverting ? '撤回中…' : '撤回草稿' }}</span>
        </button>
      </div>

      <!-- 列2: 已确认 -->
      <div class="qw-col">
        <div class="qw-card" :class="cardClass('confirmed')" @click="tryChange('confirmed')">
          <div class="qw-icon" :class="iconClass('confirmed')">
            <el-icon v-if="isPast('confirmed')" :size="16"><Check /></el-icon>
            <span v-else>2</span>
          </div>
          <div class="qw-text">
            <div class="qw-label">已确认</div>
            <div v-if="'confirmed' === currentStatus" class="qw-tag cur-tag">当前</div>
            <div v-else-if="isPast('confirmed')" class="qw-tag done-tag">已完成</div>
          </div>
        </div>
      </div>

      <!-- 箭头2 -->
      <div class="qw-conn" :class="{ 'conn-done': isPast('converted') }">
        <div class="qw-line"></div>
        <div class="qw-point">▶</div>
        <!-- 转订单按钮，在已确认状态显示在箭头上 -->
        <button
          v-if="currentStatus === 'confirmed'"
          class="qw-btn-on-arrow danger"
          :disabled="converting"
          @click="$emit('convert')"
        >
          <el-icon :size="13"><Right /></el-icon>
          <span>{{ converting ? '转换中…' : '转订单' }}</span>
        </button>
      </div>

      <!-- 列3: 已转订单 -->
      <div class="qw-col">
        <div class="qw-card" :class="cardClass('converted')" @click="tryChange('converted')">
          <div class="qw-icon" :class="iconClass('converted')">
            <el-icon v-if="isPast('converted')" :size="16"><Check /></el-icon>
            <span v-else>3</span>
          </div>
          <div class="qw-text">
            <div class="qw-label">已转订单</div>
            <div v-if="'converted' === currentStatus" class="qw-tag cur-tag">当前</div>
            <div v-else-if="isPast('converted')" class="qw-tag done-tag">已完成</div>
          </div>
        </div>
      </div>

      <!-- 预览按钮 -->
      <div class="qw-preview">
        <button class="qw-action outline" @click="$emit('preview')">
          <el-icon :size="14"><View /></el-icon>
          <span>预览</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Check, Edit, CircleCheck, Back, Right, View } from '@element-plus/icons-vue'

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

function tryChange(status: string) {
  if (!isReachable(status) || props.saving || props.converting) return

  // 从草稿 → 已确认
  if (status === 'confirmed' && props.currentStatus === 'draft') {
    emit('confirm')
    return
  }
  // 从已确认 → 已转订单
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
  padding: 24px;
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
  gap: 10px;
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

/* ===== 连接箭头 ===== */
.qw-conn {
  display: flex;
  align-items: center;
  padding: 0 4px;
  flex-shrink: 0;
  margin-top: 24px;
  position: relative;
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

/* ===== 操作按钮 ===== */
.qw-action {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 12px;
  border: none;
  border-radius: 7px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
  line-height: 1;
  outline: none;
}

.qw-action:hover {
  transform: translateY(-1px);
}

.qw-action:active {
  transform: translateY(0);
}

.qw-action:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none !important;
}

.qw-action.primary {
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  color: #fff;
  box-shadow: 0 2px 6px rgba(64,158,255,0.25);
}

.qw-action.primary:hover:not(:disabled) {
  box-shadow: 0 4px 12px rgba(64,158,255,0.35);
}

.qw-action.outline {
  background: var(--ad-card);
  color: var(--ad-text);
  border: 1.5px solid var(--ad-border);
}

.qw-action.outline:hover {
  border-color: #409eff;
  color: #409eff;
  box-shadow: 0 2px 6px rgba(64,158,255,0.1);
}

/* ===== 箭头上按钮 ===== */
.qw-btn-on-arrow {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border: none;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
  line-height: 1;
  outline: none;
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 2;
  color: #fff;
}

.qw-btn-on-arrow:hover {
  transform: translate(-50%, -55%);
}

.qw-btn-on-arrow:active {
  transform: translate(-50%, -50%);
}

.qw-btn-on-arrow:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: translate(-50%, -50%) !important;
}

.qw-btn-on-arrow.success {
  background: linear-gradient(135deg, #52c41a 0%, #73d13d 100%);
  box-shadow: 0 2px 6px rgba(82,196,26,0.25);
}

.qw-btn-on-arrow.warning {
  background: linear-gradient(135deg, #faad14 0%, #ffc53d 100%);
  box-shadow: 0 2px 6px rgba(250,173,20,0.25);
}

.qw-btn-on-arrow.danger {
  background: linear-gradient(135deg, #ff4d4f 0%, #ff7875 100%);
  box-shadow: 0 2px 6px rgba(255,77,79,0.25);
}

/* ===== 预览按钮容器 ===== */
.qw-preview {
  margin-left: 20px;
  padding-left: 20px;
  border-left: 1.5px solid var(--ad-border);
  padding-top: 10px;
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
:root[data-theme="dark"] .qw-action.outline {
  border-color: #434343;
}
:root[data-theme="dark"] .qw-action.outline:hover {
  border-color: #409eff;
}

/* ===== 小屏 ===== */
@media (max-width: 800px) {
  .qw-bar { padding: 14px; }
  .qw-card { padding: 8px 12px; min-width: 60px; min-height: 40px; gap: 8px; }
  .qw-line { width: 20px; }
  .qw-conn { padding: 0 2px; }
  .qw-tag { display: none; }
  .qw-btn-on-arrow { display: none; }
  .qw-preview { margin-left: 0; padding-left: 0; border-left: none; }
}
</style>
