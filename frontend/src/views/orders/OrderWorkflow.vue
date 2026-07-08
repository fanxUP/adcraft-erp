<template>
  <div class="ow-bar">
    <!-- ===== 横向：确认订单 → 进行中 → 已完成 → 取消订单 ===== -->
    <div class="ow-horizontal">
      <div
        v-for="(step, idx) in topSteps"
        :key="step.status"
        class="oh-unit"
      >
        <!-- 连接箭头 -->
        <div v-if="idx > 0" class="oh-conn" :class="{ 'conn-done': isPast(step.status) }">
          <div class="oh-line"></div>
          <div class="oh-point">▶</div>
        </div>

        <!-- 节点 -->
        <div
          class="oh-node"
          :class="nodeClass(step.status)"
          @click="tryChange(step.status)"
        >
          <div class="oh-icon" :class="iconClass(step.status)">
            <el-icon v-if="isPast(step.status)" :size="16"><Check /></el-icon>
            <span v-else>{{ step.num }}</span>
          </div>
          <div class="oh-text">
            <div class="oh-label">{{ step.label }}</div>
            <div v-if="step.status === currentStatus" class="oh-badge cur-badge">当前</div>
            <div v-else-if="isReachable(step.status)" class="oh-badge ready-badge">可点击</div>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== 竖向：生产中 / 安装中（在"进行中"下方） ===== -->
    <div class="ow-vertical">
      <div class="ov-branch-start">
        <div class="ov-branch-line"></div>
      </div>

      <div
        v-for="step in bottomSteps"
        :key="step.status"
        class="ov-unit"
      >
        <div class="ov-left">
          <div class="ov-dot" :class="iconClass(step.status)">
            <el-icon v-if="isPast(step.status)" :size="14"><Check /></el-icon>
            <span v-else>{{ step.num }}</span>
          </div>
        </div>
        <div
          class="ov-node"
          :class="nodeClass(step.status)"
          @click="tryChange(step.status)"
        >
          <div class="ov-text">
            <div class="ov-label">{{ step.label }}</div>
            <div v-if="step.status === currentStatus" class="ov-badge cur-badge">当前</div>
            <div v-else-if="isReachable(step.status)" class="ov-badge ready-badge">可点击</div>
          </div>
          <div v-if="isPast(step.status)" class="ov-check">
            <el-icon :size="20" color="#52c41a"><CircleCheckFilled /></el-icon>
          </div>
          <div v-else-if="step.status === currentStatus" class="ov-arrow">
            <el-icon :size="16" color="#409eff"><Right /></el-icon>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Check, Right, CircleCheckFilled } from '@element-plus/icons-vue'

const props = defineProps<{
  currentStatus: string
  changing: boolean
}>()

const emit = defineEmits<{
  change: [status: string]
}>()

interface StepDef { status: string; label: string; num: number }

const topSteps: StepDef[] = [
  { status: 'confirmed', label: '确认订单', num: 1 },
  { status: 'in_progress', label: '进行中', num: 2 },
  { status: 'completed', label: '已完成', num: 3 },
  { status: 'cancelled', label: '取消订单', num: 4 },
]

const bottomSteps: StepDef[] = [
  { status: 'in_production', label: '生产中', num: 5 },
  { status: 'in_installation', label: '安装中', num: 6 },
]

const allStatuses = [...topSteps, ...bottomSteps].map(s => s.status)

const currentIdx = computed(() => {
  const idx = allStatuses.indexOf(props.currentStatus)
  return idx >= 0 ? idx : -1
})

/* 可跳转的目标 */
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

/* ===== 样式类 ===== */
function nodeClass(status: string) {
  if (status === props.currentStatus) {
    if (status === 'cancelled') return 'n-current n-cancelled'
    return 'n-current'
  }
  if (isPast(status)) {
    if (status === 'cancelled') return 'n-done n-cancelled-done'
    return 'n-done'
  }
  if (isReachable(status)) {
    if (status === 'cancelled') return 'n-ready n-cancelled-ready'
    return 'n-ready'
  }
  if (status === 'cancelled') return 'n-disabled n-cancelled-disabled'
  return 'n-disabled'
}

function iconClass(status: string) {
  if (status === props.currentStatus) return 'i-current'
  if (isPast(status)) return 'i-done'
  if (isReachable(status)) return 'i-ready'
  return 'i-disabled'
}

function isCancelled(status: string): boolean {
  return status === 'cancelled'
}
</script>

<style scoped>
.ow-bar {
  background: var(--ad-card);
  border: 1px solid var(--ad-border);
  border-radius: 12px;
  padding: 20px 24px;
  margin-bottom: 20px;
}

/* ============ 横向 ============ */
.ow-horizontal {
  display: flex;
  align-items: center;
  padding-bottom: 6px;
}

.oh-unit {
  display: flex;
  align-items: center;
}

/* 节点卡片 */
.oh-node {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 18px;
  border-radius: 10px;
  border: 2px solid transparent;
  transition: all 0.25s ease;
  cursor: default;
  position: relative;
}

.oh-text {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.oh-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--ad-text);
  white-space: nowrap;
  letter-spacing: 0.5px;
}

.oh-badge {
  font-size: 10px;
  font-weight: 500;
  white-space: nowrap;
}

.cur-badge { color: #409eff; }
.ready-badge { color: #409eff; }

/* 圆形图标 */
.oh-icon {
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

/* 连接箭头 */
.oh-conn {
  display: flex;
  align-items: center;
  width: 40px;
  flex-shrink: 0;
}

.oh-line {
  flex: 1;
  height: 2px;
  background: #e8e8e8;
  border-radius: 2px;
  transition: all 0.3s ease;
}

.conn-done .oh-line {
  background: linear-gradient(to right, #52c41a, #73d13d);
  height: 3px;
}

.oh-point {
  font-size: 12px;
  color: #d9d9d9;
  margin-left: -2px;
  transition: all 0.3s ease;
}

.conn-done .oh-point {
  color: #73d13d;
}

/* ============ 竖向 ============ */
.ow-vertical {
  display: flex;
  flex-direction: column;
  gap: 0;
  padding-left: 40px;
  position: relative;
  margin-top: 4px;
}

/* 分支线：从"进行中"下方开始 */
.ov-branch-start {
  position: absolute;
  left: 40px;
  top: -4px;
}

.ov-branch-line {
  width: 2px;
  height: 12px;
  background: #e8e8e8;
}

.ov-unit {
  display: flex;
  align-items: stretch;
  gap: 12px;
  min-height: 48px;
}

.ov-left {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 20px;
  flex-shrink: 0;
  position: relative;
}

.ov-dot {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
  z-index: 1;
  flex-shrink: 0;
  transition: all 0.25s ease;
}

/* 竖向连接线 */
.ov-unit:not(:last-child) .ov-left::after {
  content: '';
  position: absolute;
  top: 20px;
  left: 50%;
  width: 2px;
  height: calc(100% - 20px);
  background: #e8e8e8;
}

/* 竖向卡片 */
.ov-node {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  border-radius: 8px;
  border: 2px solid transparent;
  transition: all 0.25s ease;
  cursor: default;
  margin: 1px 0;
  max-width: 280px;
}

.ov-text {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.ov-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--ad-text);
  letter-spacing: 0.3px;
}

.ov-badge {
  font-size: 10px;
  font-weight: 500;
}

.ov-check, .ov-arrow {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

/* ============ 节点状态 ============ */

/* 当前 */
.n-current {
  border-color: #409eff;
  background: linear-gradient(135deg, rgba(64,158,255,0.07), rgba(64,158,255,0.03));
  box-shadow: 0 0 0 4px rgba(64,158,255,0.08);
}
.n-current .oh-label,
.n-current .ov-label { color: #409eff; }

.i-current {
  background: linear-gradient(135deg, #409eff, #66b1ff);
  color: #fff;
  box-shadow: 0 2px 8px rgba(64,158,255,0.35);
}

/* 已完成 */
.n-done { border-color: transparent; }
.n-done .oh-label,
.n-done .ov-label { color: #52c41a; }

.i-done {
  background: linear-gradient(135deg, #52c41a, #73d13d);
  color: #fff;
  box-shadow: 0 2px 6px rgba(82,196,26,0.3);
}

/* 可点击（蓝色虚线框） */
.n-ready {
  border-color: #409eff;
  border-style: dashed;
  background: rgba(64,158,255,0.03);
  cursor: pointer;
}
.n-ready:hover {
  background: rgba(64,158,255,0.08);
  box-shadow: 0 2px 10px rgba(64,158,255,0.1);
  transform: translateX(3px);
}
.n-ready:active { transform: translateX(0); }
.n-ready .oh-label,
.n-ready .ov-label { color: #409eff; }

.i-ready {
  background: #f0f5ff;
  color: #409eff;
  border: 2px solid #409eff;
  cursor: pointer;
}
.i-ready:hover {
  background: #e6f0ff;
  box-shadow: 0 0 0 4px rgba(64,158,255,0.15);
}

/* 不可达 */
.n-disabled { border-color: #f0f0f0; background: #fafafa; }
.n-disabled .oh-label,
.n-disabled .ov-label { color: #d9d9d9; }

.i-disabled {
  background: #f5f5f5;
  color: #d9d9d9;
  border: 2px solid #e8e8e8;
}



/* ============ 取消订单特殊颜色 ============ */
.n-cancelled {
  border-color: #ff4d4f !important;
  background: linear-gradient(135deg, rgba(255,77,79,0.07), rgba(255,77,79,0.03)) !important;
  box-shadow: 0 0 0 4px rgba(255,77,79,0.08) !important;
}
.n-cancelled .oh-label { color: #ff4d4f !important; }

.n-cancelled-done {
  border-color: transparent !important;
}
.n-cancelled-done .oh-label { color: #ff4d4f !important; }

.n-cancelled-ready {
  border-color: #ff4d4f !important;
  border-style: dashed !important;
  background: rgba(255,77,79,0.03) !important;
}
.n-cancelled-ready:hover {
  background: rgba(255,77,79,0.08) !important;
  box-shadow: 0 2px 10px rgba(255,77,79,0.1) !important;
}

:root[data-theme=dark] .n-cancelled {
  background: rgba(255,77,79,0.1) !important;
  box-shadow: 0 0 0 4px rgba(255,77,79,0.12) !important;
}
:root[data-theme=dark] .n-cancelled-ready {
  background: rgba(255,77,79,0.06) !important;
}
:root[data-theme=dark] .n-cancelled-ready:hover {
  background: rgba(255,77,79,0.15) !important;
}

/* ============ 暗色 ============ */
:root[data-theme="dark"] .i-disabled {
  background: #262626; color: #434343; border-color: #434343;
}
:root[data-theme="dark"] .i-ready {
  background: rgba(64,158,255,0.12);
}
:root[data-theme="dark"] .i-ready:hover {
  background: rgba(64,158,255,0.2);
}
:root[data-theme="dark"] .n-disabled {
  border-color: #262626; background: #1a1a1a;
}
:root[data-theme="dark"] .n-disabled .oh-label,
:root[data-theme="dark"] .n-disabled .ov-label { color: #434343; }
:root[data-theme="dark"] .n-current {
  background: rgba(64,158,255,0.1);
  box-shadow: 0 0 0 4px rgba(64,158,255,0.12);
}
:root[data-theme="dark"] .n-ready {
  background: rgba(64,158,255,0.06);
}
:root[data-theme="dark"] .n-ready:hover {
  background: rgba(64,158,255,0.15);
}
:root[data-theme="dark"] .oh-line,
:root[data-theme="dark"] .ov-unit:not(:last-child) .ov-left::after {
  background: #434343;
}
:root[data-theme="dark"] .oh-point { color: #595959; }
:root[data-theme="dark"] .ov-branch-line { background: #434343; }

/* ============ 小屏 ============ */
@media (max-width: 700px) {
  .ow-bar { padding: 12px; }
  .oh-node { padding: 8px 10px; }
  .oh-conn { width: 20px; }
  .oh-badge, .ov-badge { display: none; }
  .ow-vertical { padding-left: 20px; }
}
</style>
