<template>
  <div class="mobile-page">
    <div class="mobile-header">
      <span class="mobile-title">安装任务</span>
    </div>

    <div v-if="tasks.length === 0 && !loading" class="empty-state">暂无安装任务</div>

    <div v-for="task in tasks" :key="task.id" class="task-card" @click="openTask(task)">
      <div class="task-header">
        <span class="task-no">{{ task.installation_no }}</span>
        <el-tag :type="statusColor(task.status)" size="small">{{ statusLabel(task.status) }}</el-tag>
      </div>
      <div class="task-name">{{ task.project_name }}</div>
      <div class="task-info">
        <div><el-icon><Location /></el-icon> {{ task.address || '-' }}</div>
        <div><el-icon><User /></el-icon> {{ task.contact_name || '-' }} {{ task.contact_phone || '' }}</div>
        <div><el-icon><Clock /></el-icon> {{ task.scheduled_at?.slice(0, 10) || '-' }}</div>
      </div>
    </div>

    <el-drawer v-model="drawerVisible" :title="currentTask?.project_name" direction="btt" size="85%">
      <div v-if="currentTask" class="drawer-content">
        <el-descriptions :column="1" size="small">
          <el-descriptions-item label="任务编号">{{ currentTask.installation_no }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusColor(currentTask.status)" size="small">{{ statusLabel(currentTask.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="地址">{{ currentTask.address }}</el-descriptions-item>
          <el-descriptions-item label="联系人">{{ currentTask.contact_name }}</el-descriptions-item>
          <el-descriptions-item label="电话">
            <a :href="`tel:${currentTask.contact_phone}`" style="color: #e63946">{{ currentTask.contact_phone }}</a>
          </el-descriptions-item>
        </el-descriptions>

        <div style="margin-top: 16px">
          <el-button type="primary" block @click="takePhoto" style="margin-bottom: 8px">
            <el-icon><Camera /></el-icon> 拍照
          </el-button>
          <el-button block @click="uploadPhoto">
            <el-icon><Upload /></el-icon> 从相册选择
          </el-button>
          <input ref="fileInput" type="file" accept="image/*" capture="environment" style="display: none" @change="onFileChange" />
        </div>

        <el-divider />

        <div class="photo-grid" v-if="currentTask.attachments?.length">
          <div v-for="att in currentTask.attachments" :key="att.id" class="photo-item">
            <img :src="`/uploads/${att.file_path}`" :alt="att.filename" class="photo-img" />
          </div>
        </div>
        <div v-else style="color: #999; text-align: center; padding: 20px">暂无现场照片</div>

        <el-divider />

        <div class="status-actions">
          <el-button
            v-for="s in nextStatuses"
            :key="s.value"
            :type="s.type"
            block
            style="margin-bottom: 8px"
            @click="changeStatus(s.value)"
          >
            {{ s.label }}
          </el-button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { getInstallationTasks, getInstallationTask, changeInstallationTaskStatus, uploadAttachment } from '@/api/tasks'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const tasks = ref<any[]>([])
const currentTask = ref<any>(null)
const drawerVisible = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

const statusTransitions: Record<string, { value: string; label: string; type: string }[]> = {
  pending: [{ value: 'assigned', label: '已分配', type: '' }, { value: 'in_progress', label: '开始安装', type: 'primary' }],
  assigned: [{ value: 'in_progress', label: '开始安装', type: 'primary' }],
  in_progress: [{ value: 'pending_acceptance', label: '提交验收', type: 'success' }],
  pending_acceptance: [{ value: 'completed', label: '验收通过', type: 'success' }, { value: 'in_progress', label: '返回安装', type: 'warning' }],
  completed: [],
}

const nextStatuses = computed(() => currentTask.value ? (statusTransitions[currentTask.value.status] || []) : [])

function statusLabel(s: string) {
  const map: Record<string, string> = { pending: '待分配', assigned: '已分配', in_progress: '安装中', pending_acceptance: '待验收', completed: '已完成' }
  return map[s] || s
}
function statusColor(s: string) {
  const map: Record<string, string> = { pending: 'info', assigned: '', in_progress: 'warning', pending_acceptance: 'warning', completed: 'success' }
  return map[s] || 'info'
}

async function fetchTasks() {
  loading.value = true
  try {
    const data = await getInstallationTasks({ page_size: 50, status: 'in_progress,pending_acceptance,assigned,pending' })
    tasks.value = data.items
  } finally { loading.value = false }
}

async function openTask(task: any) {
  currentTask.value = await getInstallationTask(task.id)
  drawerVisible.value = true
}

function takePhoto() {
  if (fileInput.value) {
    fileInput.value.setAttribute('capture', 'environment')
    fileInput.value.click()
  }
}

function uploadPhoto() {
  if (fileInput.value) {
    fileInput.value.removeAttribute('capture')
    fileInput.value.click()
  }
}

async function onFileChange(ev: Event) {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file || !currentTask.value) return
  try {
    await uploadAttachment('installation_task', currentTask.value.id, file, 'photo')
    ElMessage.success('上传成功')
    currentTask.value = await getInstallationTask(currentTask.value.id)
  } catch { /* handled */ }
  input.value = ''
}

async function changeStatus(toStatus: string) {
  if (!currentTask.value) return
  try {
    await changeInstallationTaskStatus(currentTask.value.id, { to_status: toStatus })
    ElMessage.success('状态已更新')
    currentTask.value = await getInstallationTask(currentTask.value.id)
    fetchTasks()
  } catch { /* handled */ }
}

onMounted(fetchTasks)
</script>

<style scoped>
.mobile-page { max-width: 480px; margin: 0 auto; padding: 12px; min-height: 100vh; background: #0f0f1a; }
.mobile-header { padding: 12px 0; text-align: center; }
.mobile-title { font-size: 18px; font-weight: bold; color: var(--ad-text); }
.empty-state { text-align: center; color: #666; padding: 60px 0; }
.task-card { background: var(--ad-card); border: 1px solid var(--ad-border); border-radius: 8px; padding: 14px; margin-bottom: 10px; cursor: pointer; }
.task-card:active { border-color: #e63946; }
.task-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.task-no { font-size: 12px; color: #888; }
.task-name { font-weight: bold; color: var(--ad-text); margin-bottom: 8px; font-size: 15px; }
.task-info { font-size: 13px; color: #999; display: flex; flex-direction: column; gap: 4px; }
.task-info > div { display: flex; align-items: center; gap: 4px; }
.drawer-content { padding: 0 8px; }
.photo-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
.photo-item { border-radius: 6px; overflow: hidden; }
.photo-img { width: 100%; height: 140px; object-fit: cover; }
.status-actions { margin-top: 16px; }
</style>
