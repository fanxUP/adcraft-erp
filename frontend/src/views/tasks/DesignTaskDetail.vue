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

      <el-card shadow="never" class="info-card" style="margin-top: 16px">
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
          <el-form-item label="设计说明">
            <el-input v-model="editForm.description" type="textarea" :rows="3" />
          </el-form-item>
          <el-form-item label="客户意见">
            <el-input v-model="editForm.client_comments" type="textarea" :rows="3" />
          </el-form-item>
          <el-form-item label="设计稿URL">
            <el-input v-model="editForm.design_file_url" placeholder="上传后自动填入" />
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
              accept="image/*,.pdf,.ai,.psd,.cdr,.dwg"
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
import { ElMessage } from 'element-plus'

const route = useRoute()
const loading = ref(false)
const updating = ref(false)
const changing = ref(false)
const task = ref<any>(null)
const statusForm = reactive({ to_status: '', reason: '' })
const editForm = reactive({ description: '', client_comments: '', design_file_url: '' })

function statusLabel(s: string) {
  const map: Record<string, string> = { pending: '待分配', designing: '设计中', pending_review: '待确认', revision: '需修改', confirmed: '已确认' }
  return map[s] || s
}
function statusColor(s: string) {
  const map: Record<string, string> = { pending: 'info', designing: '', pending_review: 'warning', revision: 'danger', confirmed: 'success' }
  return map[s] || 'info'
}

async function fetchTask() {
  loading.value = true
  try { task.value = await getDesignTask(route.params.id as string) } finally { loading.value = false }
}

async function handleUpdate() {
  updating.value = true
  try {
    await updateDesignTask(route.params.id as string, editForm)
    ElMessage.success('保存成功')
    fetchTask()
  } catch { /* handled */ } finally { updating.value = false }
}

async function handleChangeStatus() {
  if (!statusForm.to_status) { ElMessage.warning('请选择目标状态'); return }
  changing.value = true
  try {
    await changeDesignTaskStatus(route.params.id as string, statusForm)
    ElMessage.success('状态已变更')
    statusForm.to_status = ''
    statusForm.reason = ''
    fetchTask()
  } catch { /* handled */ } finally { changing.value = false }
}

async function handleUpload(req: any) {
  try {
    await uploadAttachment('design_task', route.params.id as string, req.file, 'design')
    ElMessage.success('上传成功')
    fetchTask()
  } catch { /* handled */ }
}

async function handleDeleteAttachment(id: string) {
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
