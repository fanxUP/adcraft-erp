<template>
  <AppPage>
    <template #header><PageHeader title="外协任务回收站" description="查看已删除的外协任务并恢复需要继续保留的记录。">
      <template #actions><el-button text @click="$router.push('/outsource/tasks')"><el-icon><ArrowLeft /></el-icon> 返回外协任务</el-button></template>
    </PageHeader></template>

    <DataTableShell :state="tableState" aria-label="外协任务回收站列表">
      <el-table :data="list" stripe>
      <el-table-column prop="task_no" label="任务编号" width="180" />
      <el-table-column prop="vendor_name" label="外协商" width="140" />
      <el-table-column label="关联任务" width="160" show-overflow-tooltip>
        <template #default="{ row }">
          <span v-if="row.related_project_name">{{ row.related_project_name }}</span>
          <span v-else style="color: #999">-</span>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="描述" min-width="180" show-overflow-tooltip />
      <el-table-column v-if="canViewOutsourceCost" prop="total_amount" label="总金额" width="120" align="right">
        <template #default="{ row }">{{ formatMoney(row.total_amount) }}</template>
      </el-table-column>
      <el-table-column label="原状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="deleted_at" label="删除时间" width="160">
        <template #default="{ row }">{{ formatDateTimeFull(row.deleted_at) }}</template>
      </el-table-column>
      <el-table-column v-if="canUsePermanentDelete" label="永久删除资格" min-width="160">
        <template #default="{ row }">
          <el-tooltip :content="permanentDeleteBlockMessage(row.permanent_delete_eligibility)" placement="top">
            <el-tag :type="canPermanentlyDelete(row.permanent_delete_eligibility) ? 'success' : 'danger'" size="small">
              {{ canPermanentlyDelete(row.permanent_delete_eligibility) ? '可永久删除' : '暂不可删除' }}
            </el-tag>
          </el-tooltip>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="250">
        <template #default="{ row }">
          <el-button text type="success" @click="handleRestore(row)">恢复</el-button>
          <el-button
            v-if="canUsePermanentDelete"
            text
            type="danger"
            :disabled="!canPermanentlyDelete(row.permanent_delete_eligibility)"
            @click="openPermanentDeleteDialog(row)"
          >永久删除</el-button>
        </template>
      </el-table-column>
      </el-table>
      <template #error><StatePanel state="error" action-label="重新加载" @action="fetchData" /></template>
    </DataTableShell>

    <el-pagination v-if="tableState === 'ready'"
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :page-sizes="[10, 20, 50, 100]"
      :total="total"
      layout="total, sizes, prev, pager, next"
      style="margin-top: 16px; justify-content: flex-end"
      @change="fetchData"
    />

    <el-dialog
      v-model="permanentDeleteDialogVisible"
      title="永久删除外协任务"
      width="560px"
      :close-on-click-modal="false"
      :close-on-press-escape="!permanentDeleteSubmitting"
      :show-close="!permanentDeleteSubmitting"
    >
      <template v-if="permanentDeleteTarget">
        <el-alert type="error" :closable="false" show-icon>
          <template #title>此操作不可恢复，请先确认下列记录及影响</template>
          <template #default>
            将删除当前外协任务及其外协付款、付款日期核对和费用重叠审查记录。关联订单、订单明细、设计/制作/安装任务、项目成本及操作审计会保留；删除后这些外协付款不再计入支出台账。
          </template>
        </el-alert>
        <el-descriptions :column="1" border class="delete-summary">
          <el-descriptions-item label="任务编号">{{ permanentDeleteTarget.task_no }}</el-descriptions-item>
          <el-descriptions-item label="原任务状态">{{ statusLabel(permanentDeleteTarget.status) }}</el-descriptions-item>
          <el-descriptions-item label="外协商">{{ permanentDeleteTarget.vendor_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="关联业务">
            <div v-if="permanentDeleteTarget.linked_records?.length" class="linked-record-list">
              <div v-for="record in permanentDeleteTarget.linked_records" :key="`${record.kind}-${record.id}`" class="linked-record">
                <el-tag size="small" type="info">{{ record.label }}</el-tag>
                <span class="linked-record-number">{{ record.business_no || record.id }}</span>
                <span v-if="record.name">{{ record.name }}</span>
                <span v-if="record.status" class="linked-record-status">状态：{{ record.status }}</span>
              </div>
            </div>
            <span v-else>-</span>
          </el-descriptions-item>
          <el-descriptions-item v-if="canViewOutsourceCost" label="金额">
            计划 {{ formatMoney(permanentDeleteTarget.total_amount) }}；已付 {{ formatMoney(permanentDeleteTarget.paid_amount) }}；未付 {{ formatMoney(permanentDeleteTarget.unpaid_amount) }}
          </el-descriptions-item>
          <el-descriptions-item label="将删除的财务记录">
            外协付款 {{ permanentDeleteTarget.permanent_delete_eligibility?.references.payment_count ?? '-' }} 条
            <template v-if="canViewOutsourceCost">，合计 {{ formatMoney(permanentDeleteTarget.permanent_delete_eligibility?.references.payment_total_amount) }}</template>；
            付款日期核对 {{ permanentDeleteTarget.permanent_delete_eligibility?.references.reconciliation_count ?? '-' }} 条（含已撤销）
            <template v-if="canViewOutsourceCost">，合计 {{ formatMoney(permanentDeleteTarget.permanent_delete_eligibility?.references.reconciliation_total_amount) }}</template>；
            费用重叠审查 {{ permanentDeleteTarget.permanent_delete_eligibility?.references.cost_overlap_review_count ?? '-' }} 条。
          </el-descriptions-item>
          <el-descriptions-item label="历史审计记录">
            旧版日志记录曾清除付款流水 {{ permanentDeleteTarget.permanent_delete_eligibility?.references.legacy_deleted_payment_count ?? '-' }} 条；本次不会删除这些日志。
          </el-descriptions-item>
          <el-descriptions-item label="保留的数据">
            项目成本、订单/明细、来源设计/制作/安装任务和操作审计均保留；关联记录只解除与本外协任务的关系。
          </el-descriptions-item>
        </el-descriptions>
        <el-form label-position="top" class="delete-confirm-form">
          <el-form-item label="删除原因（5–500 字）">
            <el-input v-model="permanentDeleteReason" type="textarea" :rows="3" maxlength="500" show-word-limit />
          </el-form-item>
        </el-form>
        <el-alert v-if="permanentDeleteError" type="error" :closable="false" :title="permanentDeleteError" />
      </template>
      <template #footer>
        <el-button :disabled="permanentDeleteSubmitting" @click="permanentDeleteDialogVisible = false">取消</el-button>
        <el-button
          type="danger"
          :loading="permanentDeleteSubmitting"
          :disabled="!permanentDeleteTarget || !isPermanentDeleteReasonValid(permanentDeleteReason)"
          @click="handlePermanentDelete"
        >确认永久删除</el-button>
      </template>
    </el-dialog>
  </AppPage>
</template>

<script setup lang="ts">
import { formatDateTimeFull } from '@/utils/datetime'
import { computed, ref, onMounted } from 'vue'
import { getDeletedOutsourceTasks, permanentlyDeleteOutsourceTask, restoreOutsourceTask } from '@/api/outsource'
import type { OutsourceTaskResponse } from '@/types/api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { AppPage, DataTableShell, PageHeader, StatePanel } from '@/components/ui'
import { formatMoney } from '@/utils/format'
import { useAuthStore } from '@/stores/auth'
import {
  canPermanentlyDelete,
  isPermanentDeleteReasonValid,
  permanentDeleteBlockMessage,
} from '@/utils/outsourceTaskPermanentDelete'

const loading = ref(false)
const list = ref<OutsourceTaskResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loadError = ref('')
const tableState = computed(() => loading.value ? 'loading' : loadError.value ? 'error' : list.value.length ? 'ready' : 'empty')
const authStore = useAuthStore()
const canViewOutsourceCost = computed(() => authStore.hasPermission('finance:view_cost'))
const canUsePermanentDelete = computed(() => authStore.can('outsource_task:permanent_delete'))
const permanentDeleteDialogVisible = ref(false)
const permanentDeleteSubmitting = ref(false)
const permanentDeleteTarget = ref<OutsourceTaskResponse | null>(null)
const permanentDeleteReason = ref('')
const permanentDeleteError = ref('')

function statusLabel(val: string) {
  const map: Record<string, string> = { pending: '待处理', in_progress: '进行中', completed: '已完成', settled: '已结算', cancelled: '已取消' }
  return map[val] || val
}

function statusTagType(val: string) {
  const map: Record<string, string> = { pending: 'warning', in_progress: '', completed: 'success', settled: 'info', cancelled: 'danger' }
  return (map[val] || 'info') as 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined
}

async function fetchData() {
  loading.value = true
  loadError.value = ''
  try {
    const data = await getDeletedOutsourceTasks({ page: page.value, page_size: pageSize.value })
    list.value = data.items as OutsourceTaskResponse[]
    total.value = data.total
  } catch (error: unknown) {
    loadError.value = error instanceof Error ? error.message : '加载回收站失败'
    ElMessage.error(loadError.value)
  } finally {
    loading.value = false
  }
}

async function handleRestore(row: OutsourceTaskResponse) {
  await ElMessageBox.confirm(`确定恢复外协任务「${row.task_no}」？恢复后状态为已取消。`, '恢复任务', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  })
  await restoreOutsourceTask(row.id)
  ElMessage.success('外协任务已恢复')
  fetchData()
}

function openPermanentDeleteDialog(row: OutsourceTaskResponse) {
  if (!canUsePermanentDelete.value || !canPermanentlyDelete(row.permanent_delete_eligibility)) return
  permanentDeleteTarget.value = row
  permanentDeleteReason.value = ''
  permanentDeleteError.value = ''
  permanentDeleteDialogVisible.value = true
}

async function handlePermanentDelete() {
  const target = permanentDeleteTarget.value
  if (!target || !isPermanentDeleteReasonValid(permanentDeleteReason.value)) return

  permanentDeleteSubmitting.value = true
  permanentDeleteError.value = ''
  try {
    await permanentlyDeleteOutsourceTask(target.id, {
      reason: permanentDeleteReason.value.trim(),
    })
    permanentDeleteDialogVisible.value = false
    ElMessage.success(`外协任务 ${target.task_no} 已永久删除`)
    await fetchData()
  } catch (error: unknown) {
    permanentDeleteError.value = error instanceof Error ? error.message : '永久删除失败，请刷新资格后重试'
  } finally {
    permanentDeleteSubmitting.value = false
  }
}

onMounted(fetchData)
</script>

<style scoped>
.delete-summary {
  margin-top: 16px;
}

.delete-confirm-form {
  margin-top: 18px;
}

.linked-record-list {
  display: grid;
  gap: 8px;
}

.linked-record {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.linked-record-number {
  font-weight: 600;
}

.linked-record-status {
  color: var(--el-text-color-secondary);
}
</style>
