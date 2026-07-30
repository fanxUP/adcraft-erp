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
        <div class="dtw-bar">
          <div class="dtw-flow">
            <!-- 1. 待分配 -->
            <div class="dtw-col">
              <div class="dtw-card" :class="dwCard('pending')" @click="dwClick('pending')">
                <div class="dtw-icon" :class="dwIcon('pending')">
                  <el-icon v-if="dwPast('pending')" :size="16"><Check /></el-icon>
                  <span v-else>1</span>
                </div>
                <div class="dtw-text">
                  <div class="dtw-label">待分配</div>
                  <div class="dtw-tag" :class="dwTagClass('pending')" v-text="dwTagText('pending')"></div>
                </div>
              </div>
            </div>
            <div class="dtw-conn" :class="dwConn('designing')">
              <div class="dtw-line"></div><div class="dtw-point">▶</div>
            </div>

            <!-- 2. 设计中 -->
            <div class="dtw-col">
              <div data-ai-target="task-status-designing" class="dtw-card" :class="dwCard('designing')" @click="dwClick('designing')">
                <div class="dtw-icon" :class="dwIcon('designing')">
                  <el-icon v-if="dwPast('designing')" :size="16"><Check /></el-icon>
                  <span v-else>2</span>
                </div>
                <div class="dtw-text">
                  <div class="dtw-label">设计中</div>
                  <div class="dtw-tag" :class="dwTagClass('designing')" v-text="dwTagText('designing')"></div>
                </div>
              </div>
            </div>
            <div class="dtw-conn" :class="dwBranchConnClass()">
              <div class="dtw-line"></div><div class="dtw-point">▶</div>
            </div>

            <!-- 3+4. 待确认 / 需修改 (并列) -->
            <div class="dtw-branch">
              <div class="dtw-col">
                <div data-ai-target="task-status-pending_review" class="dtw-card" :class="dwCard('pending_review')" @click="dwClick('pending_review')">
                  <div class="dtw-icon" :class="dwIcon('pending_review')">
                    <el-icon v-if="dwPast('pending_review')" :size="16"><Check /></el-icon>
                    <span v-else>3</span>
                  </div>
                  <div class="dtw-text">
                    <div class="dtw-label">待确认</div>
                    <div class="dtw-tag" :class="dwTagClass('pending_review')" v-text="dwTagText('pending_review')"></div>
                  </div>
                </div>
              </div>
              <div class="dtw-branch-sep"></div>
              <div class="dtw-col">
                <div data-ai-target="task-status-revision" class="dtw-card" :class="dwCard('revision')" @click="dwClick('revision')">
                  <div class="dtw-icon" :class="dwIcon('revision')">
                    <el-icon v-if="dwPast('revision')" :size="16"><Check /></el-icon>
                    <span v-else>4</span>
                  </div>
                  <div class="dtw-text">
                    <div class="dtw-label">需修改</div>
                    <div class="dtw-tag" :class="dwTagClass('revision')" v-text="dwTagText('revision')"></div>
                  </div>
                </div>
              </div>
            </div>
            <div class="dtw-conn" :class="dwConn('confirmed')">
              <div class="dtw-line"></div><div class="dtw-point">▶</div>
            </div>

            <!-- 5. 已完成 -->
            <div class="dtw-col">
              <div data-ai-target="task-status-confirmed" class="dtw-card" :class="dwCard('confirmed')" @click="dwClick('confirmed')">
                <div class="dtw-icon" :class="dwIcon('confirmed')">
                  <el-icon v-if="dwPast('confirmed')" :size="16"><Check /></el-icon>
                  <span v-else>5</span>
                </div>
                <div class="dtw-text">
                  <div class="dtw-label">已完成</div>
                  <div class="dtw-tag" :class="dwTagClass('confirmed')" v-text="dwTagText('confirmed')"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <el-form v-if="showReason" :model="statusForm" inline style="margin-top: 12px">
          <el-form-item label="原因">
            <el-input v-model="statusForm.reason" style="width: 240px" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="changing" @click="confirmChange">确认变更</el-button>
            <el-button @click="cancelChange">取消</el-button>
          </el-form-item>
        </el-form>
      </el-card>
      <!-- 管理员删除 -->
      <el-card v-if="authStore.isAdmin" shadow="never" class="info-card" style="margin-top: 16px; border-color: #ff4d4f;">
        <template #header><span style="color: #ff4d4f;">危险操作</span></template>
        <el-button type="danger" :loading="deleting" @click="handleDelete">删除此任务</el-button>
        <span style="color: #999; margin-left: 12px; font-size: 12px;">删除后订单将回退到确认状态，下游任务将被清除</span>
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
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getDesignTask, updateDesignTask, changeDesignTaskStatus, uploadAttachment, deleteAttachment } from '@/api/tasks'
import { getUsers } from '@/api/users'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadRequestOptions } from 'element-plus'
import type { DesignTaskResponse, UserResponse } from '@/types/api'
import { useAiAssistantStore } from '@/stores/aiAssistantStore'
import { useAuthStore } from '@/stores/auth'
import { deleteDesignTask } from '@/api/tasks'

const route = useRoute()
const router = useRouter()
const aiStore = useAiAssistantStore()
const authStore = useAuthStore()
const loading = ref(false)
const updating = ref(false)
const changing = ref(false)
const deleting = ref(false)
const task = ref<DesignTaskResponse | null>(null)
const userOptions = ref<UserResponse[]>([])
const pendingTarget = ref('')
const statusForm = reactive({ to_status: '', reason: '' })
const showReason = computed(() => {
  return !!pendingTarget.value && isReasonRequired(pendingTarget.value)
})
const editForm = reactive({
  assigned_to: '',
  description: '',
  client_comments: '',
  design_file_url: '',
})

const DESIGN_WORKFLOW: Record<string, string[]> = {
  pending: ['designing'],
  designing: ['pending_review', 'pending'],
  pending_review: ['confirmed', 'revision'],
  revision: ['designing', 'pending_review'],
  confirmed: [],
  cancelled: [],
}

const stepOrder = ['pending', 'designing', 'pending_review', 'revision', 'confirmed']
const stepLabels: Record<string, string> = { pending: '待分配', designing: '设计中', pending_review: '待确认', revision: '需修改', confirmed: '已完成' }

function dwPast(s: string) {
  const cur = stepOrder.indexOf(task.value?.status || '')
  const idx = stepOrder.indexOf(s)
  return idx >= 0 && idx < cur
}
function dwCur(s: string) { return s === task.value?.status }
function isReachable(s: string) {
  if (changing.value || !task.value) return false
  return (DESIGN_WORKFLOW[task.value.status] || []).includes(s)
}
function dwCard(s: string) {
  if (dwCur(s)) return 'dw-card-cur'
  if (dwPast(s)) return 'dw-card-done'
  if (isReachable(s)) return 'dw-card-ready'
  return 'dw-card-disabled'
}
function dwIcon(s: string) {
  if (dwCur(s)) return 'dw-icon-cur'
  if (dwPast(s)) return 'dw-icon-done'
  if (isReachable(s)) return 'dw-icon-ready'
  return 'dw-icon-disabled'
}
function dwConn(s: string) {
  return dwPast(s) || dwCur(s) ? 'dw-conn-done' : ''
}
function dwBranchConnClass() {
  return dwPast('pending_review') || dwCur('pending_review') || dwPast('revision') || dwCur('revision') ? 'dw-conn-done' : ''
}
function dwTagClass(s: string) {
  if (dwCur(s)) return 'dw-tag-cur'
  if (dwPast(s)) return 'dw-tag-done'
  if (isReachable(s)) return 'dw-tag-ready'
  return 'dw-tag-future'
}
function dwTagText(s: string) {
  if (dwCur(s)) return '当前'
  if (dwPast(s)) return '已完成'
  if (isReachable(s)) return '可点击'
  return '待进行'
}
function dwClick(s: string) {
  if (!isReachable(s)) return
  if (isReasonRequired(s)) { pendingTarget.value = s; return }
  doChangeStatus(s, '')
}

function isReasonRequired(status: string) {
  return ['pending', 'revision'].includes(status) || status.startsWith('cancel')
}

async function doChangeStatus(to_status: string, reason: string) {
  await ElMessageBox.confirm(`确定将设计任务状态变更为「${stepLabels[to_status] || to_status}」？`, '变更状态', {
    confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning',
  })
  changing.value = true
  try {
    await changeDesignTaskStatus(route.params.id as string, { to_status, reason })
    ElMessage.success('状态已变更')
    pendingTarget.value = ''
    statusForm.reason = ''
    await fetchTask()
    await aiStore.notifyBusinessMutation()
  } catch { /* handled */ } finally { changing.value = false }
}

async function confirmChange() {
  if (!pendingTarget.value) return
  await doChangeStatus(pendingTarget.value, statusForm.reason)
}

function cancelChange() {
  pendingTarget.value = ''
  statusForm.reason = ''
}

function statusLabel(s: string) {
  const map: Record<string, string> = { pending: '待分配', designing: '设计中', pending_review: '待确认', revision: '需修改', confirmed: '已完成', cancelled: '已取消' }
  return map[s] || s
}
function statusColor(s: string) {
  const map: Record<string, string> = { pending: 'info', designing: '', pending_review: 'warning', revision: 'danger', confirmed: 'success', cancelled: 'info' }
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

async function handleDelete() {
  await ElMessageBox.confirm(
    `确定删除设计任务 ${task.value?.design_no || ''}？删除后不可恢复，关联订单将回退到确认状态。`,
    '删除任务', { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'error' }
  )
  deleting.value = true
  try {
    await deleteDesignTask(route.params.id as string)
    ElMessage.success('任务已删除')
    await aiStore.notifyBusinessMutation()
    router.back()
  } catch { /* handled */ } finally { deleting.value = false }
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
/* 设计任务流程图 (分支布局) */
.dtw-bar {
  border: 1px solid var(--ad-border);
  border-radius: 12px;
  padding: 20px 24px;
  background: var(--ad-card);
}
.dtw-flow {
  display: flex;
  align-items: flex-start;
  gap: 0;
  flex-wrap: wrap;
}
.dtw-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
}
.dtw-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 18px;
  border-radius: 10px;
  border: 2px solid transparent;
  transition: all 0.25s ease;
  cursor: default;
  min-width: 80px;
  min-height: 44px;
  box-sizing: border-box;
}
.dtw-icon {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
  transition: all 0.25s ease;
}
.dtw-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.dtw-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--ad-text);
  white-space: nowrap;
  letter-spacing: 0.3px;
}
.dtw-tag { font-size: 10px; font-weight: 500; white-space: nowrap; }
.dtw-tag-cur { color: #409eff; }
.dtw-tag-done { color: #52c41a; }
.dtw-tag-ready { color: #409eff; }
.dtw-tag-future { color: #d9d9d9; }

.dtw-conn {
  display: flex;
  align-items: center;
  padding: 0 2px;
  flex-shrink: 0;
  margin-top: 22px;
}
.dtw-line { width: 32px; height: 2px; background: #e8e8e8; border-radius: 2px; transition: all 0.3s ease; }
.dtw-conn-done .dtw-line { background: linear-gradient(to right, #52c41a, #73d13d); height: 3px; }
.dtw-point { font-size: 11px; color: #d9d9d9; margin-left: -2px; transition: all 0.3s ease; }
.dtw-conn-done .dtw-point { color: #73d13d; }

/* 并列分支 */
.dtw-branch {
  display: flex;
  align-items: center;
  gap: 8px;
}
.dtw-branch-sep {
  width: 8px;
}

/* 卡片状态 */
.dw-card-cur {
  border-color: #409eff;
  background: linear-gradient(135deg, rgba(64,158,255,0.07), rgba(64,158,255,0.03));
  box-shadow: 0 0 0 4px rgba(64,158,255,0.08);
  cursor: pointer;
}
.dw-card-cur:hover {
  background: linear-gradient(135deg, rgba(64,158,255,0.12), rgba(64,158,255,0.06));
  box-shadow: 0 2px 12px rgba(64,158,255,0.15);
}
.dw-card-cur .dtw-label { color: #409eff; }

.dw-icon-cur {
  background: linear-gradient(135deg, #409eff, #66b1ff);
  color: #fff;
  box-shadow: 0 2px 8px rgba(64,158,255,0.35);
}

.dw-card-done { border-color: transparent; }
.dw-card-done .dtw-label { color: #52c41a; }
.dw-icon-done {
  background: linear-gradient(135deg, #52c41a, #73d13d);
  color: #fff;
  box-shadow: 0 2px 6px rgba(82,196,26,0.3);
}

.dw-card-ready {
  border-color: #409eff;
  border-style: dashed;
  background: rgba(64,158,255,0.03);
  cursor: pointer;
}
.dw-card-ready:hover {
  background: rgba(64,158,255,0.08);
  box-shadow: 0 2px 10px rgba(64,158,255,0.1);
  transform: translateX(3px);
}
.dw-card-ready:active { transform: translateX(0); }
.dw-card-ready .dtw-label { color: #409eff; }

.dw-icon-ready {
  background: #f0f5ff;
  color: #409eff;
  border: 2px solid #409eff;
  cursor: pointer;
}
.dw-icon-ready:hover {
  background: #e6f0ff;
  box-shadow: 0 0 0 4px rgba(64,158,255,0.15);
}

.dw-card-disabled { border-color: #f0f0f0; background: #fafafa; }
.dw-card-disabled .dtw-label { color: #d9d9d9; }
.dw-icon-disabled {
  background: #f5f5f5;
  color: #d9d9d9;
  border: 2px solid #e8e8e8;
}

:root[data-theme*="dark"] .dw-icon-disabled {
  background: #262626; color: #434343; border-color: #434343;
}
:root[data-theme*="dark"] .dw-icon-ready { background: rgba(64,158,255,0.12); }
:root[data-theme*="dark"] .dw-icon-ready:hover { background: rgba(64,158,255,0.2); }
:root[data-theme*="dark"] .dw-card-disabled { border-color: #262626; background: #1a1a1a; }
:root[data-theme*="dark"] .dw-card-disabled .dtw-label { color: #434343; }
:root[data-theme*="dark"] .dw-card-disabled .dw-tag-future { color: #434343; }
:root[data-theme*="dark"] .dw-card-cur { background: rgba(64,158,255,0.1); box-shadow: 0 0 0 4px rgba(64,158,255,0.12); }
:root[data-theme*="dark"] .dw-card-ready { background: rgba(64,158,255,0.06); }
:root[data-theme*="dark"] .dw-card-ready:hover { background: rgba(64,158,255,0.15); }
:root[data-theme*="dark"] .dtw-line { background: #434343; }
:root[data-theme*="dark"] .dtw-point { color: #595959; }

@media (max-width: 800px) {
  .dtw-bar { padding: 14px; }
  .dtw-card { padding: 8px 12px; min-width: 56px; min-height: 38px; gap: 6px; }
  .dtw-line { width: 16px; }
  .dtw-tag { display: none; }
  .dtw-branch { flex-wrap: wrap; }
}

</style>
