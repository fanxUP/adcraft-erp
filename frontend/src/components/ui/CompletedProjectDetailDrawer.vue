<template>
  <el-drawer
    :model-value="modelValue"
    title="完成项目详情"
    size="min(760px, 100%)"
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div v-loading="loading" class="drawer-content">
      <el-alert
        v-if="error"
        :title="error"
        type="warning"
        :closable="false"
        show-icon
        class="drawer-alert"
      />

      <template v-if="project">
        <div class="project-header">
          <div>
            <div class="project-no">{{ project.project_no }}</div>
            <h3>{{ project.project_name }}</h3>
          </div>
          <StatusTag status="completed" size="md" />
        </div>

        <div class="project-meta">
          <div>
            <span>客户名称</span>
            <strong>{{ project.customer_name || '-' }}</strong>
          </div>
          <div>
            <span>部门/科室</span>
            <strong>{{ project.department || '-' }}</strong>
          </div>
          <div>
            <span>完成时间</span>
            <strong>{{ formatDateTimeFull(project.completed_at) }}</strong>
          </div>
          <div v-if="project.total_amount !== null && project.total_amount !== undefined">
            <span>订单金额</span>
            <strong>¥ {{ formatMoney(project.total_amount) }}</strong>
          </div>
        </div>

        <div class="detail-heading">
          <span>完成明细</span>
          <small>{{ project.items.length }} 条可见记录</small>
        </div>
        <el-table
          v-if="project.items.length"
          :data="project.items"
          size="small"
          stripe
          class="detail-table"
          row-key="order_item_id"
        >
          <el-table-column prop="item_name" label="订单明细" min-width="170" show-overflow-tooltip />
          <el-table-column prop="task_label" label="阶段" width="80" align="center" />
          <el-table-column prop="task_no" label="任务编号" width="150" show-overflow-tooltip />
          <el-table-column prop="employee_name" label="执行人" width="100" />
          <el-table-column label="完成时间" width="165">
            <template #default="{ row }">{{ formatDateTimeFull(row.completed_at) }}</template>
          </el-table-column>
        </el-table>
        <el-empty v-else description="暂无可见的完成明细" :image-size="64" />
      </template>

      <el-empty v-else-if="!loading && !error" description="暂无项目详情" :image-size="64" />
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import type { CompletedProjectDetail } from '@/types/api'
import StatusTag from './StatusTag.vue'
import { formatDateTimeFull } from '@/utils/datetime'
import { formatMoney } from '@/utils/format'

defineProps<{
  modelValue: boolean
  project: CompletedProjectDetail | null
  loading?: boolean
  error?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()
</script>

<style scoped>
.drawer-content {
  min-height: 220px;
}

.drawer-alert {
  margin-bottom: 16px;
}

.project-header,
.detail-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.project-header {
  padding-bottom: 16px;
  border-bottom: 1px solid var(--ad-border);
}

.project-no {
  color: var(--ad-text-secondary);
  font-size: 13px;
}

h3 {
  margin: 6px 0 0;
  color: var(--ad-text);
  font-size: 20px;
}

.project-meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  padding: 16px 0 20px;
}

.project-meta div {
  min-width: 0;
}

.project-meta span,
.project-meta strong {
  display: block;
}

.project-meta span {
  margin-bottom: 4px;
  color: var(--ad-text-secondary);
  font-size: 12px;
}

.project-meta strong {
  overflow: hidden;
  color: var(--ad-text);
  font-size: 14px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detail-heading {
  margin-bottom: 10px;
  color: var(--ad-text);
  font-size: 16px;
  font-weight: 700;
}

.detail-heading small {
  color: var(--ad-text-secondary);
  font-size: 12px;
  font-weight: 400;
}

.detail-table {
  width: 100%;
}

@media (max-width: 560px) {
  .project-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .project-meta {
    grid-template-columns: 1fr;
  }
}
</style>
