<template>
  <div class="page">
    <el-button text @click="$router.back()">
      <el-icon><ArrowLeft /></el-icon> 返回
    </el-button>

    <div v-if="task" v-loading="loading">
      <h2 style="margin: 16px 0; color: var(--ad-text)">安装任务 {{ task.installation_no }}</h2>

      <el-card shadow="never" class="info-card">
        <el-descriptions :column="2">
          <el-descriptions-item label="任务编号">{{ task.installation_no }}</el-descriptions-item>
          <el-descriptions-item label="项目名称">{{ task.project_name }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusColor(task.status)">{{ statusLabel(task.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="安装地址">{{ task.address || '-' }}</el-descriptions-item>
          <el-descriptions-item label="联系人">{{ task.contact_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="联系电话">{{ task.contact_phone || '-' }}</el-descriptions-item>
          <el-descriptions-item label="计划时间">{{ task.scheduled_at?.slice(0, 19).replace('T', ' ') || '-' }}</el-descriptions-item>
          <el-descriptions-item label="验收结果">{{ task.acceptance_result || '-' }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card shadow="never" class="info-card" style="margin-top: 16px">
        <template #header><span>变更状态</span></template>
        <el-form :model="statusForm" inline>
          <el-form-item label="目标状态">
            <el-select v-model="statusForm.to_status" style="width: 160px">
              <el-option label="已分配" value="assigned" />
              <el-option label="安装中" value="in_progress" />
              <el-option label="待验收" value="pending_acceptance" />
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
        <template #header><span>验收</span></template>
        <el-form :model="editForm" label-width="120px">
          <el-form-item label="验收结果">
            <el-input v-model="editForm.acceptance_result" type="textarea" :rows="3" placeholder="填写验收意见..." />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="updating" @click="handleUpdate">保存</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card shadow="never" class="info-card" style="margin-top: 16px">
        <template #header>
          <div class="card-header">
            <span>现场照片</span>
            <el-upload
              :http-request="handleUpload"
              :show-file-list="false"
              accept="image/*"
              multiple
            >
              <el-button type="danger" size="small">上传照片</el-button>
            </el-upload>
          </div>
        </template>
        <div class="photo-grid" v-if="task.attachments?.length">
          <div v-for="att in task.attachments" :key="att.id" class="photo-item">
            <img :src="`/uploads/${att.file_path}`" :alt="att.filename" class="photo-img" />
            <div class="photo-actions">
              <span class="photo-label">{{ att.category || att.filename }}</span>
              <el-button text type="danger" size="small" @click="handleDeleteAttachment(att.id)">删除</el-button>
            </div>
          </div>
        </div>
        <div v-else style="color: #666; padding: 20px; text-align: center">暂无照片</div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getInstallationTask, updateInstallationTask, changeInstallationTaskStatus, uploadAttachment, deleteAttachment } from '@/api/tasks'
import { ElMessage } from 'element-plus'
import type { UploadRequestOptions } from 'element-plus'
import type { InstallationTaskResponse } from '@/types/api'

const route = useRoute()
const loading = ref(false)
const updating = ref(false)
const changing = ref(false)
const task = ref<InstallationTaskResponse | null>(null)
const statusForm = reactive({ to_status: '', reason: '' })
const editForm = reactive({ acceptance_result: '' })

function statusLabel(s: string) {
  const map: Record<string, string> = { pending: '待分配', assigned: '已分配', in_progress: '安装中', pending_acceptance: '待验收', completed: '已完成' }
  return map[s] || s
}
function statusColor(s: string) {
  const map: Record<string, string> = { pending: 'info', assigned: '', in_progress: 'warning', pending_acceptance: 'warning', completed: 'success' }
  return (map[s] || 'info') as 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined
}

async function fetchTask() {
  loading.value = true
  try { task.value = await getInstallationTask(route.params.id as string) } finally { loading.value = false }
}

async function handleUpdate() {
  updating.value = true
  try {
    await updateInstallationTask(route.params.id as string, editForm)
    ElMessage.success('保存成功')
    fetchTask()
  } catch { /* handled */ } finally { updating.value = false }
}

async function handleChangeStatus() {
  if (!statusForm.to_status) { ElMessage.warning('请选择目标状态'); return }
  changing.value = true
  try {
    await changeInstallationTaskStatus(route.params.id as string, statusForm)
    ElMessage.success('状态已变更')
    statusForm.to_status = ''
    statusForm.reason = ''
    fetchTask()
  } catch { /* handled */ } finally { changing.value = false }
}

async function handleUpload(req: UploadRequestOptions) {
  try {
    const cat = req.file.type.startsWith('image/') ? 'photo' : 'file'
    await uploadAttachment('installation_task', route.params.id as string, req.file, cat)
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
.photo-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }
.photo-item { background: #252540; border-radius: 6px; overflow: hidden; border: 1px solid var(--ad-border); }
.photo-img { width: 100%; height: 160px; object-fit: cover; }
.photo-actions { padding: 6px 10px; display: flex; justify-content: space-between; align-items: center; }
.photo-label { font-size: 12px; color: #888; }
</style>
