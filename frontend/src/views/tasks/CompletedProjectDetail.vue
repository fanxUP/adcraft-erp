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

        <div class="detail-heading">
          <div>
            <h3>完成明细</h3>
            <span>{{ project.items.length }} 条可见记录</span>
          </div>
          <span class="readonly-hint">只读</span>
        </div>

        <el-table
          v-if="project.items.length"
          :data="project.items"
          size="small"
          stripe
          class="detail-table"
          empty-text="暂无可见的完成明细"
        >
          <el-table-column prop="item_name" label="订单明细" min-width="220" show-overflow-tooltip />
          <el-table-column prop="task_label" label="阶段" width="90" align="center" />
          <el-table-column prop="task_no" label="任务编号" min-width="170" show-overflow-tooltip />
          <el-table-column prop="employee_name" label="执行人" width="120" />
          <el-table-column label="完成时间" min-width="180">
            <template #default="{ row }">{{ formatDateTimeFull(row.completed_at) }}</template>
          </el-table-column>
        </el-table>
        <el-empty v-else description="暂无可见的完成明细" :image-size="64" />
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
import type { CompletedProjectDetail as CompletedProjectDetailType } from '@/types/api'
import StatusTag from '@/components/ui/StatusTag.vue'
import { formatDateTimeFull } from '@/utils/datetime'
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
.project-header, .detail-heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.project-header { padding-bottom: 18px; border-bottom: 1px solid var(--ad-border); }
.project-heading { min-width: 0; }
.project-no { color: var(--ad-text-secondary); font-size: 13px; font-variant-numeric: tabular-nums; }
.project-heading h2 { margin: 6px 0 0; color: var(--ad-text); font-size: 22px; line-height: 1.45; }
.project-meta { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; margin: 0; padding: 20px 0 24px; }
.project-meta div { min-width: 0; }
.project-meta dt { margin-bottom: 5px; color: var(--ad-text-secondary); font-size: 12px; }
.project-meta dd { margin: 0; overflow: hidden; color: var(--ad-text); font-size: 14px; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.detail-heading { margin-bottom: 12px; }
.detail-heading h3 { display: inline; margin: 0 10px 0 0; color: var(--ad-text); font-size: 17px; }
.detail-heading span { color: var(--ad-text-secondary); font-size: 12px; }
.readonly-hint { padding: 3px 8px; border: 1px solid var(--ad-border); border-radius: 999px; }
.detail-table { width: 100%; }

@media (max-width: 900px) {
  .project-meta { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 560px) {
  .project-header { align-items: flex-start; flex-direction: column; }
  .project-heading h2 { font-size: 19px; }
  .project-meta { grid-template-columns: 1fr; gap: 12px; }
}
</style>
