<template>
  <div class="workflow-progress" aria-label="订单全流程进度">
    <div class="progress-summary">
      <span>全流程进度</span>
      <strong>{{ progress.completed_steps }}/{{ progress.total_steps }}</strong>
    </div>
    <el-progress
      :percentage="progress.percent"
      :stroke-width="6"
      :show-text="false"
      color="var(--ai-accent, #f56c6c)"
      :aria-label="`流程已完成 ${progress.percent}%`"
    />

    <ol class="progress-steps">
      <li
        v-for="step in progress.steps"
        :key="step.key"
        class="progress-step"
        :class="`is-${step.state}`"
        :aria-current="step.state === 'current' ? 'step' : undefined"
      >
        <span class="step-marker" aria-hidden="true">
          <el-icon v-if="step.state === 'completed'"><CircleCheckFilled /></el-icon>
          <el-icon v-else-if="step.state === 'blocked'"><WarningFilled /></el-icon>
          <span v-else class="step-dot" />
        </span>
        <span class="step-content">
          <span class="step-label">{{ step.label }}</span>
          <span class="step-detail">{{ step.detail }}</span>
        </span>
        <span v-if="step.state === 'current'" class="step-state">当前</span>
        <span v-else-if="step.state === 'blocked'" class="step-state">已终止</span>
      </li>
    </ol>

    <div v-if="alerts.length" class="progress-alerts" aria-label="流程异常提醒">
      <div class="alerts-heading">
        <el-icon><WarningFilled /></el-icon>
        异常提醒
      </div>
      <div
        v-for="alert in alerts"
        :key="alert.code"
        class="progress-alert"
        :class="`is-${alert.severity}`"
        :role="alert.severity === 'danger' ? 'alert' : 'status'"
      >
        <strong>{{ alert.title }}</strong>
        <span>{{ alert.detail }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type {
  AiWorkflowAlert,
  AiWorkflowProgress,
} from '@/types/aiAssistant'

defineProps<{
  progress: AiWorkflowProgress
  alerts: AiWorkflowAlert[]
}>()
</script>

<style scoped>
.workflow-progress {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--ai-border, #2a2a4a);
}
.progress-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 7px;
  color: var(--ai-text-secondary, #8888aa);
  font-size: 12px;
}
.progress-summary strong {
  color: var(--ai-text, #e8e8f0);
  font-variant-numeric: tabular-nums;
}
.progress-steps {
  display: grid;
  gap: 0;
  margin: 10px 0 0;
  padding: 0;
  list-style: none;
}
.progress-step {
  position: relative;
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr) auto;
  gap: 7px;
  min-height: 36px;
  color: var(--ai-text-muted, #666688);
}
.progress-step:not(:last-child)::before {
  position: absolute;
  top: 17px;
  bottom: -3px;
  left: 7px;
  width: 1px;
  background: var(--ai-border, #2a2a4a);
  content: "";
}
.step-marker {
  position: relative;
  z-index: 1;
  display: flex;
  justify-content: center;
  padding-top: 1px;
  font-size: 15px;
  background: var(--ai-surface, #1c1c34);
}
.step-dot {
  width: 8px;
  height: 8px;
  margin-top: 4px;
  border: 2px solid currentColor;
  border-radius: 50%;
}
.step-content {
  display: flex;
  min-width: 0;
  flex-direction: column;
}
.step-label {
  color: inherit;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.35;
}
.step-detail {
  overflow: hidden;
  color: var(--ai-text-muted, #666688);
  font-size: 11px;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.step-state {
  padding-top: 1px;
  color: inherit;
  font-size: 10px;
}
.progress-step.is-completed {
  color: var(--el-color-success);
}
.progress-step.is-current {
  color: var(--ai-accent, #f56c6c);
}
.progress-step.is-blocked {
  color: var(--el-color-danger);
}
.progress-alerts {
  display: grid;
  gap: 6px;
  margin-top: 8px;
}
.alerts-heading {
  display: flex;
  align-items: center;
  gap: 5px;
  color: var(--el-color-warning);
  font-size: 11px;
}
.progress-alert {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 7px 8px;
  border-left: 2px solid var(--el-color-warning);
  background: rgba(230, 162, 60, 0.08);
  font-size: 11px;
  line-height: 1.4;
}
.progress-alert strong {
  color: var(--ai-text, #e8e8f0);
}
.progress-alert span {
  color: var(--ai-text-secondary, #8888aa);
}
.progress-alert.is-danger {
  border-left-color: var(--el-color-danger);
  background: rgba(245, 108, 108, 0.08);
}
.progress-alert.is-info {
  border-left-color: var(--el-color-info);
  background: rgba(144, 147, 153, 0.08);
}
</style>
