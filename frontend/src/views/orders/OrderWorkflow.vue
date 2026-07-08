<template>
  <div class="ow-bar">
    <div class="ow-flow">
      <!-- 列1: 确认订单 -->
      <div class="ow-col">
        <div class="ow-card" :class="cardClass('confirmed')" @click="tryChange('confirmed')">
          <div class="ow-icon" :class="iconClass('confirmed')">
            <el-icon v-if="isPast('confirmed')" :size="16"><Check /></el-icon>
            <span v-else>1</span>
          </div>
          <div class="ow-text">
            <div class="ow-label">确认订单</div>
            <div v-if="'confirmed' === currentStatus" class="ow-tag cur-tag">当前</div>
            <div v-else-if="isReachable('confirmed')" class="ow-tag ready-tag">可点击</div>
          </div>
        </div>
      </div>

      <!-- 箭头1 -->
      <div class="ow-conn" :class="{ 'conn-done': isPast('in_progress') }">
        <div class="ow-line"></div>
        <div class="ow-point">▶</div>
      </div>

      <!-- 列2: 进行中 / 生产中 / 安装中（竖排） -->
      <div class="ow-col ow-col-stack">
        <div class="ow-card" :class="cardClass('in_progress')" @click="tryChange('in_progress')">
          <div class="ow-icon" :class="iconClass('in_progress')">
            <el-icon v-if="isPast('in_progress')" :size="16"><Check /></el-icon>
            <span v-else>2</span>
          </div>
          <div class="ow-text">
            <div class="ow-label">进行中</div>
            <div v-if="'in_progress' === currentStatus" class="ow-tag cur-tag">当前</div>
            <div v-else-if="isReachable('in_progress')" class="ow-tag ready-tag">可点击</div>
          </div>
        </div>

        <!-- 竖排连接线 -->
        <div class="stack-line" :class="{ 'stack-done': isPast('in_production') || currentStatus === 'in_production' }"></div>

        <div class="ow-card" :class="cardClass('in_production')" @click="tryChange('in_production')">
          <div class="ow-icon" :class="iconClass('in_production')">
            <el-icon v-if="isPast('in_production')" :size="16"><Check /></el-icon>
            <span v-else>3</span>
          </div>
          <div class="ow-text">
            <div class="ow-label">生产中</div>
            <div v-if="'in_production' === currentStatus" class="ow-tag cur-tag">当前</div>
            <div v-else-if="isReachable('in_production')" class="ow-tag ready-tag">可点击</div>
          </div>
        </div>

        <div class="stack-line" :class="{ 'stack-done': isPast('in_installation') || currentStatus === 'in_installation' }"></div>

        <div class="ow-card" :class="cardClass('in_installation')" @click="tryChange('in_installation')">
          <div class="ow-icon" :class="iconClass('in_installation')">
            <el-icon v-if="isPast('in_installation')" :size="16"><Check /></el-icon>
            <span v-else>4</span>
          </div>
          <div class="ow-text">
            <div class="ow-label">安装中</div>
            <div v-if="'in_installation' === currentStatus" class="ow-tag cur-tag">当前</div>
            <div v-else-if="isReachable('in_installation')" class="ow-tag ready-tag">可点击</div>
          </div>
        </div>
      </div>

      <!-- 箭头2 -->
      <div class="ow-conn" :class="{ 'conn-done': isPast('completed') }">
        <div class="ow-line"></div>
        <div class="ow-point">▶</div>
      </div>

      <!-- 列3: 已完成 -->
      <div class="ow-col">
        <div class="ow-card" :class="cardClass('completed')" @click="tryChange('completed')">
          <div class="ow-icon" :class="iconClass('completed')">
            <el-icon v-if="isPast('completed')" :size="16"><Check /></el-icon>
            <span v-else>5</span>
          </div>
          <div class="ow-text">
            <div class="ow-label">已完成</div>
            <div v-if="'completed' === currentStatus" class="ow-tag cur-tag">当前</div>
            <div v-else-if="isReachable('completed')" class="ow-tag ready-tag">可点击</div>
          </div>
        </div>
      </div>

      <!-- 箭头3 -->
      <div class="ow-conn" :class="{ 'conn-done': isPast('cancelled') }">
        <div class="ow-line"></div>
        <div class="ow-point">▶</div>
      </div>

      <!-- 列4: 取消订单 -->
      <div class="ow-col">
        <div class="ow-card" :class="cardClass('cancelled') + ' ' + cancellClass()" @click="tryChange('cancelled')">
          <div class="ow-icon" :class="iconClass('cancelled')">
            <el-icon v-if="isPast('cancelled')" :size="16"><Close /></el-icon>
            <span v-else>6</span>
          </div>
          <div class="ow-text">
            <div class="ow-label">取消订单</div>
            <div v-if="'cancelled' === currentStatus" class="ow-tag cur-tag">已取消</div>
            <div v-else-if="isReachable('cancelled')" class="ow-tag ready-tag">可点击</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Check, Close, CircleCheckFilled } from '@element-plus/icons-vue'

const props = defineProps<{
  currentStatus: string
  changing: boolean
}>()

const emit = defineEmits<{
  change: [status: string]
}>()

const allStatuses = ['pending_confirm', 'confirmed', 'in_progress', 'in_production', 'in_installation', 'completed', 'cancelled']

const currentIdx = computed(() => {
  const idx = allStatuses.indexOf(props.currentStatus)
  return idx >= 0 ? idx : -1
})

const reachableTargets = computed(() => {
  const cur = props.currentStatus
  const idx = currentIdx.value
  if (idx < 0 || cur === 'cancelled' || cur === 'completed') return []
  return allStatuses.slice(idx + 1)
})

function isPast(status: string): boolean {
  const idx = allStatuses.indexOf(status)
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

function cancellClass() {
  const s = props.currentStatus
  if (s === 'cancelled') return 'card-cancelled'
  if (isReachable('cancelled')) return 'card-cancelled-ready'
  return ''
}
</script>

<style scoped>
.ow-bar {
  background: var(--ad-card);
  border: 1px solid var(--ad-border);
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 20px;
}

.ow-flow {
  display: flex;
  align-items: flex-start;
  gap: 0;
}

.ow-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
}

.ow-col-stack {
  gap: 0;
}

/* ===== 卡片（统一大小样式） ===== */
.ow-card {
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

.ow-icon {
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

.ow-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.ow-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--ad-text);
  white-space: nowrap;
  letter-spacing: 0.5px;
}

.ow-tag {
  font-size: 10px;
  font-weight: 500;
  white-space: nowrap;
}
.cur-tag { color: #409eff; }
.ready-tag { color: #409eff; }

/* ===== 竖排连接线 ===== */
.stack-line {
  width: 2px;
  height: 8px;
  background: #e8e8e8;
  margin: 0 auto;
  transition: all 0.3s ease;
}

.stack-done {
  background: linear-gradient(to bottom, #52c41a, #73d13d);
}

/* ===== 连接箭头 ===== */
.ow-conn {
  display: flex;
  align-items: center;
  padding: 0 4px;
  flex-shrink: 0;
  margin-top: 26px; /* 与第一行卡片对齐 */
}

.ow-line {
  width: 36px;
  height: 2px;
  background: #e8e8e8;
  border-radius: 2px;
  transition: all 0.3s ease;
}

.conn-done .ow-line {
  background: linear-gradient(to right, #52c41a, #73d13d);
  height: 3px;
}

.ow-point {
  font-size: 12px;
  color: #d9d9d9;
  margin-left: -2px;
  transition: all 0.3s ease;
}

.conn-done .ow-point {
  color: #73d13d;
}

/* ===== 卡片状态 ===== */

/* 当前 */
.card-current {
  border-color: #409eff;
  background: linear-gradient(135deg, rgba(64,158,255,0.07), rgba(64,158,255,0.03));
  box-shadow: 0 0 0 4px rgba(64,158,255,0.08);
}
.card-current .ow-label { color: #409eff; }

.icon-current {
  background: linear-gradient(135deg, #409eff, #66b1ff);
  color: #fff;
  box-shadow: 0 2px 8px rgba(64,158,255,0.35);
}

/* 已完成 */
.card-done { border-color: transparent; }
.card-done .ow-label { color: #52c41a; }

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
.card-ready .ow-label { color: #409eff; }

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
.card-disabled .ow-label { color: #d9d9d9; }

.icon-disabled {
  background: #f5f5f5;
  color: #d9d9d9;
  border: 2px solid #e8e8e8;
}

/* ===== 取消订单 ===== */
.card-cancelled {
  border-color: #ff4d4f !important;
  background: linear-gradient(135deg, rgba(255,77,79,0.07), rgba(255,77,79,0.03)) !important;
  box-shadow: 0 0 0 4px rgba(255,77,79,0.08) !important;
}
.card-cancelled .ow-label { color: #ff4d4f !important; }

.card-cancelled-ready {
  border-color: #ff4d4f !important;
  border-style: dashed !important;
  background: rgba(255,77,79,0.03) !important;
  cursor: pointer !important;
}
.card-cancelled-ready:hover {
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
:root[data-theme="dark"] .card-disabled .ow-label { color: #434343; }
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
:root[data-theme="dark"] .card-cancelled {
  background: rgba(255,77,79,0.1) !important;
  box-shadow: 0 0 0 4px rgba(255,77,79,0.12) !important;
}
:root[data-theme="dark"] .card-cancelled-ready {
  background: rgba(255,77,79,0.06) !important;
}
:root[data-theme="dark"] .card-cancelled-ready:hover {
  background: rgba(255,77,79,0.15) !important;
}
:root[data-theme="dark"] .ow-line { background: #434343; }
:root[data-theme="dark"] .ow-point { color: #595959; }
:root[data-theme="dark"] .stack-line { background: #434343; }

/* ===== 小屏 ===== */
@media (max-width: 800px) {
  .ow-bar { padding: 14px; }
  .ow-card { padding: 8px 12px; min-width: 60px; min-height: 40px; gap: 8px; }
  .ow-line { width: 16px; }
  .ow-conn { padding: 0 2px; }
  .ow-tag { display: none; }
}
</style>
