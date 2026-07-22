<template>
  <div class="aw-bar">
    <div class="aw-flow">
      <!-- 列1: 草稿 -->
      <div class="aw-col">
        <div class="aw-card" :class="cardClass('draft')" @click="tryChange('draft')">
          <div class="aw-icon" :class="iconClass('draft')">
            <el-icon v-if="isPast('draft')" :size="16"><Check /></el-icon>
            <span v-else>1</span>
          </div>
          <div class="aw-text">
            <div class="aw-label">草稿</div>
            <div v-if="'draft' === currentStatus" class="aw-tag cur-tag">当前</div>
            <div v-else-if="isReachable('draft')" class="aw-tag ready-tag">可点击</div>
          </div>
        </div>
      </div>

      <!-- 箭头1 -->
      <div class="aw-conn" :class="{ 'conn-done': isPast('pending') }">
        <div class="aw-line"></div>
        <div class="aw-point">▶</div>
      </div>

      <!-- 列2: 待验收 -->
      <div class="aw-col">
        <div class="aw-card" :class="cardClass('pending')" @click="tryChange('pending')">
          <div class="aw-icon" :class="iconClass('pending')">
            <el-icon v-if="isPast('pending')" :size="16"><Check /></el-icon>
            <span v-else>2</span>
          </div>
          <div class="aw-text">
            <div class="aw-label">待验收</div>
            <div v-if="'pending' === currentStatus" class="aw-tag cur-tag">当前</div>
            <div v-else-if="isReachable('pending')" class="aw-tag ready-tag">可点击</div>
          </div>
        </div>
      </div>

      <!-- 箭头2 -->
      <div class="aw-conn" :class="{ 'conn-done': isPast('accepted') }">
        <div class="aw-line"></div>
        <div class="aw-point">▶</div>
      </div>

      <!-- 列3: 已验收 -->
      <div class="aw-col">
        <div class="aw-card" :class="cardClass('accepted')" @click="tryChange('accepted')">
          <div class="aw-icon" :class="iconClass('accepted')">
            <el-icon v-if="isPast('accepted')" :size="16"><Check /></el-icon>
            <span v-else>3</span>
          </div>
          <div class="aw-text">
            <div class="aw-label">已验收</div>
            <div v-if="'accepted' === currentStatus" class="aw-tag cur-tag">已通过</div>
            <div v-else-if="isReachable('accepted')" class="aw-tag ready-tag">可点击</div>
          </div>
        </div>
      </div>

      <!-- 箭头3 -->
      <div class="aw-conn" :class="{ 'conn-done': currentStatus === 'rejected' }">
        <div class="aw-line"></div>
        <div class="aw-point">▶</div>
      </div>

      <!-- 列4: 已驳回 -->
      <div class="aw-col">
        <div class="aw-card" :class="cardClass('rejected') + ' ' + rejectClass()" @click="tryChange('rejected')">
          <div class="aw-icon" :class="iconClass('rejected')">
            <el-icon v-if="currentStatus === 'rejected'" :size="16"><Close /></el-icon>
            <span v-else>4</span>
          </div>
          <div class="aw-text">
            <div class="aw-label">驳回</div>
            <div v-if="'rejected' === currentStatus" class="aw-tag cur-tag">已驳回</div>
            <div v-else-if="isReachable('rejected')" class="aw-tag ready-tag">可点击</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Check, Close } from '@element-plus/icons-vue'

const props = defineProps<{
  currentStatus: string
  changing: boolean
}>()

const emit = defineEmits<{
  change: [status: string]
}>()

/** 主线状态（用于判断"已完成"的前置状态） */
const mainFlow = ['draft', 'pending', 'accepted']

const currentIdx = computed(() => {
  const idx = mainFlow.indexOf(props.currentStatus)
  return idx >= 0 ? idx : mainFlow.length // rejected 视为在所有主线状态之后
})

const reachableTargets = computed(() => {
  const cur = props.currentStatus
  if (cur === 'draft') return ['pending']
  if (cur === 'pending') return ['accepted', 'rejected']
  if (cur === 'rejected') return ['draft']
  return [] // accepted 终态
})

function isPast(status: string): boolean {
  // rejected 不属于主线，"已完成"判断仅对主线状态有效
  if (status === 'rejected') return false
  const idx = mainFlow.indexOf(status)
  return idx >= 0 && idx < currentIdx.value
}

function isReachable(status: string): boolean {
  return reachableTargets.value.includes(status)
}

function tryChange(status: string) {
  if (!isReachable(status) || props.changing) return
  emit('change', status)
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

function rejectClass() {
  const s = props.currentStatus
  if (s === 'rejected') return 'card-rejected'
  if (isReachable('rejected')) return 'card-rejected-ready'
  return ''
}
</script>

<style scoped>
.aw-bar {
  background: var(--ad-card);
  border: 1px solid var(--ad-border);
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 20px;
}

.aw-flow {
  display: flex;
  align-items: flex-start;
  gap: 0;
}

.aw-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
}

/* ===== 卡片 ===== */
.aw-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 22px;
  border-radius: 10px;
  border: 2px solid transparent;
  transition: all 0.25s ease;
  cursor: default;
  min-width: 110px;
  min-height: 52px;
  box-sizing: border-box;
}

.aw-icon {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  flex-shrink: 0;
  transition: all 0.25s ease;
}

.aw-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.aw-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--ad-text);
  white-space: nowrap;
  letter-spacing: 0.5px;
}

.aw-tag {
  font-size: 10px;
  font-weight: 500;
  white-space: nowrap;
}
.cur-tag { color: #409eff; }
.ready-tag { color: #409eff; }

/* ===== 连接箭头 ===== */
.aw-conn {
  display: flex;
  align-items: center;
  padding: 0 4px;
  flex-shrink: 0;
  margin-top: 26px;
}

.aw-line {
  width: 36px;
  height: 2px;
  background: #e8e8e8;
  border-radius: 2px;
  transition: all 0.3s ease;
}

.conn-done .aw-line {
  background: linear-gradient(to right, #52c41a, #73d13d);
  height: 3px;
}

.aw-point {
  font-size: 12px;
  color: #d9d9d9;
  margin-left: -2px;
  transition: all 0.3s ease;
}

.conn-done .aw-point {
  color: #73d13d;
}

/* ===== 卡片状态 ===== */

/* 当前 */
.card-current {
  border-color: #409eff;
  background: linear-gradient(135deg, rgba(64,158,255,0.07), rgba(64,158,255,0.03));
  box-shadow: 0 0 0 4px rgba(64,158,255,0.08);
}
.card-current .aw-label { color: #409eff; }

.icon-current {
  background: linear-gradient(135deg, #409eff, #66b1ff);
  color: #fff;
  box-shadow: 0 2px 8px rgba(64,158,255,0.35);
}

/* 已完成 */
.card-done { border-color: transparent; }
.card-done .aw-label { color: #52c41a; }

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
.card-ready .aw-label { color: #409eff; }

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
.card-disabled .aw-label { color: #d9d9d9; }

.icon-disabled {
  background: #f5f5f5;
  color: #d9d9d9;
  border: 2px solid #e8e8e8;
}

/* ===== 驳回 ===== */
.card-rejected {
  border-color: #ff4d4f !important;
  background: linear-gradient(135deg, rgba(255,77,79,0.07), rgba(255,77,79,0.03)) !important;
  box-shadow: 0 0 0 4px rgba(255,77,79,0.08) !important;
}
.card-rejected .aw-label { color: #ff4d4f !important; }

.card-rejected-ready {
  border-color: #ff4d4f !important;
  border-style: dashed !important;
  background: rgba(255,77,79,0.03) !important;
  cursor: pointer !important;
}
.card-rejected-ready:hover {
  background: rgba(255,77,79,0.08) !important;
  box-shadow: 0 2px 10px rgba(255,77,79,0.1) !important;
  transform: translateX(3px) !important;
}

/* ===== 暗色 ===== */
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
:root[data-theme="dark"] .card-disabled .aw-label { color: #434343; }
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
:root[data-theme="dark"] .card-rejected {
  background: rgba(255,77,79,0.1) !important;
  box-shadow: 0 0 0 4px rgba(255,77,79,0.12) !important;
}
:root[data-theme="dark"] .card-rejected-ready {
  background: rgba(255,77,79,0.06) !important;
}
:root[data-theme="dark"] .card-rejected-ready:hover {
  background: rgba(255,77,79,0.15) !important;
}
:root[data-theme="dark"] .aw-line { background: #434343; }
:root[data-theme="dark"] .aw-point { color: #595959; }

/* ===== 小屏 ===== */
@media (max-width: 800px) {
  .aw-bar { padding: 14px; }
  .aw-card { padding: 8px 12px; min-width: 60px; min-height: 40px; gap: 8px; }
  .aw-line { width: 16px; }
  .aw-conn { padding: 0 2px; }
  .aw-tag { display: none; }
}
</style>
