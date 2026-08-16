<template>
  <section class="workflow-card" aria-live="polite" aria-label="业务流程导航">
    <header class="workflow-header">
      <div>
        <span class="workflow-eyebrow">业务导航</span>
        <h2>{{ guidance.current_step }}</h2>
      </div>
      <el-button
        text
        circle
        size="small"
        aria-label="关闭流程导航"
        @click="store.clearWorkflowGuidance()"
      >
        <el-icon><Close /></el-icon>
      </el-button>
    </header>

    <AiWorkflowProgress
      v-if="guidance.progress"
      :progress="guidance.progress"
      :alerts="guidance.alerts"
      @action="goToAction"
    />

    <AiWorkflowChecklist
      v-if="guidance.checklist"
      :checklist="guidance.checklist"
      @action="goToAction"
    />

    <div
      v-if="guidance.next_action?.semantics"
      class="action-contract"
      aria-label="下一步操作说明"
    >
      <div class="action-contract-heading">
        <span>下一步怎么做</span>
        <el-tag
          size="small"
          :type="guidance.next_action.semantics.effect === 'write' ? 'warning' : 'info'"
        >
          {{ guidance.next_action.semantics.requires_confirmation ? '需要人工确认' : '只读预览' }}
        </el-tag>
      </div>
      <strong>{{ guidance.next_action.semantics.purpose }}</strong>
      <ul>
        <li
          v-for="item in guidance.next_action.semantics.prerequisites"
          :key="item"
        >
          操作前：{{ item }}
        </li>
      </ul>
      <small>所需权限：{{ guidance.next_action.semantics.required_permission }}</small>
    </div>

    <div v-if="visibleBlockers.length" class="workflow-blockers">
      <div class="workflow-label">
        <el-icon><WarningFilled /></el-icon>
        完成前请处理
      </div>
      <ul>
        <li v-for="blocker in visibleBlockers" :key="blocker">{{ blocker }}</li>
      </ul>
    </div>

    <div class="workflow-signal">
      <span>完成标志</span>
      <p>{{ guidance.completion_signal }}</p>
    </div>

    <p v-if="store.guidanceError" class="workflow-error" role="alert">
      {{ store.guidanceError }}
    </p>

    <footer class="workflow-actions">
      <el-button
        v-if="guidance.next_action"
        type="primary"
        size="small"
        :disabled="!canNavigate"
        @click="goToNextAction"
      >
        <el-icon v-if="guidance.next_action.target_key"><Position /></el-icon>
        {{ guidance.next_action.label }}
        <el-icon class="el-icon--right"><Right /></el-icon>
      </el-button>
      <span v-else class="workflow-complete">
        <el-icon><CircleCheckFilled /></el-icon>
        当前流程已完成
      </span>
      <el-button
        size="small"
        :loading="store.guidanceLoading"
        @click="store.refreshWorkflowGuidance()"
      >
        我已完成，重新核验
      </el-button>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { useRoute } from 'vue-router'
import { useAiAssistantStore } from '@/stores/aiAssistantStore'
import { isSafeWorkflowTarget } from '@/utils/workflowGuidance'
import { isSameWorkflowPath } from '@/utils/pageActionGuide'
import type { AiWorkflowAction } from '@/types/aiAssistant'
import AiWorkflowProgress from './AiWorkflowProgress.vue'
import AiWorkflowChecklist from './AiWorkflowChecklist.vue'

const store = useAiAssistantStore()
const router = useRouter()
const route = useRoute()
const guidance = computed(() => store.activeGuidance!)
const visibleBlockers = computed(() => guidance.value.blockers.filter(blocker =>
  !(
    guidance.value.alerts.some(alert => alert.code === 'receivable_outstanding')
    && blocker.includes('未收')
  ),
))
const canNavigate = computed(() =>
  Boolean(
    guidance.value.next_action
    && isSafeWorkflowTarget(guidance.value.next_action.target_path),
  ),
)

async function goToNextAction() {
  const nextAction = guidance.value.next_action
  if (nextAction) await goToAction(nextAction)
}

async function goToAction(action: AiWorkflowAction) {
  const path = action.target_path
  if (!path || !isSafeWorkflowTarget(path)) {
    ElMessage.error('该导航地址不在系统允许范围内')
    return
  }
  if (action.target_key) {
    store.startPageActionGuide(action)
  }
  if (!isSameWorkflowPath(route.path, path)) {
    await router.push(path)
  }
}
</script>

<style scoped>
.workflow-card {
  margin: 10px 14px 4px;
  padding: 12px;
  border: 1px solid var(--ai-border, #2a2a4a);
  border-left: 3px solid var(--ai-accent, var(--el-color-danger));
  border-radius: 8px;
  background: var(--ai-surface, #1c1c34);
  color: var(--ai-text, #e8e8f0);
  flex-shrink: 0;
}
.workflow-header,
.workflow-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.workflow-eyebrow,
.workflow-label,
.workflow-signal span {
  font-size: 11px;
  color: var(--ai-text-muted, #666688);
}
h2 {
  margin: 2px 0 0;
  font-size: 15px;
  line-height: 1.4;
}
.workflow-blockers {
  margin-top: 10px;
  padding: 8px 10px;
  border-radius: 6px;
  background: var(--ai-warning-bg, rgba(230, 162, 60, 0.1));
}
.action-contract {
  display: grid;
  gap: 5px;
  margin-top: 10px;
  padding: 8px 10px;
  border: 1px solid var(--ai-border, #2a2a4a);
  border-radius: 6px;
  background: rgba(144, 147, 153, 0.06);
}
.action-contract-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  color: var(--ai-text-muted, #666688);
  font-size: 11px;
}
.action-contract strong {
  color: var(--ai-text, #e8e8f0);
  font-size: 12px;
  line-height: 1.45;
}
.action-contract ul {
  margin-top: 0;
}
.action-contract small {
  color: var(--ai-text-muted, #666688);
  font-size: 10px;
}
.workflow-label {
  display: flex;
  align-items: center;
  gap: 5px;
  color: var(--ai-warning, var(--el-color-warning));
}
ul {
  margin: 5px 0 0;
  padding-left: 18px;
  font-size: 12px;
  line-height: 1.6;
}
.workflow-signal {
  margin-top: 10px;
}
.workflow-signal p {
  margin: 3px 0 0;
  font-size: 12px;
  line-height: 1.5;
  color: var(--ai-text-secondary, #8888aa);
}
.workflow-error {
  margin: 8px 0 0;
  color: var(--el-color-danger);
  font-size: 12px;
}
.workflow-actions {
  margin-top: 12px;
  flex-wrap: wrap;
}
.workflow-complete {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--el-color-success);
  font-size: 12px;
}
</style>
