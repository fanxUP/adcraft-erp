<template>
  <div class="page">
    <h2 style="margin-bottom: 16px; color: var(--ad-text)">备份管理</h2>

    <!-- Stats -->
    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="8">
        <el-card shadow="never" class="stat-card">
          <div class="stat-value">{{ stats.total }}</div>
          <div class="stat-label">备份总数</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="never" class="stat-card">
          <div class="stat-value">{{ stats.totalSizeDisplay }}</div>
          <div class="stat-label">总大小</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="never" class="stat-card">
          <div class="stat-value">{{ stats.lastBackup }}</div>
          <div class="stat-label">最近备份</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Actions -->
    <div style="margin-bottom: 16px; display: flex; gap: 10px">
      <el-button type="danger" @click="handleCreate" :loading="creating" :disabled="creating">
        <el-icon><Plus /></el-icon> 创建备份
      </el-button>
      <el-button @click="triggerImport" :loading="importing">
        <el-icon><Upload /></el-icon> 导入备份
      </el-button>
      <input ref="fileInputRef" type="file" accept=".tar.gz" style="display: none" @change="handleFileChange" />
      <el-button @click="fetchList" :loading="loading">刷新</el-button>
    </div>

    <!-- Table -->
    <el-card shadow="never">
      <el-table :data="backups" v-loading="loading" stripe style="width: 100%" empty-text="暂无备份文件">
        <el-table-column prop="filename" label="文件名" min-width="280" />
        <el-table-column prop="size_display" label="大小" width="100" align="center" />
        <el-table-column label="创建时间" width="180" align="center">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" align="center" fixed="right">
          <template #default="{ row }">
            <el-button
              type="primary"
              size="small"
              @click="handleExport(row as BackupItem)"
              :disabled="exporting === row.filename"
            >
              导出
            </el-button>
            <el-button
              type="warning"
              size="small"
              @click="handleRestore(row as BackupItem)"
              :disabled="restoring === row.filename"
            >
              恢复
            </el-button>
            <el-button
              type="danger"
              size="small"
              @click="handleDelete(row as BackupItem)"
              :disabled="deleting === row.filename"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Create result dialog -->
    <el-dialog v-model="resultVisible" title="备份结果" width="500px">
      <div v-if="result">
        <p><strong>状态：</strong>✅ {{ result.message }}</p>
        <p v-if="result.backup">
          <strong>文件：</strong>{{ result.backup.filename }}<br />
          <strong>大小：</strong>{{ result.backup.size_display }}<br />
          <strong>时间：</strong>{{ formatTime(result.backup.created_at) }}
        </p>
        <p v-if="result.output" style="margin-top: 8px">
          <strong>输出：</strong>
        </p>
        <pre v-if="result.output" class="output-block">{{ result.output }}</pre>
      </div>
    </el-dialog>

    <!-- Restore confirm dialog -->
    <el-dialog v-model="restoreConfirmVisible" title="确认恢复" width="420px">
      <p style="color: #e6a23c; font-size: 15px; margin-bottom: 12px">
        ⚠️ 恢复操作将<strong>覆盖</strong>当前数据库和上传文件！
      </p>
      <p style="color: var(--ad-text); margin-bottom: 8px">备份文件：{{ toRestore?.filename }}</p>
      <p style="color: var(--ad-text-secondary); font-size: 13px">创建时间：{{ formatTime(toRestore?.created_at) }}</p>
      <template #footer>
        <el-button @click="restoreConfirmVisible = false">取消</el-button>
        <el-button type="danger" @click="confirmRestore" :loading="!!restoring">
          确认恢复
        </el-button>
      </template>
    </el-dialog>

    <!-- Restore result dialog -->
    <el-dialog v-model="restoreResultVisible" :title="restoreSuccess ? '恢复成功' : '恢复失败'" width="420px">
      <div style="text-align: center; padding: 10px 0">
        <div v-if="restoreSuccess" style="font-size: 48px; margin-bottom: 16px">✅</div>
        <div v-else style="font-size: 48px; margin-bottom: 16px">❌</div>
        <p style="font-size: 15px; color: var(--ad-text); margin-bottom: 12px">{{ restoreMessage }}</p>
        <p v-if="restoreSuccess" style="color: #e6a23c; font-size: 13px">
          点击"重新登录"将跳转到登录页面
        </p>
      </div>
      <template #footer>
        <el-button v-if="!restoreSuccess" @click="restoreResultVisible = false">关闭</el-button>
        <el-button v-if="restoreSuccess" type="primary" @click="handleRelogin">
          重新登录
        </el-button>
      </template>
    </el-dialog>

    <!-- Delete confirm dialog -->
    <el-dialog v-model="deleteConfirmVisible" title="确认删除" width="400px">
      <p style="color: var(--ad-text)">确定删除备份文件 <strong>{{ toDelete?.filename }}</strong> 吗？</p>
      <p style="color: #999; font-size: 13px; margin-top: 4px">此操作不可撤销。</p>
      <template #footer>
        <el-button @click="deleteConfirmVisible = false">取消</el-button>
        <el-button type="danger" @click="confirmDelete" :loading="!!deleting">
          删除
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { createBackup, listBackups, restoreBackup, deleteBackup, exportBackup, importBackup } from '@/api/backup'
import type { BackupItem, CreateBackupResponse } from '@/types/api'
import { ElMessage } from 'element-plus'
import { getErrorMessage } from '@/utils/error'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

const loading = ref(false)
const creating = ref(false)
const restoring = ref('')
const deleting = ref('')
const exporting = ref('')
const importing = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)
const backups = ref<BackupItem[]>([])

const stats = reactive({
  total: 0,
  totalSizeDisplay: '0 B',
  lastBackup: '-',
})

const resultVisible = ref(false)
const result = ref<CreateBackupResponse | null>(null)

const restoreConfirmVisible = ref(false)
const toRestore = ref<BackupItem | null>(null)

const restoreResultVisible = ref(false)
const restoreSuccess = ref(false)
const restoreMessage = ref('')

const deleteConfirmVisible = ref(false)
const toDelete = ref<BackupItem | null>(null)

function formatTime(ts: string | undefined): string {
  if (!ts) return '-'
  return ts.replace('T', ' ').slice(0, 19)
}

async function fetchList() {
  loading.value = true
  try {
    const data = await listBackups()
    backups.value = data.backups || []
    stats.total = data.total || 0
    stats.totalSizeDisplay = data.total_size_display || '0 B'
    stats.lastBackup = backups.value.length > 0
      ? formatTime(backups.value[0].created_at)
      : '-'
  } catch {
    ElMessage.error('获取备份列表失败')
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  creating.value = true
  try {
    const data = await createBackup()
    result.value = data
    resultVisible.value = true
    await fetchList()
  } catch (e: unknown) {
    ElMessage.error(getErrorMessage(e, '创建备份失败'))
  } finally {
    creating.value = false
  }
}

function handleRestore(row: BackupItem) {
  toRestore.value = row
  restoreConfirmVisible.value = true
}

async function confirmRestore() {
  if (!toRestore.value) return
  const filename = toRestore.value.filename
  restoring.value = filename
  try {
    await restoreBackup(filename)
    restoreSuccess.value = true
    restoreMessage.value = '数据恢复成功！由于数据库已被替换，您需要重新登录。'
    restoreConfirmVisible.value = false
    restoreResultVisible.value = true
  } catch (e: unknown) {
    restoreSuccess.value = false
    restoreMessage.value = getErrorMessage(e, '恢复失败')
    restoreConfirmVisible.value = false
    restoreResultVisible.value = true
  } finally {
    restoring.value = ''
    toRestore.value = null
  }
}

function handleRelogin() {
  restoreResultVisible.value = false
  authStore.logout()
}

function handleDelete(row: BackupItem) {
  toDelete.value = row
  deleteConfirmVisible.value = true
}

async function confirmDelete() {
  if (!toDelete.value) return
  const filename = toDelete.value.filename
  deleting.value = filename
  try {
    await deleteBackup(filename)
    ElMessage.success('已删除')
    deleteConfirmVisible.value = false
    await fetchList()
  } catch (e: unknown) {
    ElMessage.error(getErrorMessage(e, '删除失败'))
  } finally {
    deleting.value = ''
    toDelete.value = null
  }
}

async function handleExport(row: BackupItem) {
  exporting.value = row.filename
  try {
    await exportBackup(row.filename)
    ElMessage.success('导出成功')
  } catch (e: unknown) {
    ElMessage.error(getErrorMessage(e, '导出失败'))
  } finally {
    exporting.value = ''
  }
}

function triggerImport() {
  fileInputRef.value?.click()
}

async function handleFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  // Reset input so the same file can be selected again
  input.value = ''

  importing.value = true
  try {
    const data = await importBackup(file)
    ElMessage.success(data.message || '导入成功')
    await fetchList()
  } catch (e: unknown) {
    ElMessage.error(getErrorMessage(e, '导入失败'))
  } finally {
    importing.value = false
  }
}

onMounted(fetchList)
</script>

<style scoped>
.stat-card {
  background: var(--ad-card);
  border: 1px solid var(--ad-border);
  text-align: center;
}
.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--ad-red, #e63946);
  margin-bottom: 4px;
}
.stat-label {
  font-size: 13px;
  color: var(--ad-text-secondary, #a0a0b0);
}
.output-block {
  background: #0f0f1a;
  border: 1px solid var(--ad-border);
  border-radius: 6px;
  padding: 10px;
  font-size: 12px;
  color: #ccc;
  max-height: 200px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
