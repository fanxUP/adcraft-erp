<template>
  <AppPage>
    <PageHeader title="用户管理" description="员工账号由员工档案自动生成；此处维护角色、启停状态和密码操作。" />

    <el-alert v-if="rolesError" title="角色加载失败，暂时无法编辑账号，避免误清空原有授权。" type="error" :closable="false" show-icon>
      <el-button text type="primary" :loading="rolesLoading" @click="loadRoles">重新加载角色</el-button>
    </el-alert>

    <DataTableShell :state="tableState" aria-label="用户列表">
      <template #error><StatePanel state="error" action-label="重试" @action="fetchData" /></template>
      <el-table :data="list" v-loading="loading" stripe>
      <el-table-column label="工号" width="160">
        <template #default="{ row }">
          <span>{{ row.username }}</span>
          <el-tag v-if="row.username === 'admin' && !row.linked_employee" size="small" type="info" style="margin-left: 6px">系统账号</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="real_name" label="姓名" width="120" />
      <el-table-column label="关联员工" width="210">
        <template #default="{ row }">
          <template v-if="row.linked_employee">
            <div>{{ row.linked_employee.name }}（{{ row.linked_employee.employee_no }}）</div>
            <span class="linked-department">{{ departmentLabel(row.linked_employee.department) }}</span>
          </template>
          <el-tag v-else type="warning" size="small">未关联员工</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="phone" label="手机号" width="130" />
      <el-table-column prop="email" label="邮箱" min-width="180" show-overflow-tooltip />
      <el-table-column label="角色" width="200">
        <template #default="{ row }">
          <el-tag v-for="r in row.roles" :key="r" size="small" style="margin-right: 4px">{{ roleLabel(r) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">{{ row.is_active ? '启用' : '停用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="登录提示" width="120">
        <template #default="{ row }">
          <el-tag v-if="row.must_change_password" type="warning" size="small">首次登录改密</el-tag>
          <span v-else class="muted">正常</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" size="small" :disabled="!rolesReady || saving" @click="openEdit(row)">编辑</el-button>
          <el-button text type="warning" size="small" @click="handleResetPwd(row)">重置密码</el-button>
          <el-button v-if="row.username !== 'admin' && !row.linked_employee" text type="danger" size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
      </el-table>

      <template #footer>
        <el-pagination v-if="total > 0" v-model:current-page="page" v-model:page-size="pageSize" :page-sizes="[10, 20, 50]" :total="total" layout="total, sizes, prev, pager, next" @change="fetchData" />
      </template>
    </DataTableShell>

    <el-dialog v-model="showDialog" title="编辑用户账号" width="min(480px, 94vw)" :close-on-click-modal="false" :close-on-press-escape="!saving" :show-close="!saving">
      <el-form :model="form" label-width="80px" :disabled="saving">
        <el-form-item label="工号" required>
          <el-input v-model="form.username" disabled placeholder="员工工号" />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="form.real_name" placeholder="真实姓名" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="form.phone" placeholder="手机号" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="form.email" placeholder="邮箱" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role_ids" multiple filterable :disabled="!rolesReady" style="width: 100%" placeholder="选择角色">
            <el-option v-for="r in roleOptions" :key="r.id" :label="roleLabel(r.name)" :value="r.id" />
          </el-select>
          <div class="role-hint">多个角色的权限合并生效，保存时会检查最终权限组合。</div>
          <div v-if="!form.role_ids.length" class="role-hint">未分配角色，该账号将没有业务操作权限。</div>
          <div v-for="role in assignedRoles" :key="role.id" class="role-hint">{{ roleLabel(role.name) }}：{{ role.description || `${role.permissions.length} 项权限` }}</div>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.is_active" active-text="启用" inactive-text="停用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button :disabled="saving" @click="showDialog = false">取消</el-button>
        <el-button :loading="saving" :disabled="!rolesReady" @click="handleSave" type="primary">保存</el-button>
      </template>
    </el-dialog>
  </AppPage>
</template>

<script setup lang="ts">
import { passwordError } from '@/utils/password'
import { ref, reactive, computed, onMounted } from 'vue'
import { getUsers, updateUser, deleteUser, resetPassword } from '@/api/users'
import { getRoles, type RoleItem } from '@/api/admin'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UserResponse } from '@/types/api'
import { AppPage, DataTableShell, PageHeader, StatePanel } from '@/components/ui'
import { roleLabel, resolveUserRoleIds } from '@/utils/permissionEditor'
import { getErrorMessage } from '@/utils/error'

const DEPARTMENT_MAP: Record<string, string> = {
  design: '设计部', production: '生产部', installation: '安装部',
  sales: '销售部', finance: '财务部', admin: '行政部',
}
function departmentLabel(value?: string | null) { return value ? (DEPARTMENT_MAP[value] || value) : '未设置部门' }

const loading = ref(false)
const loadError = ref(false)
const saving = ref(false)
const list = ref<UserResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const showDialog = ref(false)
const isEditing = ref(false)
const editingId = ref('')
const roleOptions = ref<RoleItem[]>([])
const rolesLoading = ref(true)
const rolesError = ref(false)
const rolesReady = computed(() => !rolesLoading.value && !rolesError.value)
const assignedRoles = computed(() => roleOptions.value.filter(role => form.role_ids.includes(role.id)))

const tableState = computed(() => loadError.value ? 'error' as const : loading.value ? 'loading' as const : list.value.length ? 'ready' as const : 'empty' as const)

const form = reactive({
  username: '', real_name: '', phone: '', email: '',
  role_ids: [] as string[], is_active: true,
})

function resetForm() {
  Object.assign(form, { username: '', real_name: '', phone: '', email: '', role_ids: [], is_active: true })
  isEditing.value = false
  editingId.value = ''
}

async function fetchData() {
  loading.value = true
  loadError.value = false
  try {
    const data = await getUsers({ page: page.value, page_size: pageSize.value })
    list.value = data.items
    total.value = data.total
  } catch { loadError.value = true } finally { loading.value = false }
}

async function loadRoles() {
  rolesLoading.value = true
  rolesError.value = false
  try { roleOptions.value = await getRoles() }
  catch { rolesError.value = true }
  finally { rolesLoading.value = false }
}

function openEdit(row: UserResponse) {
  if (!rolesReady.value || saving.value) return
  let roleIds: string[]
  try { roleIds = resolveUserRoleIds(roleOptions.value, row.roles) }
  catch (error) {
    rolesError.value = true
    ElMessage.error(getErrorMessage(error))
    return
  }
  isEditing.value = true
  editingId.value = row.id
  form.username = row.username
  form.real_name = row.real_name || ''
  form.phone = row.phone || ''
  form.email = row.email || ''
  form.is_active = row.is_active
  form.role_ids = roleIds
  showDialog.value = true
}

async function handleSave() {
  if (saving.value || !rolesReady.value || !editingId.value) return
  saving.value = true
  try {
    await updateUser(editingId.value, {
      real_name: form.real_name || null,
      phone: form.phone || null,
      email: form.email || null,
      is_active: form.is_active,
      role_ids: form.role_ids,
    })
    ElMessage.success('用户已更新')
    showDialog.value = false
    resetForm()
    fetchData()
  } catch (error) { ElMessage.error(getErrorMessage(error)) } finally { saving.value = false }
}

async function handleResetPwd(row: UserResponse) {
  try {
    const { value } = await ElMessageBox.prompt('请输入新密码', `重置「${row.real_name || row.username}」的密码`, {
      confirmButtonText: '确定', cancelButtonText: '取消', inputValidator: (value: string) => passwordError(value) || true,
    })
    if (value) {
      await resetPassword(row.id, value)
      ElMessage.success('密码已重置')
    }
  } catch { /* cancelled */ }
}

async function handleDelete(row: UserResponse) {
  try {
    await ElMessageBox.confirm(`确定删除用户「${row.real_name || row.username}」吗？`, '确认删除', {
      confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning',
    })
    await deleteUser(row.id)
    ElMessage.success('已删除')
    fetchData()
  } catch { /* cancelled */ }
}

onMounted(() => { fetchData(); loadRoles() })
</script>

<style scoped>
.linked-department { color: var(--el-text-color-secondary); font-size: 12px; }
.role-hint { width: 100%; color: var(--el-text-color-secondary); font-size: 13px; line-height: 1.7; }
</style>
