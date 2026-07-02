<template>
  <div class="page">
    <el-button text @click="$router.back()">
      <el-icon><ArrowLeft /></el-icon> 返回
    </el-button>

    <div v-if="task" v-loading="loading">
      <h2 style="margin: 16px 0; color: var(--ad-text)">制作任务 {{ task.production_no }}</h2>

      <el-card shadow="never" class="info-card">
        <el-descriptions :column="2">
          <el-descriptions-item label="任务编号">{{ task.production_no }}</el-descriptions-item>
          <el-descriptions-item label="项目名称">{{ task.project_name }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusColor(task.status)">{{ statusLabel(task.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="尺寸">长{{ task.length }}m × 宽{{ task.width }}m × 高{{ task.height }}m</el-descriptions-item>
          <el-descriptions-item label="数量">{{ task.quantity }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card shadow="never" class="info-card" style="margin-top: 16px">
        <template #header><span>变更状态</span></template>
        <el-form :model="statusForm" inline>
          <el-form-item label="目标状态">
            <el-select v-model="statusForm.to_status" style="width: 160px">
              <el-option label="排队中" value="queued" />
              <el-option label="制作中" value="in_progress" />
              <el-option label="待质检" value="qc_check" />
              <el-option label="返工" value="rework" />
              <el-option label="已完成" value="completed" />
            </el-select>
          </el-form-item>
          <el-form-item label="原因">
            <el-input v-model="statusForm.reason" style="width: 200px" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="changing" @click="handleChangeStatus">变更</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card shadow="never" class="info-card" style="margin-top: 16px">
        <template #header><span>质检与返工</span></template>
        <el-form :model="editForm" label-width="120px">
          <el-form-item label="质检结果">
            <el-select v-model="editForm.qc_result" style="width: 200px">
              <el-option label="合格" value="pass" />
              <el-option label="不合格" value="fail" />
            </el-select>
          </el-form-item>
          <el-form-item label="返工原因" v-if="editForm.qc_result === 'fail'">
            <el-input v-model="editForm.rework_reason" type="textarea" :rows="2" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="updating" @click="handleUpdate">保存</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card shadow="never" class="info-card" style="margin-top: 16px">
        <template #header>
          <div class="card-header">
            <span>附件</span>
            <el-upload
              :http-request="handleUpload"
              :show-file-list="false"
              accept="image/*"
            >
              <el-button type="danger" size="small">上传文件</el-button>
            </el-upload>
          </div>
        </template>
        <el-table :data="task.attachments" stripe size="small">
          <el-table-column prop="filename" label="文件名" min-width="200" />
          <el-table-column prop="category" label="类别" width="100" />
          <el-table-column label="大小" width="100">
            <template #default="{ row }">{{ row.file_size ? (row.file_size / 1024).toFixed(1) + 'KB' : '-' }}</template>
          </el-table-column>
          <el-table-column label="操作" width="80">
            <template #default="{ row }">
              <el-button text type="danger" size="small" @click="handleDeleteAttachment(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getProductionTask, updateProductionTask, changeProductionTaskStatus, uploadAttachment, deleteAttachment } from '@/api/tasks'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadRequestOptions } from 'element-plus'
import type { ProductionTaskResponse } from '@/types/api'

const route = useRoute()
const loading = ref(false)
const updating = ref(false)
const changing = ref(false)
const task = ref<ProductionTaskResponse | null>(null)
const statusForm = reactive({ to_status: '', reason: '' })
const editForm = reactive({ qc_result: '', rework_reason: '' })

function statusLabel(s: string) {
  const map: Record<string, string> = { pending: '待制作', queued: '排队中', in_progress: '制作中', qc_check: '待质检', rework: '返工', completed: '已完成' }
  return map[s] || s
}
function statusColor(s: string) {
  const map: Record<string, string> = { pending: 'info', queued: 'warning', in_progress: '', qc_check: 'warning', rework: 'danger', completed: 'success' }
  return (map[s] || 'info') as 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined
}

async function fetchTask() {
  loading.value = true
  try { task.value = await getProductionTask(route.params.id as string) } finally { loading.value = false }
}

async function handleUpdate() {
  updating.value = true
  try {
    await updateProductionTask(route.params.id as string, editForm)
    ElMessage.success('保存成功')
    fetchTask()
  } catch { /* handled */ } finally { updating.value = false }
}

async function handleChangeStatus() {
  if (!statusForm.to_status) { ElMessage.warning('请选择目标状态'); return }
  await ElMessageBox.confirm(`确定将制作任务状态变更为「${statusForm.to_status}」？`, '变更状态', {
    confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning',
  })
  changing.value = true
  try {
    await changeProductionTaskStatus(route.params.id as string, statusForm)
    ElMessage.success('状态已变更')
    statusForm.to_status = ''
    statusForm.reason = ''
    fetchTask()
  } catch { /* handled */ } finally { changing.value = false }
}

async function handleUpload(req: UploadRequestOptions) {
  try {
    await uploadAttachment('production_task', route.params.id as string, req.file, 'production')
    ElMessage.success('上传成功')
    fetchTask()
  } catch { /* handled */ }
}

async function handleDeleteAttachment(id: string) {
  await ElMessageBox.confirm('确定删除此附件？删除后无法恢复。', '删除附件', {
    confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning',
  })
  await deleteAttachment(id)
  ElMessage.success('已删除')
  fetchTask()
}

onMounted(fetchTask)
</script>

<style scoped>
.page { padding: 0; }
.info-card { background: var(--ad-card); border: 1px solid var(--ad-border); color: var(--ad-text); }
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
