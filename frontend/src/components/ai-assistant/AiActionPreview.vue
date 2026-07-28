<template>
  <div class="ai-action-preview">
    <div class="ai-action-header">
      <div class="ai-action-header-left">
        <div class="ai-action-warning-icon">
          <el-icon :size="14"><WarningFilled /></el-icon>
        </div>
        <span class="ai-action-title">待确认操作</span>
      </div>
      <span class="ai-action-badge">需要审核</span>
    </div>
    <div class="ai-action-body">
      <div class="ai-action-label-row">
        <span class="ai-action-label">操作类型</span>
        <span class="ai-action-value">{{ actionLabel }}</span>
      </div>
      <div class="ai-action-section-label">预览数据</div>
      <pre class="ai-action-data">{{ formattedPreview }}</pre>
    </div>
    <div class="ai-action-footer">
      <el-button size="small" class="ai-action-cancel" @click="handleCancel">取消</el-button>
      <el-button size="small" type="primary" class="ai-action-confirm" @click="handleConfirm">
        <el-icon :size="13" style="margin-right:4px"><Check /></el-icon>
        确认执行
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAiAssistantStore } from '@/stores/aiAssistantStore'

const store = useAiAssistantStore()

const action = computed(() => store.pendingAction)

const actionLabel = computed(() => {
  const toolName = action.value?.tool_name || ''
  const labels: Record<string, string> = {
    create_installation_task_confirmed: '创建安装任务',
    create_installation_task_draft: '安装任务草稿预览',
    create_quote_draft: '报价草稿预览',
    create_quote_confirmed: '创建报价单',
  }
  return labels[toolName] || toolName
})

const formattedPreview = computed(() => {
  const data = action.value?.preview_data
  if (!data) return '无数据'
  try {
    return JSON.stringify(data, null, 2)
  } catch {
    return String(data)
  }
})

function handleConfirm() {
  if (action.value?.id) {
    store.confirmPendingAction(action.value.id)
  }
}

function handleCancel() {
  if (action.value?.id) {
    store.cancelPendingAction(action.value.id)
  }
}
</script>

<style scoped>
.ai-action-preview {
  border-top: 2px solid var(--ai-warning, #e6a23c);
  background: linear-gradient(180deg, rgba(230, 162, 60, 0.06), rgba(230, 162, 60, 0.02));
  padding: 12px 16px 10px;
}
.ai-action-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.ai-action-header-left {
  display: flex;
  align-items: center;
  gap: 7px;
}
.ai-action-warning-icon {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  background: var(--ai-warning-bg, rgba(230, 162, 60, 0.12));
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ai-warning, #e6a23c);
}
.ai-action-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--ai-text, #e8e8f0);
}
.ai-action-badge {
  padding: 2px 8px;
  border-radius: 10px;
  background: var(--ai-warning-bg, rgba(230, 162, 60, 0.12));
  color: var(--ai-warning, #e6a23c);
  font-size: 11px;
  font-weight: 500;
}
.ai-action-body {
  margin-bottom: 10px;
}
.ai-action-label-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.ai-action-label {
  font-size: 12px;
  color: var(--ai-text-secondary, #8888aa);
}
.ai-action-value {
  font-size: 12px;
  font-weight: 500;
  color: var(--ai-text, #e8e8f0);
  background: rgba(255,255,255,0.03);
  padding: 2px 8px;
  border-radius: 4px;
}
.ai-action-section-label {
  font-size: 11px;
  color: var(--ai-text-muted, #666688);
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}
.ai-action-data {
  margin: 0;
  padding: 8px 10px;
  background: rgba(0,0,0,0.2);
  border-radius: 6px;
  white-space: pre-wrap;
  word-break: break-all;
  font-size: 11px;
  font-family: 'Menlo', 'Monaco', 'Consolas', monospace;
  line-height: 1.5;
  color: var(--ai-text-secondary, #8888aa);
  max-height: 140px;
  overflow-y: auto;
  border: 1px solid rgba(255,255,255,0.03);
}
.ai-action-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.ai-action-cancel {
  border-radius: 8px;
}
.ai-action-confirm {
  border-radius: 8px;
  background: linear-gradient(135deg, #f56c6c, #d03050);
  border: none;
}
.ai-action-confirm:hover {
  background: linear-gradient(135deg, #f56c6c, #c02840);
  box-shadow: 0 2px 8px rgba(245,108,108,0.25);
}
</style>
