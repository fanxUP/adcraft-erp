<template>
  <div class="page">
    <el-button text @click="$router.back()">
      <el-icon><ArrowLeft /></el-icon> 返回
    </el-button>

    <div v-if="task" v-loading="loading">
      <h2 style="margin: 16px 0; color: var(--ad-text)">设计任务 {{ task.design_no }}</h2>

      <el-card shadow="never" class="info-card">
        <el-descriptions :column="2">
          <el-descriptions-item label="任务编号">{{ task.design_no }}</el-descriptions-item>
          <el-descriptions-item label="项目名称">{{ task.project_name }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusColor(task.status)">{{ statusLabel(task.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="设计说明">{{ task.description || '-' }}</el-descriptions-item>
          <el-descriptions-item label="客户意见">{{ task.client_comments || '-' }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card
        data-ai-targets="task-status-designing task-status-pending_review task-status-revision task-status-confirmed"
        shadow="never"
        class="info-card"
        style="margin-top: 16px"
      >
        <template #header><span>变更状态</span></template>
        <el-form :model="statusForm" inline>
          <el-form-item label="目标状态">
            <el-select v-model="statusForm.to_status" style="width: 160px">
              <el-option label="设计中" value="designing" />
              <el-option label="待确认" value="pending_review" />
              <el-option label="需修改" value="revision" />
              <el-option label="已确认" value="confirmed" />
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
        <template #header>
          <div class="card-header"><span>更新信息</span></div>
        </template>
        <el-form :model="editForm" label-width="120px">
          <el-form-item label="负责人" data-ai-target="task-assignee">
            <el-select
              v-model="editForm.assigned_to"
              placeholder="选择设计师"
              clearable
              filterable
              style="width: 100%"
            >
              <el-option
                v-for="user in userOptions"
                :key="user.id"
                :label="user.real_name || user.username"
                :value="user.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="设计说明">
            <el-input v-model="editForm.description" type="textarea" :rows="3" />
          </el-form-item>
          <el-form-item label="客户意见">
            <el-input v-model="editForm.client_comments" type="textarea" :rows="3" />
          </el-form-item>
          <el-form-item label="设计稿" data-ai-target="design-file">
            <div class="design-file-field">
              <el-input v-model="editForm.design_file_url" placeholder="上传后自动填入，也可粘贴文件链接" />
              <el-upload
                :http-request="handleUpload"
                :show-file-list="false"
                accept="image/*,.pdf,.ai,.psd,.cdr,.dwg"
              >
                <el-button type="danger">上传设计稿</el-button>
              </el-upload>
            </div>
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
          </div>
        </template>
        <el-table :data="task.attachments" stripe size="small">
          <el-table-column prop="filename" label="文件名" min-width="200" />
          <el-table-column prop="category" label="类别" width="100" />
          <el-table-column label="大小" width="100">
            <template #default="{ row }">{{ row.file_size ? (row.file_size / 1024).toFixed(1) + 'KB' : '-' }}</template>
          </el-table-column>
          <el-table-column label="时间" width="180">
            <template #default="{ row }">{{ row.created_at?.slice(0, 19).replace('T', ' ') }}</template>
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
import { getDesignTask, updateDesignTask, changeDesignTaskStatus, uploadAttachment, deleteAttachment } from '@/api/tasks'
import { getUsers } from '@/api/users'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadRequestOptions } from 'element-plus'
import type { DesignTaskResponse, UserResponse } from '@/types/api'
import { useAiAssistantStore } from '@/stores/aiAssistantStore'

const route = useRoute()
const aiStore = useAiAssistantStore()
const loading = ref(false)
const updating = ref(false)
const changing = ref(false)
const task = ref<DesignTaskResponse | null>(null)
const userOptions = ref<UserResponse[]>([])
const statusForm = reactive({ to_status: '', reason: '' })
const editForm = reactive({
  assigned_to: '',
  description: '',
  client_comments: '',
  design_file_url: '',
})

function statusLabel(s: string) {
  const map: Record<string, string> = { pending: '待分配', designing: '设计中', pending_review: '待确认', revision: '需修改', confirmed: '已确认' }
  return map[s] || s
}
function statusColor(s: string) {
  const map: Record<string, string> = { pending: 'info', designing: '', pending_review: 'warning', revision: 'danger', confirmed: 'success' }
  return (map[s] || 'info') as 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined
}

async function fetchTask() {
  loading.value = true
  try {
    const data = await getDesignTask(route.params.id as string)
    task.value = data
    Object.assign(editForm, {
      assigned_to: data.assigned_to || '',
      description: data.description || '',
      client_comments: data.client_comments || '',
      design_file_url: data.design_file_url || '',
    })
  } finally { loading.value = false }
}

async function loadUsers() {
  const data = await getUsers({ page_size: 100 })
  userOptions.value = data.items
}

async function handleUpdate() {
  updating.value = true
  try {
    await updateDesignTask(route.params.id as string, {
      ...editForm,
      assigned_to: editForm.assigned_to || null,
    })
    ElMessage.success('保存成功')
    await fetchTask()
    await aiStore.notifyBusinessMutation()
  } catch { /* handled */ } finally { updating.value = false }
}

async function handleChangeStatus() {
  if (!statusForm.to_status) { ElMessage.warning('请选择目标状态'); return }
  await ElMessageBox.confirm(`确定将设计任务状态变更为「${statusForm.to_status}」？`, '变更状态', {
    confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning',
  })
  changing.value = true
  try {
    await changeDesignTaskStatus(route.params.id as string, statusForm)
    ElMessage.success('状态已变更')
    statusForm.to_status = ''
    statusForm.reason = ''
    await fetchTask()
    await aiStore.notifyBusinessMutation()
  } catch { /* handled */ } finally { changing.value = false }
}

async function handleUpload(req: UploadRequestOptions) {
  try {
    const attachment = await uploadAttachment(
      'design_task',
      route.params.id as string,
      req.file,
      'design',
    )
    await updateDesignTask(route.params.id as string, {
      design_file_url: `/uploads/${attachment.file_path}`,
    })
    ElMessage.success('上传成功')
    await fetchTask()
    await aiStore.notifyBusinessMutation()
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

onMounted(() => {
  void fetchTask()
  void loadUsers()
})
</script>

<style scoped>
.page { padding: 0; }
.info-card { background: var(--ad-card); border: 1px solid var(--ad-border); color: var(--ad-text); }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.design-file-field { display: flex; width: 100%; gap: 8px; }
.design-file-field .el-input { flex: 1; }
@media (max-width: 640px) {
  .design-file-field { align-items: stretch; flex-direction: column; }
}
</style>
