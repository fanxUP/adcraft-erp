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

    <div v-if="guidance.blockers.length" class="workflow-blockers">
      <div class="workflow-label">
        <el-icon><WarningFilled /></el-icon>
        完成前请处理
      </div>
      <ul>
        <li v-for="blocker in guidance.blockers" :key="blocker">{{ blocker }}</li>
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

const store = useAiAssistantStore()
const router = useRouter()
const route = useRoute()
const guidance = computed(() => store.activeGuidance!)
const canNavigate = computed(() =>
  Boolean(
    guidance.value.next_action
    && isSafeWorkflowTarget(guidance.value.next_action.target_path),
  ),
)

async function goToNextAction() {
  const nextAction = guidance.value.next_action
  const path = nextAction?.target_path
  if (!path || !isSafeWorkflowTarget(path)) {
    ElMessage.error('该导航地址不在系统允许范围内')
    return
  }
  if (nextAction?.target_key) {
    store.startPageActionGuide(nextAction)
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
  border-left: 3px solid var(--ai-accent, #f56c6c);
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
.workflow-label {
  display: flex;
  align-items: center;
  gap: 5px;
  color: var(--ai-warning, #e6a23c);
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
