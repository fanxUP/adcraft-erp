<template>
  <el-card shadow="never" class="info-card" style="margin-top: 16px">
    <template #header>
      <div class="card-header">
        <span>
          外协情况
          <el-tag v-if="outsourceTasks.length > 0" type="warning" size="small" style="margin-left: 8px">已外协</el-tag>
        </span>
        <div style="display: flex; gap: 8px; align-items: center;">
          <el-button type="danger" size="small" @click="openDialog">发送外协</el-button>
          <el-button text type="primary" size="small" @click="$router.push('/outsource/tasks')">外协任务管理</el-button>
        </div>
      </div>
    </template>

    <el-table :data="outsourceTasks" v-loading="loading" stripe size="small" empty-text="尚未发送外协">
      <el-table-column prop="task_no" label="外协编号" width="150" />
      <el-table-column prop="vendor_name" label="外协商" width="150" />
      <el-table-column prop="description" label="描述" min-width="150" show-overflow-tooltip />
      <el-table-column label="总金额" width="110" align="right">
        <template #default="{ row }">¥{{ Number(row.total_amount || 0).toFixed(2) }}</template>
      </el-table-column>
      <el-table-column label="未付" width="100" align="right">
        <template #default="{ row }">
          <span v-if="Number(row.unpaid_amount) > 0" style="color: var(--el-color-danger)">¥{{ Number(row.unpaid_amount).toFixed(2) }}</span>
          <span v-else style="color: var(--el-color-success)">已结清</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="预计完成" width="120">
        <template #default="{ row }">{{ row.expected_at ? row.expected_at.slice(0, 10) : '-' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="80">
        <template #default>
          <el-button text type="primary" size="small" @click="$router.push('/outsource/tasks')">查看</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" title="发送外协" width="520px" :close-on-click-modal="false" append-to-body>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="外协商" prop="vendor_id">
          <el-select v-model="form.vendor_id" filterable clearable placeholder="选择外协商" style="width: 100%">
            <el-option v-for="v in vendors" :key="v.id" :label="v.name" :value="v.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="数量" prop="quantity">
          <el-input-number v-model="form.quantity" :min="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="单价" prop="unit_price">
          <el-input-number v-model="form.unit_price" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="预计完成">
          <el-date-picker v-model="form.expected_at" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="saving" @click="handleSubmit">发送</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getOutsourceVendors, getOutsourceTasks, createOutsourceTask } from '@/api/outsource'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import type { VendorResponse, OutsourceTaskResponse } from '@/types/api'


const props = defineProps<{
  taskType: 'design' | 'production' | 'installation'
  taskId: string
  orderId: string
  projectName: string
}>()

const loading = ref(false)
const saving = ref(false)
const outsourceTasks = ref<OutsourceTaskResponse[]>([])
const vendors = ref<VendorResponse[]>([])
const dialogVisible = ref(false)
const formRef = ref<FormInstance>()
const form = reactive({
  vendor_id: '',
  description: '',
  quantity: 1,
  unit_price: 0,
  expected_at: '',
  remark: '',
})
const rules: FormRules = {
  vendor_id: [{ required: true, message: '请选择外协商', trigger: 'change' }],
}

function statusLabel(s: string) {
  const map: Record<string, string> = { pending: '待处理', in_progress: '进行中', completed: '已完成', settled: '已结算', cancelled: '已取消' }
  return map[s] || s
}
function statusType(s: string) {
  const map: Record<string, string> = { pending: 'info', in_progress: 'warning', completed: 'success', settled: '', cancelled: 'danger' }
  return (map[s] || 'info') as 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined
}

async function fetchOutsource() {
  loading.value = true
  try {
    const data = await getOutsourceTasks({ page: 1, page_size: 50, source_task_id: props.taskId, source_task_type: props.taskType })
    outsourceTasks.value = data.items
  } finally { loading.value = false }
}

async function loadVendors() {
  try {
    const data = await getOutsourceVendors({ page: 1, page_size: 100 })
    vendors.value = data.items
  } catch { /* handled */ }
}

function openDialog() {
  form.vendor_id = ''
  form.description = props.projectName || ''
  form.quantity = 1
  form.unit_price = 0
  form.expected_at = ''
  form.remark = ''
  dialogVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    await createOutsourceTask({
      vendor_id: form.vendor_id,
      task_type: props.taskType,
      related_doc_id: props.orderId,
      related_doc_type: 'order',
      source_task_type: props.taskType,
      source_task_id: props.taskId,
      description: form.description,
      quantity: form.quantity,
      unit_price: form.unit_price,
      expected_at: form.expected_at || undefined,
      remark: form.remark || undefined,
    })
    ElMessage.success('已发送外协')
    dialogVisible.value = false
    await fetchOutsource()
  } catch { /* handled */ } finally { saving.value = false }
}

onMounted(() => {
  void fetchOutsource()
  void loadVendors()
})
</script>

<style scoped>
.info-card { background: var(--ad-card); border: 1px solid var(--ad-border); color: var(--ad-text); }
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
