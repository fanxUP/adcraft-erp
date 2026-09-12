<template>
  <div class="page completed-project-detail-page">
    <div class="page-header">
      <div>
        <el-button text class="back-button" @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          返回完成看板
        </el-button>
        <h1>完成项目详情</h1>
      </div>
    </div>

    <el-card shadow="never" class="detail-card" v-loading="loading">
      <el-alert
        v-if="error"
        :title="error"
        type="warning"
        :closable="false"
        show-icon
        class="detail-alert"
      />

      <template v-if="project">
        <div class="project-header">
          <div class="project-heading">
            <span class="project-no">{{ project.project_no }}</span>
            <h2>{{ project.project_name }}</h2>
          </div>
          <StatusTag status="completed" size="md" />
        </div>

        <dl class="project-meta">
          <div>
            <dt>客户名称</dt>
            <dd>{{ project.customer_name || '-' }}</dd>
          </div>
          <div>
            <dt>部门/科室</dt>
            <dd>{{ project.department || '-' }}</dd>
          </div>
          <div>
            <dt>完成时间</dt>
            <dd>{{ formatDateTimeFull(project.completed_at) }}</dd>
          </div>
          <div v-if="project.total_amount !== null && project.total_amount !== undefined">
            <dt>订单金额</dt>
            <dd>¥ {{ formatMoney(project.total_amount) }}</dd>
          </div>
        </dl>

        <section class="detail-section">
          <div class="section-heading">
            <div>
              <h3>订单明细</h3>
              <span>{{ project.items.length }} 条明细</span>
            </div>
            <span class="readonly-hint">只读</span>
          </div>

          <el-table
            v-if="project.items.length"
            :data="project.items"
            row-key="order_item_id"
            size="small"
            stripe
            class="detail-table"
            empty-text="暂无可见的完成明细"
          >
            <el-table-column label="项目内容" min-width="180">
              <template #default="{ row }">
                <span class="item-name">{{ row.item_name }}</span>
              </template>
            </el-table-column>
            <el-table-column label="产品/材质/工艺" min-width="260">
              <template #default="{ row }">
                <span class="wrap-cell">{{ row.material_process || '—' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="规格" min-width="150">
              <template #default="{ row }">
                <span class="wrap-cell">{{ row.specification || '—' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="数量" width="100" align="right">
              <template #default="{ row }">{{ formatQuantity(row) }}</template>
            </el-table-column>
            <el-table-column label="设计" min-width="170">
              <template #default="{ row }">
                <div v-if="row.stages.design" class="stage-cell">
                  <span class="stage-status">{{ row.stages.design.status_label }}</span>
                  <span class="stage-executor">执行人：{{ row.stages.design.employee_name || '未分配' }}</span>
                  <span class="stage-date">完成时间：{{ formatStageDate(row.stages.design) }}</span>
                </div>
                <span v-else class="stage-empty">—</span>
              </template>
            </el-table-column>
            <el-table-column label="制作" min-width="170">
              <template #default="{ row }">
                <div v-if="row.stages.production" class="stage-cell">
                  <span class="stage-status">{{ row.stages.production.status_label }}</span>
                  <span class="stage-executor">执行人：{{ row.stages.production.employee_name || '未分配' }}</span>
                  <span class="stage-date">完成时间：{{ formatStageDate(row.stages.production) }}</span>
                </div>
                <span v-else class="stage-empty">—</span>
              </template>
            </el-table-column>
            <el-table-column label="安装" min-width="170">
              <template #default="{ row }">
                <div v-if="row.stages.installation" class="stage-cell">
                  <span class="stage-status">{{ row.stages.installation.status_label }}</span>
                  <span class="stage-executor">执行人：{{ row.stages.installation.employee_name || '未分配' }}</span>
                  <span class="stage-date">完成时间：{{ formatStageDate(row.stages.installation) }}</span>
                </div>
                <span v-else class="stage-empty">—</span>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-else description="暂无可见的完成明细" :image-size="64" />
        </section>

        <section class="detail-section resource-section">
          <div class="section-heading">
            <div>
              <h3>任务资料</h3>
              <span>订单资料源头，按设计、制作、安装分组展示</span>
            </div>
            <span class="readonly-hint">只读</span>
          </div>

          <div class="resource-grid">
            <OrderTaskAttachments
              v-if="project.stages.includes('design')"
              :order-id="project.project_id"
              stage="design"
              readonly
            />
            <OrderTaskAttachments
              v-if="project.stages.includes('production')"
              :order-id="project.project_id"
              stage="production"
              readonly
            />
            <OrderTaskAttachments
              v-if="project.stages.includes('installation')"
              :order-id="project.project_id"
              stage="installation"
              readonly
            />
          </div>
        </section>
      </template>

      <el-empty v-else-if="!loading && !error" description="暂无项目详情" :image-size="64" />
    </el-card>

  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { getCompletedProject } from '@/api/tasks'
import type {
  CompletedProjectDetail as CompletedProjectDetailType,
  CompletedProjectDetailItem,
  CompletedProjectStage,
} from '@/types/api'
import StatusTag from '@/components/ui/StatusTag.vue'
import OrderTaskAttachments from '@/components/orders/OrderTaskAttachments.vue'
import { formatDate, formatDateTimeFull } from '@/utils/datetime'
import { formatMoney } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const error = ref('')
const project = ref<CompletedProjectDetailType | null>(null)

async function fetchProject() {
  const projectId = String(route.params.projectId || '')
  project.value = null
  error.value = ''
  if (!projectId) {
    error.value = '无法确定要查看的完成项目'
    return
  }

  loading.value = true
  try {
    project.value = await getCompletedProject(projectId)
  } catch {
    error.value = '完成项目详情暂时无法加载，请稍后重试'
  } finally {
    loading.value = false
  }
}

function goBack() {
  if (typeof window !== 'undefined' && typeof window.history.state?.back === 'string') {
    router.back()
    return
  }
  router.push({ name: 'ProjectKanbanBoard' })
}

function formatQuantity(row: CompletedProjectDetailItem) {
  if (row.quantity === null || row.quantity === undefined) return '-'
  const quantity = Number.isInteger(row.quantity) ? String(row.quantity) : String(row.quantity)
  return row.unit ? `${quantity} ${row.unit}` : quantity
}

function formatStageDate(stage?: CompletedProjectStage | null) {
  return formatDate(stage?.completed_at)
}

watch(() => route.params.projectId, () => {
  void fetchProject()
})

onMounted(() => {
  void fetchProject()
})
</script>

<style scoped>
.page { padding: 0; }
.page-header { margin-bottom: 16px; }
.back-button { padding-left: 0; color: var(--ad-text-secondary); }
.page-header h1 { margin: 6px 0 0; color: var(--ad-text); font-size: 24px; }
.detail-card { min-height: 280px; border: 1px solid var(--ad-border); background: var(--ad-card); color: var(--ad-text); }
.detail-alert { margin-bottom: 16px; }
.project-header, .section-heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.project-header { padding-bottom: 18px; border-bottom: 1px solid var(--ad-border); }
.project-heading { min-width: 0; }
.project-no { color: var(--ad-text-secondary); font-size: 13px; font-variant-numeric: tabular-nums; }
.project-heading h2 { margin: 6px 0 0; color: var(--ad-text); font-size: 22px; line-height: 1.45; }
.project-meta { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; margin: 0; padding: 20px 0 24px; }
.project-meta div { min-width: 0; }
.project-meta dt { margin-bottom: 5px; color: var(--ad-text-secondary); font-size: 12px; }
.project-meta dd { margin: 0; overflow: hidden; color: var(--ad-text); font-size: 14px; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.detail-section { margin-top: 20px; padding-top: 20px; border-top: 1px solid var(--ad-border); }
.section-heading { margin-bottom: 12px; }
.section-heading h3 { display: inline; margin: 0 10px 0 0; color: var(--ad-text); font-size: 17px; }
.section-heading span { color: var(--ad-text-secondary); font-size: 12px; }
.readonly-hint { padding: 3px 8px; border: 1px solid var(--ad-border); border-radius: 999px; }
.detail-table { width: 100%; }
.detail-table :deep(.cell) { line-height: 1.45; white-space: normal; word-break: break-word; }
.item-name { color: var(--ad-text); font-weight: 600; }
.wrap-cell { color: var(--ad-text); white-space: normal; word-break: break-word; }
.stage-cell { display: flex; flex-direction: column; gap: 3px; min-width: 132px; padding: 2px 0; }
.stage-status { color: var(--el-color-success); font-weight: 600; }
.stage-executor { color: #d93025; font-size: 12px; }
.stage-date { color: var(--ad-text-secondary); font-size: 12px; }
.stage-empty { color: var(--ad-text-placeholder); }
.resource-section { padding-bottom: 4px; }
.resource-grid { display: grid; grid-template-columns: 1fr; gap: 16px; }

@media (max-width: 900px) {
  .project-meta { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 560px) {
  .project-header { align-items: flex-start; flex-direction: column; }
  .project-heading h2 { font-size: 19px; }
  .project-meta { grid-template-columns: 1fr; gap: 12px; }
  .detail-card :deep(.el-card__body) { padding: 16px 12px; }
}
</style>
