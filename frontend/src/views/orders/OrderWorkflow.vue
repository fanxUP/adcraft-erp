<template>
  <div class="ow-bar">
    <div class="ow-title">订单状态</div>
    <div class="ow-flow">
      <div
        v-for="(step, idx) in allSteps"
        :key="step.status"
        class="ow-row"
        :class="rowClass(step.status)"
      >
        <!-- 左侧竖线 + 节点圆 -->
        <div class="ow-track">
          <div class="track-line" :class="{ 'line-done': idx <= currentIdx }"></div>
          <div
            class="track-dot"
            :class="dotClass(step.status)"
            @click="tryChange(step.status)"
          >
            <el-icon v-if="isPast(step.status)" :size="16"><Check /></el-icon>
            <span v-else>{{ idx + 1 }}</span>
          </div>
        </div>

        <!-- 右侧状态框 -->
        <div
          class="ow-box"
          :class="boxClass(step.status)"
          @click="tryChange(step.status)"
        >
          <div class="box-left">
            <div class="box-label">{{ step.label }}</div>
            <div class="box-desc">{{ boxDesc(step.status) }}</div>
          </div>
          <div class="box-right">
            <el-icon v-if="isPast(step.status) && step.status !== currentStatus" :size="20" class="check-icon"><CircleCheckFilled /></el-icon>
            <el-icon v-else-if="step.status === currentStatus" :size="18" class="cur-arrow"><Right /></el-icon>
          </div>
        </div>
      </div>
    </div>

    <!-- 取消按钮 -->
    <div v-if="currentStatus !== 'cancelled' && currentStatus !== 'completed'" class="ow-cancel">
      <div class="ow-row cancel-row" @click="tryChange('cancelled')">
        <div class="ow-track">
          <div class="track-line line-cancel-top"></div>
          <div class="track-dot dot-cancel">
            <el-icon :size="16"><Close /></el-icon>
          </div>
          <div class="track-line line-cancel-bot"></div>
        </div>
        <div class="ow-box box-cancel">
          <div class="box-left">
            <div class="box-label cancel-label">取消订单</div>
            <div class="box-desc cancel-desc">终止此订单所有流程</div>
          </div>
          <div class="box-right">
            <el-icon :size="18" class="cur-arrow"><Right /></el-icon>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Check, Close, Right, CircleCheckFilled } from '@element-plus/icons-vue'

const props = defineProps<{
  currentStatus: string
  changing: boolean
}>()

const emit = defineEmits<{
  change: [status: string]
}>()

interface StepDef { status: string; label: string }

const allSteps: StepDef[] = [
  { status: 'pending_confirm', label: '待确认' },
  { status: 'confirmed', label: '已确认' },
  { status: 'in_progress', label: '进行中' },
  { status: 'in_production', label: '生产中' },
  { status: 'in_installation', label: '安装中' },
  { status: 'completed', label: '已完成' },
]

const statusOrder = allSteps.map(s => s.status)

const currentIdx = computed(() => statusOrder.indexOf(props.currentStatus))

/* 可从当前状态跳转到任意更靠后的状态 + cancelled */
const reachable = computed(() => {
  const cur = props.currentStatus
  if (cur === 'cancelled' || cur === 'completed') return []
  // 可流转到所有后续状态（允许跳过）
  const targets = allSteps
    .filter(s => statusOrder.indexOf(s.status) > currentIdx.value)
    .map(s => s.status)
  // 加上cancelled
  targets.push('cancelled')
  return targets
})

function isPast(status: string): boolean {
  return statusOrder.indexOf(status) < currentIdx.value
}

function isReachable(status: string): boolean {
  return reachable.value.includes(status)
}

function tryChange(status: string) {
  if (!isReachable(status)) return
  if (props.changing) return
  emit('change', status)
}

/* 样式类 */
function rowClass(status: string) {
  if (status === props.currentStatus) return 'row-current'
  if (isPast(status)) return 'row-done'
  return 'row-future'
}

function dotClass(status: string) {
  if (status === props.currentStatus) return 'dot-current'
  if (isPast(status)) return 'dot-done'
  if (isReachable(status)) return 'dot-ready'
  return 'dot-disabled'
}

function boxClass(status: string) {
  if (status === props.currentStatus) return 'box-current'
  if (isPast(status)) return 'box-done'
  if (isReachable(status)) return 'box-ready'
  return 'box-disabled'
}

function boxDesc(status: string): string {
  if (status === props.currentStatus) {
    const map: Record<string, string> = {
      pending_confirm: '等待确认',
      confirmed: '已确认，可开始制作',
      in_progress: '可进入生产或安装',
      in_production: '生产中',
      in_installation: '安装中',
      completed: '订单已完成',
    }
    return map[status] || ''
  }
  if (isPast(status)) return '已完成'
  if (isReachable(status)) return '点击跳转至此状态'
  return ''
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

.ow-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--ad-text);
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--ad-border);
  letter-spacing: 0.5px;
}

.ow-flow {
  display: flex;
  flex-direction: column;
  gap: 0;
}

/* ===== 单行 ===== */
.ow-row {
  display: flex;
  align-items: stretch;
  gap: 16px;
  min-height: 64px;
}

/* ===== 左侧轨道 ===== */
.ow-track {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 32px;
  flex-shrink: 0;
  position: relative;
}

.track-line {
  flex: 1;
  width: 2px;
  background: #e8e8e8;
  transition: all 0.3s ease;
}

.line-done {
  background: linear-gradient(to bottom, #52c41a, #73d13d);
}

.track-dot {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  z-index: 1;
  flex-shrink: 0;
  transition: all 0.25s ease;
  cursor: default;
}

/* 圆点状态 */
.dot-current {
  background: linear-gradient(135deg, #409eff, #66b1ff);
  color: #fff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.35);
  cursor: default;
}

.dot-done {
  background: linear-gradient(135deg, #52c41a, #73d13d);
  color: #fff;
  box-shadow: 0 2px 6px rgba(82, 196, 26, 0.3);
  cursor: default;
}

.dot-ready {
  background: #f0f5ff;
  color: #409eff;
  border: 2px solid #409eff;
  cursor: pointer;
}

.dot-ready:hover {
  background: #e6f0ff;
  box-shadow: 0 0 0 4px rgba(64, 158, 255, 0.15);
}

.dot-disabled {
  background: #f5f5f5;
  color: #d9d9d9;
  border: 2px solid #e8e8e8;
  cursor: default;
}

/* ===== 右侧状态框 ===== */
.ow-box {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 18px;
  border-radius: 10px;
  border: 2px solid transparent;
  transition: all 0.25s ease;
  cursor: default;
  margin-bottom: 4px;
  margin-top: 4px;
}

.box-left {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.box-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--ad-text);
  letter-spacing: 0.3px;
}

.box-desc {
  font-size: 11px;
  color: var(--ad-text-secondary, #8c8c8c);
}

.box-right {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.check-icon {
  color: #52c41a;
}

.cur-arrow {
  color: #409eff;
}

/* 当前状态框 */
.box-current {
  border-color: #409eff;
  background: linear-gradient(135deg, rgba(64, 158, 255, 0.07), rgba(64, 158, 255, 0.03));
  box-shadow: 0 0 0 4px rgba(64, 158, 255, 0.08), 0 2px 6px rgba(64, 158, 255, 0.06);
}

.box-current .box-label { color: #409eff; }
.box-current .box-desc { color: #409eff; }

/* 已完成框 */
.box-done {
  border-color: transparent;
  background: transparent;
}

.box-done .box-label { color: #52c41a; }
.box-done .box-desc { color: #52c41a; }

/* 可跳转框 */
.box-ready {
  border-color: #409eff;
  border-style: dashed;
  background: rgba(64, 158, 255, 0.03);
  cursor: pointer;
}

.box-ready:hover {
  background: rgba(64, 158, 255, 0.08);
  box-shadow: 0 2px 12px rgba(64, 158, 255, 0.12);
  transform: translateX(3px);
}

.box-ready:active {
  transform: translateX(1px);
}

.box-ready .box-label { color: #409eff; }
.box-ready .box-desc { color: #409eff; }

/* 不可达框 */
.box-disabled {
  border-color: #f0f0f0;
  background: #fafafa;
}

.box-disabled .box-label { color: #d9d9d9; }
.box-disabled .box-desc { color: #e8e8e8; }

/* ===== 取消行 ===== */
.ow-cancel {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--ad-border);
}

.cancel-row {
  cursor: pointer;
}

.line-cancel-top {
  height: 8px;
  flex: none;
  background: transparent;
}

.line-cancel-bot {
  flex: 1;
  background: transparent;
}

.dot-cancel {
  background: transparent;
  color: #ff4d4f;
  border: 2px solid #ff4d4f;
  cursor: pointer;
}

.dot-cancel:hover {
  background: #fff1f0;
  box-shadow: 0 0 0 4px rgba(255, 77, 79, 0.12);
}

.box-cancel {
  border-color: #ff4d4f;
  border-style: dashed;
  cursor: pointer;
}

.box-cancel:hover {
  background: #fff1f0;
  transform: translateX(3px);
}

.box-cancel:active {
  transform: translateX(1px);
}

.cancel-label {
  color: #ff4d4f !important;
}

.cancel-desc {
  color: #ff7875 !important;
}

/* ===== 暗色主题 ===== */
:root[data-theme="dark"] .dot-disabled {
  background: #262626;
  color: #434343;
  border-color: #434343;
}

:root[data-theme="dark"] .dot-ready {
  background: rgba(64, 158, 255, 0.12);
  border-color: #409eff;
}

:root[data-theme="dark"] .dot-ready:hover {
  background: rgba(64, 158, 255, 0.2);
}

:root[data-theme="dark"] .box-disabled {
  border-color: #262626;
  background: #1a1a1a;
}
:root[data-theme="dark"] .box-disabled .box-label { color: #434343; }
:root[data-theme="dark"] .box-disabled .box-desc { color: #333; }

:root[data-theme="dark"] .box-current {
  background: rgba(64, 158, 255, 0.1);
  box-shadow: 0 0 0 4px rgba(64, 158, 255, 0.12);
}

:root[data-theme="dark"] .box-ready {
  background: rgba(64, 158, 255, 0.06);
}

:root[data-theme="dark"] .box-ready:hover {
  background: rgba(64, 158, 255, 0.15);
}

:root[data-theme="dark"] .box-cancel:hover {
  background: rgba(255, 77, 79, 0.1);
}

:root[data-theme="dark"] .dot-cancel:hover {
  background: rgba(255, 77, 79, 0.15);
}

:root[data-theme="dark"] .track-line {
  background: #434343;
}

/* ===== 小屏 ===== */
@media (max-width: 640px) {
  .ow-bar { padding: 14px 12px; }
  .ow-box { padding: 10px 12px; }
  .box-desc { display: none; }
}
</style>
