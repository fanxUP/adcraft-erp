<template>
  <div class="ow-bar">
    <div class="ow-steps">
      <!-- ====== 各步骤节点 ====== -->
      <template v-for="(step, idx) in flowSteps" :key="step.status">
        <!-- 连接箭头 -->
        <div v-if="idx > 0" class="ow-connector" :class="{ 'conn-done': isPast(step.status) }">
          <div class="conn-line"></div>
          <div class="conn-arrow">›</div>

          <!-- 箭头上的操作按钮：取当前节点的前一个状态的可用流转 -->
          <div
            v-if="showActionOnArrow(step.status)"
            class="conn-action-area"
          >
            <button
              v-if="canTransitTo(step.status) && !isMultiTarget(idx)"
              class="ow-btn next-btn"
              :class="btnClass(step.status)"
              :disabled="changing"
              @click="handleChange(step.status)"
            >
              <el-icon :size="13"><component :is="actionIcon(step.status)" /></el-icon>
              <span>{{ actionLabel(step.status) }}</span>
            </button>

            <!-- 多目标节点（in_progress 分支） -->
            <div v-else-if="isMultiTarget(idx)" class="branch-group">
              <button
                v-for="target in branchTargets"
                :key="target.status"
                class="ow-btn branch-btn"
                :class="btnClass(target.status)"
                :disabled="changing"
                @click="handleChange(target.status)"
              >
                <el-icon :size="13"><component :is="actionIcon(target.status)" /></el-icon>
                <span>{{ actionLabel(target.status) }}</span>
              </button>
            </div>
          </div>
        </div>

        <!-- 节点 -->
        <div class="ow-node" :class="nodeClass(step.status)">
          <div class="ow-badge" :class="badgeClass(step.status)">
            <el-icon v-if="isPast(step.status)" :size="14"><Check /></el-icon>
            <span v-else>{{ step.num }}</span>
          </div>
          <div class="ow-labels">
            <div class="ow-label">{{ step.label }}</div>
            <div v-if="step.status === currentStatus && !isPast(step.status)" class="ow-hint">
              <template v-if="currentStatus === 'in_progress'">选择下一步</template>
              <template v-else-if="currentStatus === 'pending_confirm'">待确认</template>
              <template v-else-if="currentStatus === 'completed'">已完成</template>
            </div>
          </div>
          <div v-if="step.status === currentStatus && !isPast(step.status)" class="ow-dot"></div>
        </div>
      </template>

      <!-- 取消按钮（分隔线右侧） -->
      <div v-if="currentStatus !== 'cancelled' && currentStatus !== 'completed'" class="ow-cancel-wrap">
        <div class="cancel-divider"></div>
        <button
          class="ow-btn cancel-btn"
          :disabled="changing"
          @click="handleChange('cancelled')"
        >
          <el-icon :size="14"><Close /></el-icon>
          <span>取消订单</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Check, Close, CircleCheck, Right, Promotion, Tickets, Finished } from '@element-plus/icons-vue'

const props = defineProps<{
  currentStatus: string
  changing: boolean
}>()

const emit = defineEmits<{
  change: [status: string]
}>()

function handleChange(status: string) {
  if (!props.changing) emit('change', status)
}

/* 流程定义 */
interface FlowStep {
  status: string
  label: string
  num: number
}

const flowSteps: FlowStep[] = [
  { status: 'pending_confirm', label: '待确认', num: 1 },
  { status: 'confirmed', label: '已确认', num: 2 },
  { status: 'in_progress', label: '进行中', num: 3 },
  { status: 'in_production', label: '生产中', num: 4 },
  { status: 'in_installation', label: '安装中', num: 5 },
  { status: 'completed', label: '已完成', num: 6 },
]

const stepStatuses = flowSteps.map(s => s.status)

/* 当前状态可流转到的目标 */
const allowedTargets = computed(() => {
  const map: Record<string, string[]> = {
    pending_confirm: ['confirmed', 'cancelled'],
    confirmed: ['in_progress', 'cancelled'],
    in_progress: ['in_production', 'in_installation', 'completed', 'cancelled'],
    in_production: ['in_installation', 'completed', 'cancelled'],
    in_installation: ['completed', 'cancelled'],
    completed: ['cancelled'],
    cancelled: [],
  }
  return map[props.currentStatus] || []
})

function isPast(status: string): boolean {
  const idx = stepStatuses.indexOf(status)
  const cur = stepStatuses.indexOf(props.currentStatus)
  return cur > idx
}

function nodeClass(status: string) {
  if (status === props.currentStatus) return 'ow-current'
  if (isPast(status)) return 'ow-done'
  return 'ow-future'
}

function badgeClass(status: string) {
  if (status === props.currentStatus) return 'badge-cur'
  if (isPast(status)) return 'badge-done'
  return 'badge-fut'
}

/* 判断箭头上的按钮是否应该显示 */
function showActionOnArrow(status: string): boolean {
  // 前一个节点是当前状态时，显示可操作按钮
  const prevIdx = stepStatuses.indexOf(status) - 1
  if (prevIdx < 0) return false
  const prevStatus = stepStatuses[prevIdx]
  return prevStatus === props.currentStatus
}

function canTransitTo(status: string): boolean {
  return allowedTargets.value.includes(status)
}

/* 多目标分支：in_progress → in_production | in_installation | completed */
const branchTargets = computed(() => {
  return allowedTargets.value.filter(s =>
    ['in_production', 'in_installation', 'completed'].includes(s)
  )
})

function isMultiTarget(idx: number): boolean {
  const status = flowSteps[idx]?.status
  if (!status) return false
  const prevIdx = stepStatuses.indexOf(status) - 1
  if (prevIdx < 0) return false
  const prevStatus = stepStatuses[prevIdx]
  if (prevStatus !== props.currentStatus) return false
  return branchTargets.value.length > 1
}

/* 按钮样式 & 文案 */
function btnClass(status: string): string {
  const map: Record<string, string> = {
    confirmed: 'btn-primary',
    in_progress: 'btn-primary',
    in_production: 'btn-info',
    in_installation: 'btn-warning',
    completed: 'btn-success',
    cancelled: 'btn-danger',
  }
  return map[status] || 'btn-primary'
}

function actionIcon(status: string) {
  const map: Record<string, any> = {
    confirmed: CircleCheck,
    in_progress: Right,
    in_production: Tickets,
    in_installation: Promotion,
    completed: Finished,
    cancelled: Close,
  }
  return map[status] || Right
}

function actionLabel(status: string): string {
  const map: Record<string, string> = {
    confirmed: '确认订单',
    in_progress: '开始制作',
    in_production: '生产中',
    in_installation: '安装中',
    completed: '完成',
    cancelled: '取消订单',
  }
  return map[status] || status
}
</script>

<style scoped>
.ow-bar {
  background: var(--ad-card);
  border: 1px solid var(--ad-border);
  border-radius: 12px;
  padding: 16px 20px;
  margin-bottom: 20px;
  overflow-x: auto;
}

.ow-steps {
  display: flex;
  align-items: center;
  gap: 0;
  min-width: fit-content;
}

/* ===== 节点 ===== */
.ow-node {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  padding: 6px 10px;
  border-radius: 8px;
  border: 2px solid transparent;
  transition: all 0.3s ease;
  position: relative;
}

.ow-current {
  border-color: #409eff;
  background: rgba(64, 158, 255, 0.06);
  box-shadow: 0 0 0 3px rgba(64, 158, 255, 0.08);
}

.ow-done { opacity: 0.85; }
.ow-future { opacity: 0.45; }

.ow-labels {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.ow-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--ad-text);
  white-space: nowrap;
  letter-spacing: 0.3px;
}

.ow-future .ow-label { color: #bfbfbf; }
.ow-done .ow-label { color: #52c41a; }
.ow-current .ow-label { color: #409eff; }

.ow-hint {
  font-size: 10px;
  color: #409eff;
  font-weight: 500;
  white-space: nowrap;
}

/* ===== 徽章 ===== */
.ow-badge {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
  transition: all 0.3s ease;
}

.badge-cur {
  background: linear-gradient(135deg, #409eff, #66b1ff);
  color: #fff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.35);
}

.badge-done {
  background: linear-gradient(135deg, #52c41a, #73d13d);
  color: #fff;
  box-shadow: 0 2px 6px rgba(82, 196, 26, 0.3);
}

.badge-fut {
  background: #f5f5f5;
  color: #bfbfbf;
  border: 2px solid #e8e8e8;
}

/* 当前节点脉冲点 */
.ow-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #409eff;
  animation: dot-pulse 1.5s ease-in-out infinite;
}

@keyframes dot-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.3; transform: scale(1.8); }
}

/* ===== 连接器 ===== */
.ow-connector {
  display: flex;
  align-items: center;
  position: relative;
  min-width: 44px;
  height: 54px;
  flex-shrink: 0;
}

.conn-line {
  flex: 1;
  height: 2px;
  background: #e8e8e8;
  border-radius: 2px;
  transition: all 0.3s ease;
}

.conn-done .conn-line {
  background: linear-gradient(to right, #52c41a, #73d13d);
  height: 3px;
}

.conn-arrow {
  font-size: 18px;
  color: #d9d9d9;
  line-height: 1;
  font-weight: 300;
  margin-left: -1px;
  transition: all 0.3s ease;
}

.conn-done .conn-arrow {
  color: #73d13d;
  font-size: 20px;
}

/* 连接器上的按钮 */
.conn-action-area {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 2;
}

/* 分支按钮组 */
.branch-group {
  display: flex;
  gap: 4px;
  white-space: nowrap;
}

.branch-btn {
  font-size: 11px !important;
  padding: 3px 8px !important;
}

/* ===== 自定义按钮 ===== */
.ow-btn {
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

.ow-btn:hover { transform: translateY(-1px); }
.ow-btn:active { transform: translateY(0); }
.ow-btn:disabled { opacity: 0.55; cursor: not-allowed; transform: none !important; }

.next-btn { padding: 5px 14px; }

.btn-primary {
  background: linear-gradient(135deg, #409eff, #66b1ff);
  color: #fff;
  box-shadow: 0 2px 6px rgba(64, 158, 255, 0.25);
}
.btn-primary:hover:not(:disabled) { box-shadow: 0 4px 12px rgba(64, 158, 255, 0.35); }

.btn-info {
  background: linear-gradient(135deg, #909399, #b0b3b8);
  color: #fff;
  box-shadow: 0 2px 6px rgba(144, 147, 153, 0.25);
}
.btn-info:hover:not(:disabled) { box-shadow: 0 4px 12px rgba(144, 147, 153, 0.35); }

.btn-warning {
  background: linear-gradient(135deg, #e6a23c, #f5b85c);
  color: #fff;
  box-shadow: 0 2px 6px rgba(230, 162, 60, 0.25);
}
.btn-warning:hover:not(:disabled) { box-shadow: 0 4px 12px rgba(230, 162, 60, 0.35); }

.btn-success {
  background: linear-gradient(135deg, #52c41a, #73d13d);
  color: #fff;
  box-shadow: 0 2px 6px rgba(82, 196, 26, 0.25);
}
.btn-success:hover:not(:disabled) { box-shadow: 0 4px 12px rgba(82, 196, 26, 0.35); }

.btn-danger {
  background: linear-gradient(135deg, #ff4d4f, #ff7875);
  color: #fff;
  box-shadow: 0 2px 6px rgba(255, 77, 79, 0.25);
}
.btn-danger:hover:not(:disabled) { box-shadow: 0 4px 12px rgba(255, 77, 79, 0.35); }

/* ===== 取消按钮区域 ===== */
.ow-cancel-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-left: 14px;
  padding-left: 14px;
  flex-shrink: 0;
}

.cancel-divider {
  width: 1.5px;
  height: 32px;
  background: var(--ad-border);
  border-radius: 2px;
}

.cancel-btn {
  padding: 6px 14px;
  font-size: 12px;
  background: transparent;
  color: #ff4d4f;
  border: 1.5px solid #ff4d4f;
  border-radius: 7px;
}
.cancel-btn:hover:not(:disabled) {
  background: #fff1f0;
  box-shadow: 0 2px 8px rgba(255, 77, 79, 0.15);
  border-color: #ff4d4f;
}

/* ===== 暗色主题 ===== */
:root[data-theme="dark"] .badge-fut {
  background: #262626;
  color: #595959;
  border-color: #434343;
}

:root[data-theme="dark"] .ow-future { opacity: 0.4; }
:root[data-theme="dark"] .ow-future .ow-label { color: #595959; }

:root[data-theme="dark"] .ow-current {
  background: rgba(64, 158, 255, 0.1);
  box-shadow: 0 0 0 3px rgba(64, 158, 255, 0.12);
}

:root[data-theme="dark"] .conn-line { background: #434343; }
:root[data-theme="dark"] .conn-arrow { color: #595959; }

:root[data-theme="dark"] .cancel-btn {
  color: #ff7875;
  border-color: #ff7875;
}
:root[data-theme="dark"] .cancel-btn:hover:not(:disabled) {
  background: rgba(255, 120, 117, 0.1);
}

/* ===== 小屏 ===== */
@media (max-width: 900px) {
  .ow-bar { padding: 12px 14px; }
  .ow-connector { min-width: 28px; }
  .conn-action-area { display: none; }
  .branch-group { display: none; }
  .ow-cancel-wrap { margin-left: 8px; padding-left: 8px; }
  .cancel-btn { font-size: 11px; padding: 4px 10px; }
}
</style>
