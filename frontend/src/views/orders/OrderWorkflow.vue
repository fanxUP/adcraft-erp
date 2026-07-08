<template>
  <div class="ow-bar">
    <div class="ow-title">订单状态</div>

    <!-- ===== 横向主流程：待确认 → 已确认 → 进行中 ===== -->
    <div class="ow-horizontal">
      <div
        v-for="(step, idx) in topSteps"
        :key="step.status"
        class="oh-row"
      >
        <!-- 连接箭头 -->
        <div v-if="idx > 0" class="oh-connector" :class="{ 'conn-done': isPast(step.status) }">
          <div class="oh-line"></div>
          <div class="oh-arrow">›</div>
        </div>

        <!-- 状态卡片 -->
        <div
          class="oh-card"
          :class="cardClass(step.status)"
          @click="tryChange(step.status)"
        >
          <div class="oh-badge" :class="badgeClass(step.status)">
            <el-icon v-if="isPast(step.status)" :size="16"><Check /></el-icon>
            <span v-else>{{ step.num }}</span>
          </div>
          <div class="oh-body">
            <div class="oh-label">{{ step.label }}</div>
            <div class="oh-desc">{{ cardDesc(step.status) }}</div>
          </div>
          <div v-if="step.status === currentStatus" class="oh-cur-dot"></div>
        </div>
      </div>
    </div>

    <!-- ===== 竖向分支：生产中 / 安装中 / 已完成 ===== -->
    <div class="ow-vertical">
      <div
        v-for="(step, idx) in bottomSteps"
        :key="step.status"
        class="ov-row"
      >
        <!-- 左侧竖线 -->
        <div class="ov-track">
          <div class="ov-line" :class="{ 'ov-line-done': isPast(step.status) }"></div>
          <div
            class="ov-dot"
            :class="dotClass(step.status)"
            @click="tryChange(step.status)"
          >
            <el-icon v-if="isPast(step.status)" :size="14"><Check /></el-icon>
            <span v-else>{{ step.num }}</span>
          </div>
        </div>

        <!-- 右侧卡片 -->
        <div
          class="ov-card"
          :class="cardClass(step.status)"
          @click="tryChange(step.status)"
        >
          <div class="ov-body">
            <div class="ov-label">{{ step.label }}</div>
            <div class="ov-desc">{{ cardDesc(step.status) }}</div>
          </div>
          <div class="ov-right">
            <el-icon v-if="isPast(step.status)" :size="20" class="ov-check"><CircleCheckFilled /></el-icon>
            <el-icon v-else-if="step.status === currentStatus" :size="16" class="ov-arr"><Right /></el-icon>
            <span v-else-if="isReachable(step.status)" class="ov-hint">可跳转</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== 取消按钮 ===== -->
    <div v-if="currentStatus !== 'cancelled' && currentStatus !== 'completed'" class="ow-cancel" @click="tryChange('cancelled')">
      <div class="cancel-card">
        <el-icon :size="16"><Close /></el-icon>
        <span>取消订单</span>
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

/* 步骤定义 */
interface StepDef { status: string; label: string; num: number }

const topSteps: StepDef[] = [
  { status: 'pending_confirm', label: '待确认', num: 1 },
  { status: 'confirmed', label: '已确认', num: 2 },
  { status: 'in_progress', label: '进行中', num: 3 },
]

const bottomSteps: StepDef[] = [
  { status: 'in_production', label: '生产中', num: 4 },
  { status: 'in_installation', label: '安装中', num: 5 },
  { status: 'completed', label: '已完成', num: 6 },
]

const allStatuses = [...topSteps, ...bottomSteps].map(s => s.status)

const currentIdx = computed(() => allStatuses.indexOf(props.currentStatus))

/* 可跳转的目标 */
const reachable = computed(() => {
  const cur = props.currentStatus
  if (cur === 'cancelled' || cur === 'completed') return []
  const targets: string[] = []
  for (const s of allStatuses) {
    if (allStatuses.indexOf(s) > currentIdx.value) targets.push(s)
  }
  return targets
})

function isPast(status: string): boolean {
  return allStatuses.indexOf(status) < currentIdx.value
}

function isReachable(status: string): boolean {
  return reachable.value.includes(status)
}

function isDisabled(status: string): boolean {
  return !isPast(status) && !isReachable(status) && status !== props.currentStatus
}

function tryChange(status: string) {
  if (!isReachable(status)) return
  if (props.changing) return
  emit('change', status)
}

/* ===== 样式类 ===== */
function cardClass(status: string) {
  if (status === props.currentStatus) return 'c-current'
  if (isPast(status)) return 'c-done'
  if (isReachable(status)) return 'c-ready'
  return 'c-disabled'
}

function badgeClass(status: string) {
  if (status === props.currentStatus) return 'b-current'
  if (isPast(status)) return 'b-done'
  if (isReachable(status)) return 'b-ready'
  return 'b-disabled'
}

function dotClass(status: string) {
  if (status === props.currentStatus) return 'd-current'
  if (isPast(status)) return 'd-done'
  if (isReachable(status)) return 'd-ready'
  return 'd-disabled'
}

function cardDesc(status: string): string {
  if (status === props.currentStatus) return '当前状态'
  if (isPast(status)) return '已完成'
  if (isReachable(status)) return '点击直接跳转'
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
  margin-bottom: 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--ad-border);
}

/* ============ 横向区域 ============ */
.ow-horizontal {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px dashed var(--ad-border);
}

.oh-row {
  display: flex;
  align-items: center;
}

/* 卡片 */
.oh-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 18px;
  border-radius: 10px;
  border: 2px solid transparent;
  transition: all 0.25s ease;
  cursor: default;
  min-width: 100px;
  position: relative;
}

.oh-body {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.oh-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--ad-text);
  white-space: nowrap;
  letter-spacing: 0.3px;
}

.oh-desc {
  font-size: 10px;
  color: var(--ad-text-secondary, #8c8c8c);
  white-space: nowrap;
}

/* 横向当前脉冲点 */
.oh-cur-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #409eff;
  animation: pulse 1.5s ease-in-out infinite;
  position: absolute;
  top: 6px;
  right: 6px;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.3; transform: scale(1.8); }
}

/* 徽章 */
.oh-badge {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
  transition: all 0.25s ease;
}

.b-current {
  background: linear-gradient(135deg, #409eff, #66b1ff);
  color: #fff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.35);
}

.b-done {
  background: linear-gradient(135deg, #52c41a, #73d13d);
  color: #fff;
  box-shadow: 0 2px 6px rgba(82, 196, 26, 0.3);
}

.b-ready {
  background: #f0f5ff;
  color: #409eff;
  border: 2px solid #409eff;
}

.b-disabled {
  background: #f5f5f5;
  color: #d9d9d9;
  border: 2px solid #e8e8e8;
}

/* 连接器 */
.oh-connector {
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

.oh-arrow {
  font-size: 16px;
  color: #d9d9d9;
  line-height: 1;
  font-weight: 300;
  margin-left: -1px;
  transition: all 0.3s ease;
}

.conn-done .oh-arrow {
  color: #73d13d;
  font-size: 18px;
}

/* ============ 竖向区域 ============ */
.ow-vertical {
  display: flex;
  flex-direction: column;
  gap: 0;
  padding-left: 18px;
  margin-bottom: 12px;
}

.ov-row {
  display: flex;
  align-items: stretch;
  gap: 14px;
  min-height: 56px;
}

/* 竖线 */
.ov-track {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 24px;
  flex-shrink: 0;
}

.ov-line {
  flex: 1;
  width: 2px;
  background: #e8e8e8;
  transition: all 0.3s ease;
}

.ov-line-done {
  background: linear-gradient(to bottom, #52c41a, #73d13d);
}

/* 圆点 */
.ov-dot {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  z-index: 1;
  flex-shrink: 0;
  transition: all 0.25s ease;
  cursor: default;
}

.d-current {
  background: linear-gradient(135deg, #409eff, #66b1ff);
  color: #fff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.35);
}

.d-done {
  background: linear-gradient(135deg, #52c41a, #73d13d);
  color: #fff;
  box-shadow: 0 2px 6px rgba(82, 196, 26, 0.3);
}

.d-ready {
  background: #f0f5ff;
  color: #409eff;
  border: 2px solid #409eff;
  cursor: pointer;
}
.d-ready:hover {
  background: #e6f0ff;
  box-shadow: 0 0 0 4px rgba(64, 158, 255, 0.15);
}

.d-disabled {
  background: #f5f5f5;
  color: #d9d9d9;
  border: 2px solid #e8e8e8;
}

/* 竖向卡片 */
.ov-card {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-radius: 10px;
  border: 2px solid transparent;
  transition: all 0.25s ease;
  cursor: default;
  margin: 2px 0;
}

.ov-body {
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

.ov-desc {
  font-size: 10px;
  color: var(--ad-text-secondary, #8c8c8c);
}

.ov-right {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.ov-check { color: #52c41a; }
.ov-arr { color: #409eff; }
.ov-hint { font-size: 11px; color: #409eff; font-weight: 500; }

/* ============ 卡片状态样式（共用横竖） ============ */
.c-current {
  border-color: #409eff;
  background: linear-gradient(135deg, rgba(64, 158, 255, 0.07), rgba(64, 158, 255, 0.03));
  box-shadow: 0 0 0 4px rgba(64, 158, 255, 0.08);
}
.c-current .oh-label, .c-current .ov-label { color: #409eff; }
.c-current .oh-desc, .c-current .ov-desc { color: #409eff; }

.c-done {
  border-color: transparent;
  background: transparent;
}
.c-done .oh-label, .c-done .ov-label { color: #52c41a; }
.c-done .oh-desc, .c-done .ov-desc { color: #52c41a; }

.c-ready {
  border-color: #409eff;
  border-style: dashed;
  background: rgba(64, 158, 255, 0.03);
  cursor: pointer;
}
.c-ready:hover {
  background: rgba(64, 158, 255, 0.08);
  box-shadow: 0 2px 10px rgba(64, 158, 255, 0.1);
  transform: translateX(3px);
}
.c-ready:active { transform: translateX(0); }
.c-ready .oh-label, .c-ready .ov-label { color: #409eff; }
.c-ready .oh-desc, .c-ready .ov-desc { color: #409eff; }

.c-disabled {
  border-color: #f0f0f0;
  background: #fafafa;
}
.c-disabled .oh-label, .c-disabled .ov-label { color: #d9d9d9; }
.c-disabled .oh-desc, .c-disabled .ov-desc { color: #e8e8e8; }

/* ============ 取消按钮 ============ */
.ow-cancel {
  padding-top: 10px;
  border-top: 1px solid var(--ad-border);
}

.cancel-card {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 8px;
  border: 1.5px dashed #ff4d4f;
  color: #ff4d4f;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.cancel-card:hover {
  background: #fff1f0;
  box-shadow: 0 2px 8px rgba(255, 77, 79, 0.1);
}

/* ============ 暗色主题 ============ */
:root[data-theme="dark"] .b-disabled,
:root[data-theme="dark"] .d-disabled {
  background: #262626;
  color: #434343;
  border-color: #434343;
}

:root[data-theme="dark"] .b-ready,
:root[data-theme="dark"] .d-ready {
  background: rgba(64, 158, 255, 0.12);
}

:root[data-theme="dark"] .d-ready:hover {
  background: rgba(64, 158, 255, 0.2);
}

:root[data-theme="dark"] .c-disabled {
  border-color: #262626;
  background: #1a1a1a;
}
:root[data-theme="dark"] .c-disabled .oh-label,
:root[data-theme="dark"] .c-disabled .ov-label { color: #434343; }
:root[data-theme="dark"] .c-disabled .oh-desc,
:root[data-theme="dark"] .c-disabled .ov-desc { color: #333; }

:root[data-theme="dark"] .c-current {
  background: rgba(64, 158, 255, 0.1);
  box-shadow: 0 0 0 4px rgba(64, 158, 255, 0.12);
}

:root[data-theme="dark"] .c-ready {
  background: rgba(64, 158, 255, 0.06);
}
:root[data-theme="dark"] .c-ready:hover {
  background: rgba(64, 158, 255, 0.15);
}

:root[data-theme="dark"] .cancel-card:hover {
  background: rgba(255, 77, 79, 0.1);
}

:root[data-theme="dark"] .ov-line { background: #434343; }
:root[data-theme="dark"] .oh-line { background: #434343; }
:root[data-theme="dark"] .oh-arrow { color: #595959; }

/* ===== 小屏 ===== */
@media (max-width: 700px) {
  .ow-bar { padding: 14px 12px; }
  .oh-card { padding: 8px 12px; min-width: 60px; }
  .oh-connector { width: 24px; }
  .ov-card { padding: 8px 12px; }
  .oh-desc, .ov-desc, .ov-hint { display: none; }
  .ow-vertical { padding-left: 8px; }
}
</style>
