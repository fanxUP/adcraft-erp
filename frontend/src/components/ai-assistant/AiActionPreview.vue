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
        <span class="ai-action-value">{{ preview.title || actionLabel }}</span>
      </div>
      <dl v-if="preview.rows.length" class="ai-action-rows">
        <div v-for="row in preview.rows" :key="row.label" class="ai-action-row">
          <dt>{{ row.label }}</dt>
          <dd>{{ row.value }}</dd>
        </div>
      </dl>
      <div v-if="preview.effects.length" class="ai-action-effects">
        <div class="ai-action-section-label">执行影响</div>
        <ul>
          <li v-for="effect in preview.effects" :key="effect">{{ effect }}</li>
        </ul>
      </div>
      <p v-if="preview.note" class="ai-action-note">{{ preview.note }}</p>
      <template v-if="preview.fallbackJson">
        <div class="ai-action-section-label">预览数据</div>
        <pre class="ai-action-data">{{ preview.fallbackJson }}</pre>
      </template>
    </div>
    <div class="ai-action-footer">
      <el-button size="small" class="ai-action-cancel" :disabled="store.actionSubmitting" @click="handleCancel">取消</el-button>
      <el-button size="small" type="primary" class="ai-action-confirm"
        :loading="store.actionSubmitting" @click="handleConfirm">
        <el-icon :size="13" style="margin-right:4px"><Check /></el-icon>
        确认执行
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAiAssistantStore } from '@/stores/aiAssistantStore'
import { buildActionPreview } from '@/utils/actionPreview'

const store = useAiAssistantStore()

const action = computed(() => store.pendingAction)

const actionLabel = computed(() => {
  const toolName = action.value?.tool_name || ''
  const labels: Record<string, string> = {
    create_installation_task_confirmed: '创建安装任务',
    create_installation_task_draft: '安装任务草稿预览',
    create_quote_draft: '报价草稿预览',
    create_quote_confirmed: '创建报价单',
    add_quote_items: '新增报价项目',
    change_order_status: '推进订单状态',
  }
  return labels[toolName] || toolName
})

const preview = computed(() => buildActionPreview(action.value?.preview_data))

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

<style scoped src="./AiActionPreview.css"></style>
