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
            只删除这条已取消任务，不删除订单、订单明细或内部任务。已取消任务的未付金额按取消的计划余额处理；任何付款或财务关联均会由服务器拒绝。
          </template>
        </el-alert>
        <el-descriptions :column="1" border class="delete-summary">
          <el-descriptions-item label="任务编号">{{ permanentDeleteTarget.task_no }}</el-descriptions-item>
          <el-descriptions-item label="外协商">{{ permanentDeleteTarget.vendor_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="关联项目">{{ permanentDeleteTarget.related_project_name || '-' }}</el-descriptions-item>
          <el-descriptions-item v-if="canViewOutsourceCost" label="金额">
            计划 {{ formatMoney(permanentDeleteTarget.total_amount) }}；已付 {{ formatMoney(permanentDeleteTarget.paid_amount) }}；未付 {{ formatMoney(permanentDeleteTarget.unpaid_amount) }}
          </el-descriptions-item>
          <el-descriptions-item label="关联记录">
            付款 {{ permanentDeleteTarget.permanent_delete_eligibility?.references.payment_count ?? '-' }} 条；
            日期核对 {{ permanentDeleteTarget.permanent_delete_eligibility?.references.reconciliation_count ?? '-' }} 条；
            费用审查 {{ permanentDeleteTarget.permanent_delete_eligibility?.references.cost_overlap_review_count ?? '-' }} 条；
            历史已清除付款流水 {{ permanentDeleteTarget.permanent_delete_eligibility?.references.legacy_deleted_payment_count ?? '-' }} 条
          </el-descriptions-item>
        </el-descriptions>
        <el-form label-position="top" class="delete-confirm-form">
          <el-form-item label="输入完整任务编号以确认">
            <el-input v-model="typedTaskNo" :placeholder="permanentDeleteTarget.task_no" autocomplete="off" />
          </el-form-item>
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
          :disabled="!permanentDeleteTarget || !isPermanentDeleteConfirmationValid(permanentDeleteTarget.task_no, typedTaskNo, permanentDeleteReason)"
          @click="handlePermanentDelete"
        >永久删除</el-button>
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
  isPermanentDeleteConfirmationValid,
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
const typedTaskNo = ref('')
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
  typedTaskNo.value = ''
  permanentDeleteReason.value = ''
  permanentDeleteError.value = ''
  permanentDeleteDialogVisible.value = true
}

async function handlePermanentDelete() {
  const target = permanentDeleteTarget.value
  if (!target || !isPermanentDeleteConfirmationValid(target.task_no, typedTaskNo.value, permanentDeleteReason.value)) return

  permanentDeleteSubmitting.value = true
  permanentDeleteError.value = ''
  try {
    await permanentlyDeleteOutsourceTask(target.id, {
      task_no_confirmation: typedTaskNo.value.trim(),
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
</style>
