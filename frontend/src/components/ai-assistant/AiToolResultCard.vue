<template>
  <div class="ai-tool-result" :class="statusClass">
    <div class="ai-tool-header" @click="expanded = !expanded">
      <div class="ai-tool-info">
        <div class="ai-tool-icon-wrap">
          <el-icon :size="13">
            <CircleCheckFilled v-if="data.status === 'success'" />
            <CircleCloseFilled v-else-if="data.status === 'failed' || data.status === 'error'" />
            <InfoFilled v-else />
          </el-icon>
        </div>
        <span class="ai-tool-name">{{ toolLabel }}</span>
      </div>
      <div class="ai-tool-meta">
        <span class="ai-tool-status-dot" :class="statusDotClass" />
        <span class="ai-tool-status-text">{{ statusText }}</span>
        <el-icon :size="11" class="ai-tool-toggle" :class="{ rotated: expanded }">
          <ArrowDown />
        </el-icon>
      </div>
    </div>
    <Transition name="expand">
      <div v-if="expanded" class="ai-tool-body">
        <div v-if="isPreview" class="ai-tool-preview-badge">
          <el-icon :size="11"><View /></el-icon>
          预览模式 — 未保存
        </div>
        <pre class="ai-tool-json">{{ formattedResult }}</pre>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { AiToolCallResult } from '@/types/aiAssistant'

const props = defineProps<{
  data: AiToolCallResult
}>()

const expanded = ref(false)

const toolLabel = computed(() => {
  const name = props.data.tool_name || ''
  const labels: Record<string, string> = {
    search_customers: '搜索客户',
    get_customer_detail: '客户详情',
    get_customer_receivables: '查询欠款',
    search_orders: '搜索订单',
    get_order_detail: '订单详情',
    get_order_progress: '订单进度',
    list_today_tasks: '今日任务',
    create_quote_draft: '报价草稿',
    create_installation_task_draft: '安装任务草稿',
    create_installation_task_confirmed: '创建安装任务',
    create_quote_confirmed: '创建报价单',
    change_order_status: '推进订单状态',
  }
  return labels[name] || name
})

const isPreview = computed(() => props.data.is_preview === true)

const statusClass = computed(() => {
  const s = props.data.status
  if (s === 'success') return 'is-success'
  if (s === 'failed' || s === 'error') return 'is-error'
  return 'is-info'
})

const statusDotClass = computed(() => {
  const s = props.data.status
  if (s === 'success') return 'dot-success'
  if (s === 'failed' || s === 'error') return 'dot-error'
  return 'dot-info'
})

const statusText = computed(() => {
  const s = props.data.status
  const map: Record<string, string> = {
    success: '成功',
    failed: '失败',
    error: '错误',
    pending: '处理中',
    running: '执行中',
    blocked: '被阻止',
    waiting_confirmation: '待确认',
  }
  return map[s] || s
})

const formattedResult = computed(() => {
  const r = props.data.result
  if (!r) return props.data.error_message || '无数据'
  try {
    return JSON.stringify(r, null, 2)
  } catch {
    return String(r)
  }
})
</script>

<style scoped>
.ai-tool-result {
  margin: 4px 0;
  border-radius: 8px;
  border: 1px solid var(--ai-border, #2a2a4a);
  overflow: hidden;
  font-size: 12px;
  transition: box-shadow 0.2s;
}
.ai-tool-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 7px 12px;
  cursor: pointer;
  user-select: none;
}
.is-success .ai-tool-header { background: rgba(103, 194, 58, 0.06); }
.is-error .ai-tool-header { background: rgba(245, 108, 108, 0.06); }
.is-info .ai-tool-header { background: rgba(144, 147, 153, 0.04); }

.ai-tool-info {
  display: flex;
  align-items: center;
  gap: 7px;
  color: var(--ai-text, #e8e8f0);
  font-weight: 500;
}
.ai-tool-icon-wrap {
  width: 22px;
  height: 22px;
  border-radius: 5px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.is-success .ai-tool-icon-wrap { background: rgba(103, 194, 58, 0.12); }
.is-error .ai-tool-icon-wrap { background: rgba(245, 108, 108, 0.12); }
.is-info .ai-tool-icon-wrap { background: rgba(144, 147, 153, 0.08); }
.is-success .ai-tool-icon-wrap .el-icon { color: #67c23a; }
.is-error .ai-tool-icon-wrap .el-icon { color: #f56c6c; }
.is-info .ai-tool-icon-wrap .el-icon { color: #909399; }

.ai-tool-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--ai-text-muted, #666688);
}
.ai-tool-status-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  flex-shrink: 0;
}
.dot-success { background: #67c23a; }
.dot-error { background: #f56c6c; }
.dot-info { background: #909399; }
.ai-tool-status-text {
  font-size: 11px;
}
.ai-tool-toggle {
  transition: transform 0.2s ease;
}
.ai-tool-toggle.rotated {
  transform: rotate(180deg);
}
.ai-tool-body {
  padding: 8px 12px 10px;
  border-top: 1px solid var(--ai-border, #2a2a4a);
  max-height: 260px;
  overflow: auto;
}
.ai-tool-preview-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--ai-warning-bg, rgba(230, 162, 60, 0.1));
  color: var(--ai-warning, #e6a23c);
  font-size: 11px;
  margin-bottom: 6px;
}
.ai-tool-json {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
  color: var(--ai-text-secondary, #8888aa);
  font-family: 'Menlo', 'Monaco', 'Consolas', monospace;
  font-size: 11px;
  line-height: 1.55;
}

/* Expand transition */
.expand-enter-active,
.expand-leave-active {
  transition: all 0.2s ease;
  overflow: hidden;
}
.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
  padding-top: 0;
  padding-bottom: 0;
}
</style>
