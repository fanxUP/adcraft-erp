<template>
  <div class="quote-workflow">
    <!-- 流程图主体 -->
    <div class="workflow-canvas">
      <div
        v-for="(step, index) in steps"
        :key="step.status"
        class="workflow-node-wrapper"
      >
        <!-- 连接箭头（在节点之前） -->
        <div v-if="index > 0" class="flow-arrow">
          <div class="arrow-line" :class="{ 'arrow-active': isCompleted(step.status) }"></div>
          <div class="arrow-head" :class="{ 'arrow-active': isCompleted(step.status) }">▶</div>
          <!-- 允许的回退箭头 -->
          <div
            v-if="index === 1 && currentStatus === 'confirmed'"
            class="back-arrow-indicator"
          >可撤回</div>
        </div>

        <!-- 节点 -->
        <div class="flow-node" :class="nodeClass(step.status)">
          <div class="node-icon-wrapper">
            <div class="node-icon">
              <el-icon v-if="isCompleted(step.status) && step.status !== currentStatus" :size="24">
                <Check />
              </el-icon>
              <span v-else class="step-num">{{ index + 1 }}</span>
            </div>
            <div v-if="step.status === currentStatus" class="node-pulse"></div>
          </div>
          <div class="node-label">{{ step.label }}</div>
          <div class="node-desc">{{ step.desc }}</div>
          <!-- 当前状态标签 -->
          <div v-if="step.status === currentStatus" class="current-badge">当前</div>
        </div>
      </div>
    </div>

    <!-- 操作区 -->
    <div class="workflow-actions">
      <div class="actions-divider"></div>
      <div class="actions-content">
        <div class="actions-title">可用操作：</div>
        <div class="actions-buttons">
          <!-- 草稿状态 -->
          <template v-if="currentStatus === 'draft'">
            <el-button type="primary" :loading="saving" @click="$emit('save')">
              <el-icon style="margin-right: 4px"><Edit /></el-icon>
              保存草稿
            </el-button>
            <el-button
              v-if="isExisting"
              type="success"
              @click="$emit('confirm')"
            >
              <el-icon style="margin-right: 4px"><CircleCheck /></el-icon>
              确认报价
            </el-button>
          </template>

          <!-- 已确认状态 -->
          <template v-else-if="currentStatus === 'confirmed'">
            <el-button type="warning" :loading="reverting" @click="$emit('revert')">
              <el-icon style="margin-right: 4px"><Refresh /></el-icon>
              撤回草稿
            </el-button>
            <el-button type="danger" :loading="converting" @click="$emit('convert')">
              <el-icon style="margin-right: 4px"><Right /></el-icon>
              转订单
            </el-button>
          </template>

          <!-- 已转订单 -->
          <template v-else-if="currentStatus === 'converted'">
            <el-tag type="success" size="large" style="font-size: 15px; padding: 8px 20px">
              <el-icon style="margin-right: 6px"><SuccessFilled /></el-icon>
              已转订单，此报价为只读状态
            </el-tag>
          </template>

          <!-- 已作废 -->
          <template v-else-if="currentStatus === 'cancelled'">
            <el-tag type="danger" size="large" style="font-size: 15px; padding: 8px 20px">
              <el-icon style="margin-right: 6px"><WarningFilled /></el-icon>
              已作废，不可编辑
            </el-tag>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  currentStatus: string
  isExisting: boolean
  saving: boolean
  converting: boolean
  reverting: boolean
}>()

defineEmits<{
  save: []
  confirm: []
  convert: []
  revert: []
}>()

interface WorkflowStep {
  status: string
  label: string
  desc: string
}

const steps: WorkflowStep[] = [
  { status: 'draft', label: '草稿', desc: '新建报价，可编辑修改' },
  { status: 'confirmed', label: '已确认', desc: '报价已锁定，等待转订单' },
  { status: 'converted', label: '已转订单', desc: '已生成订单，流程结束' },
]

const statusOrder = computed(() => {
  const order: Record<string, number> = {}
  steps.forEach((s, i) => { order[s.status] = i })
  return order
})

function isCompleted(status: string): boolean {
  const currentIdx = statusOrder.value[props.currentStatus] ?? -1
  const stepIdx = statusOrder.value[status] ?? -1
  return currentIdx > stepIdx
}

function nodeClass(status: string) {
  if (status === props.currentStatus) return 'node-current'
  if (isCompleted(status)) return 'node-completed'
  return 'node-pending'
}
</script>

<style scoped>
.quote-workflow {
  background: var(--ad-card);
  border: 1px solid var(--ad-border);
  border-radius: 8px;
  padding: 24px 20px;
  margin-bottom: 20px;
}

/* 流程图画布 */
.workflow-canvas {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  gap: 0;
  position: relative;
}

.workflow-node-wrapper {
  display: flex;
  align-items: center;
  flex: 1;
  max-width: 340px;
}

.workflow-node-wrapper:first-child {
  justify-content: flex-start;
}

.workflow-node-wrapper:last-child {
  justify-content: flex-end;
}

.workflow-node-wrapper:nth-child(2) {
  justify-content: center;
}

/* 箭头连接 */
.flow-arrow {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  position: relative;
  width: 80px;
}

.arrow-line {
  flex: 1;
  height: 3px;
  background: #dcdfe6;
  border-radius: 2px;
  transition: all 0.3s ease;
}

.arrow-line.arrow-active {
  background: linear-gradient(to right, #67c23a, #85ce61);
  height: 3px;
  box-shadow: 0 0 6px rgba(103, 194, 58, 0.3);
}

.arrow-head {
  position: absolute;
  right: -2px;
  font-size: 10px;
  color: #dcdfe6;
  transition: all 0.3s ease;
  line-height: 1;
}

.arrow-head.arrow-active {
  color: #67c23a;
}

/* 回退指示 */
.back-arrow-indicator {
  position: absolute;
  top: -20px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 10px;
  color: #e6a23c;
  white-space: nowrap;
  background: var(--ad-card);
  padding: 0 4px;
}

/* 节点 */
.flow-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  position: relative;
  padding: 12px 16px;
  min-width: 100px;
  transition: all 0.3s ease;
  cursor: default;
}

.node-icon-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.node-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 700;
  transition: all 0.3s ease;
  z-index: 1;
}

.step-num {
  font-size: 18px;
  font-weight: 700;
}

.node-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--ad-text);
  white-space: nowrap;
  transition: all 0.3s ease;
}

.node-desc {
  font-size: 11px;
  color: var(--ad-text-secondary, #909399);
  text-align: center;
  line-height: 1.3;
  max-width: 140px;
  transition: all 0.3s ease;
}

.current-badge {
  position: absolute;
  top: -8px;
  right: -8px;
  font-size: 10px;
  padding: 1px 8px;
  border-radius: 10px;
  font-weight: 600;
  white-space: nowrap;
}

/* 待处理状态 */
.node-pending .node-icon {
  background: #f0f2f5;
  color: #c0c4cc;
  border: 2px solid #dcdfe6;
}

.node-pending .node-label {
  color: #c0c4cc;
}

.node-pending .node-desc {
  color: #dcdfe6;
}

/* 已完成状态 */
.node-completed .node-icon {
  background: linear-gradient(135deg, #67c23a, #85ce61);
  color: #fff;
  border: 2px solid #67c23a;
  box-shadow: 0 2px 8px rgba(103, 194, 58, 0.35);
}

.node-completed .node-label {
  color: #67c23a;
}

/* 当前状态 */
.node-current .node-icon {
  background: linear-gradient(135deg, #409eff, #66b1ff);
  color: #fff;
  border: 2px solid #409eff;
  box-shadow: 0 2px 12px rgba(64, 158, 255, 0.4);
  transform: scale(1.1);
}

.node-current .node-label {
  color: #409eff;
  font-size: 15px;
}

.node-current .current-badge {
  background: #409eff;
  color: #fff;
}

/* 脉冲动画 */
.node-pulse {
  position: absolute;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  border: 2px solid #409eff;
  animation: pulse 2s ease-in-out infinite;
  opacity: 0.5;
}

@keyframes pulse {
  0% { transform: scale(1); opacity: 0.5; }
  50% { transform: scale(1.2); opacity: 0.1; }
  100% { transform: scale(1); opacity: 0.5; }
}

/* 操作区 */
.workflow-actions {
  margin-top: 20px;
}

.actions-divider {
  height: 1px;
  background: linear-gradient(to right, transparent, var(--ad-border), transparent);
  margin-bottom: 16px;
}

.actions-content {
  display: flex;
  align-items: center;
  gap: 12px;
  justify-content: center;
  flex-wrap: wrap;
}

.actions-title {
  font-size: 13px;
  color: var(--ad-text-secondary, #909399);
  white-space: nowrap;
}

.actions-buttons {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

/* 暗色主题适配 */
:root[data-theme="dark"] .node-pending .node-icon {
  background: #2c2c2c;
  color: #555;
  border-color: #444;
}

:root[data-theme="dark"] .node-pending .node-label {
  color: #666;
}

:root[data-theme="dark"] .node-pending .node-desc {
  color: #555;
}

:root[data-theme="dark"] .arrow-line {
  background: #444;
}

:root[data-theme="dark"] .arrow-head {
  color: #444;
}

:root[data-theme="dark"] .arrow-line.arrow-active {
  background: linear-gradient(to right, #67c23a, #85ce61);
}

:root[data-theme="dark"] .back-arrow-indicator {
  background: var(--ad-card);
}

/* 小屏适配 */
@media (max-width: 720px) {
  .workflow-canvas {
    flex-direction: column;
    align-items: center;
    gap: 12px;
  }

  .workflow-node-wrapper {
    flex-direction: column;
    max-width: 100%;
    width: 100%;
  }

  .flow-arrow {
    width: auto;
    height: 32px;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    transform: rotate(90deg);
  }

  .back-arrow-indicator {
    display: none;
  }

  .flow-node {
    flex-direction: row;
    gap: 12px;
    padding: 8px 12px;
    width: 100%;
    max-width: 300px;
  }

  .node-label { white-space: normal; }
  .node-desc { display: none; }
  .current-badge { position: static; }
}
</style>
