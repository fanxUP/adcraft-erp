<template>
  <div class="knowledge-health-page">
    <header class="page-header">
      <div>
        <h2>AI 业务知识健康</h2>
        <p>检查 AI 是否正在使用最新业务流程、页面控件和权限规则。</p>
      </div>
      <div class="header-actions">
        <el-button :loading="loading" @click="loadStatus">刷新</el-button>
        <el-button
          type="primary"
          :loading="syncing"
          :disabled="!status"
          @click="handleSync"
        >
          同步业务知识
        </el-button>
      </div>
    </header>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      show-icon
      :closable="false"
    />

    <template v-if="status">
      <el-alert
        class="sync-alert"
        :title="status.in_sync ? '业务知识已与当前代码同步' : '检测到业务知识版本漂移'"
        :description="syncDescription"
        :type="status.in_sync ? 'success' : 'warning'"
        show-icon
        :closable="false"
      />

      <section class="metric-grid" aria-label="AI业务知识指标">
        <el-card v-for="metric in metrics" :key="metric.label" shadow="never">
          <strong>{{ metric.value }}</strong>
          <span>{{ metric.label }}</span>
        </el-card>
      </section>

      <el-card shadow="never" class="contract-card">
        <template #header>
          <div class="card-header">
            <span>页面能力契约</span>
            <el-tag :type="status.contract.in_sync ? 'success' : 'warning'">
              {{ status.contract.in_sync ? '已同步' : '待同步' }}
            </el-tag>
          </div>
        </template>

        <el-descriptions :column="2" border>
          <el-descriptions-item label="源契约版本">
            v{{ status.contract.source_version }}
          </el-descriptions-item>
          <el-descriptions-item label="数据库规则版本">
            {{ status.contract.active_rule_version ?? '未发布' }}
          </el-descriptions-item>
          <el-descriptions-item label="数据库契约版本">
            {{ status.contract.database_contract_version
              ? `v${status.contract.database_contract_version}`
              : '未发布' }}
          </el-descriptions-item>
          <el-descriptions-item label="规则库指纹">
            <code>{{ shortDigest(status.catalog_digest) }}</code>
          </el-descriptions-item>
        </el-descriptions>

        <div class="coverage">
          <div class="coverage-heading">
            <span>操作语义覆盖</span>
            <strong>
              {{ status.contract.semantic_complete_count }}/{{ status.contract.capability_count }}
            </strong>
          </div>
          <el-progress
            :percentage="semanticCoverage"
            :status="semanticCoverage === 100 ? 'success' : 'warning'"
          />
        </div>

        <div v-if="hasContractIssues" class="contract-issues">
          <div v-if="status.contract.added_targets.length">
            <strong>待新增控件</strong>
            <el-tag
              v-for="target in status.contract.added_targets"
              :key="target"
              type="warning"
            >
              {{ target }}
            </el-tag>
          </div>
          <div v-if="status.contract.retired_targets.length">
            <strong>待停用控件</strong>
            <el-tag
              v-for="target in status.contract.retired_targets"
              :key="target"
              type="info"
            >
              {{ target }}
            </el-tag>
          </div>
          <div v-if="status.contract.unknown_permissions.length">
            <strong>未登记权限</strong>
            <el-tag
              v-for="permission in status.contract.unknown_permissions"
              :key="permission"
              type="danger"
            >
              {{ permission }}
            </el-tag>
          </div>
        </div>
      </el-card>

      <el-card shadow="never">
        <template #header>
          <span>最近同步记录</span>
        </template>
        <el-table
          :data="status.recent_syncs"
          empty-text="暂无同步记录"
          stripe
        >
          <el-table-column label="时间" min-width="170">
            <template #default="{ row }">
              {{ formatTime(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100" />
          <el-table-column prop="added_count" label="新增" width="80" />
          <el-table-column prop="updated_count" label="更新" width="80" />
          <el-table-column prop="retired_count" label="停用" width="80" />
          <el-table-column prop="unchanged_count" label="未变" width="80" />
          <el-table-column label="指纹" min-width="160">
            <template #default="{ row }">
              <code>{{ shortDigest(row.catalog_digest) }}</code>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>

    <el-skeleton v-else :rows="8" animated />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getBusinessRuleStatus,
  syncBusinessRules,
  type AiBusinessRuleStatus,
} from '@/api/aiAssistant'

const loading = ref(false)
const syncing = ref(false)
const errorMessage = ref('')
const status = ref<AiBusinessRuleStatus | null>(null)

const semanticCoverage = computed(() => {
  const contract = status.value?.contract
  if (!contract?.capability_count) return 0
  return Math.round(
    contract.semantic_complete_count / contract.capability_count * 100,
  )
})

const metrics = computed(() => {
  const current = status.value
  if (!current) return []
  return [
    { label: '有效业务规则', value: current.active_count },
    { label: '已登记页面', value: current.contract.page_count },
    { label: '页面操作控件', value: current.contract.capability_count },
    { label: '写操作需确认', value: current.contract.all_write_actions_require_confirmation ? '完整' : '异常' },
  ]
})

const hasContractIssues = computed(() => Boolean(
  status.value
  && (
    status.value.contract.added_targets.length
    || status.value.contract.retired_targets.length
    || status.value.contract.unknown_permissions.length
  ),
))

const syncDescription = computed(() => {
  const pending = status.value?.pending
  if (!pending) return ''
  if (status.value?.in_sync) {
    return `当前共 ${pending.unchanged_count} 条规则，无待发布变更。`
  }
  return `待新增 ${pending.added_count} 条、更新 ${pending.updated_count} 条、停用 ${pending.retired_count} 条。`
})

function formatTime(value: string | null): string {
  if (!value) return '-'
  return value.replace('T', ' ').slice(0, 19)
}

function shortDigest(value: string): string {
  return value ? `${value.slice(0, 12)}…` : '-'
}

async function loadStatus() {
  loading.value = true
  errorMessage.value = ''
  try {
    status.value = await getBusinessRuleStatus()
  } catch (error) {
    errorMessage.value = error instanceof Error
      ? error.message
      : 'AI 业务知识状态加载失败'
  } finally {
    loading.value = false
  }
}

async function handleSync() {
  try {
    await ElMessageBox.confirm(
      '将当前代码中的业务规则发布到 AI 规则库，历史版本会保留。是否继续？',
      '同步业务知识',
      {
        type: 'warning',
        confirmButtonText: '确认同步',
        cancelButtonText: '取消',
      },
    )
  } catch {
    return
  }
  syncing.value = true
  try {
    const result = await syncBusinessRules()
    ElMessage.success(
      `同步完成：新增 ${result.added_count}，更新 ${result.updated_count}，停用 ${result.retired_count}`,
    )
    await loadStatus()
  } finally {
    syncing.value = false
  }
}

onMounted(loadStatus)
</script>

<style scoped>
.knowledge-health-page {
  display: grid;
  gap: 16px;
  color: var(--ad-text);
}
.page-header,
.card-header,
.coverage-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.page-header h2 {
  margin: 0;
}
.page-header p {
  margin: 6px 0 0;
  color: var(--ad-text-secondary);
  font-size: 13px;
}
.header-actions {
  display: flex;
  gap: 8px;
}
.sync-alert {
  margin: 0;
}
.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}
.metric-grid :deep(.el-card__body) {
  display: grid;
  gap: 5px;
}
.metric-grid strong {
  font-size: 24px;
  font-variant-numeric: tabular-nums;
}
.metric-grid span,
.coverage-heading {
  color: var(--ad-text-secondary);
  font-size: 12px;
}
.coverage,
.contract-issues {
  margin-top: 16px;
}
.coverage-heading {
  margin-bottom: 8px;
}
.contract-issues {
  display: grid;
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--el-color-warning-light-5);
  border-radius: 6px;
  background: var(--el-color-warning-light-9);
}
.contract-issues > div {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}
.contract-issues strong {
  margin-right: 4px;
  font-size: 12px;
}
code {
  color: var(--ad-text-secondary);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
}
@media (max-width: 900px) {
  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 600px) {
  .page-header {
    align-items: flex-start;
    flex-direction: column;
  }
  .metric-grid {
    grid-template-columns: 1fr;
  }
  .contract-card :deep(.el-descriptions__body) {
    overflow-x: auto;
  }
}
</style>
