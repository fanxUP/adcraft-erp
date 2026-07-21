<template>
  <div class="page">
    <div class="page-header">
      <h2>用户管理</h2>
      <el-button type="danger" @click="openCreate">新增用户</el-button>
    </div>

    <el-table :data="list" v-loading="loading" stripe>
      <el-table-column prop="username" label="用户名" width="140" />
      <el-table-column prop="real_name" label="姓名" width="120" />
      <el-table-column prop="phone" label="手机号" width="140" />
      <el-table-column prop="email" label="邮箱" min-width="180" show-overflow-tooltip />
      <el-table-column label="角色" width="200">
        <template #default="{ row }">
          <el-tag v-for="r in row.roles" :key="r" size="small" style="margin-right: 4px">{{ roleLabel(r) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">{{ row.is_active ? '启用' : '停用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" size="small" @click="openEdit(row)">编辑</el-button>
          <el-button text type="warning" size="small" @click="handleResetPwd(row)">重置密码</el-button>
          <el-button v-if="row.username !== 'admin'" text type="danger" size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :page-sizes="[10, 20, 50]"
      :total="total"
      layout="total, sizes, prev, pager, next"
      style="margin-top: 16px; justify-content: flex-end"
      @change="fetchData"
    />

    <!-- Create/Edit Dialog -->
    <el-dialog v-model="showDialog" :title="isEditing ? '编辑用户' : '新增用户'" width="480px" :close-on-click-modal="false">
      <el-form :model="form" label-width="80px">
        <el-form-item label="用户名" required>
          <el-input v-model="form.username" :disabled="isEditing" placeholder="登录用户名" />
        </el-form-item>
        <el-form-item v-if="!isEditing" label="密码" required>
          <el-input v-model="form.password" type="password" show-password placeholder="初始密码" />
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
          <el-select v-model="form.role_ids" multiple style="width: 100%" placeholder="选择角色">
            <el-option v-for="r in roleOptions" :key="r.id" :label="roleLabel(r.name)" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.is_active" active-text="启用" inactive-text="停用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="danger" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getUsers, createUser, updateUser, deleteUser, resetPassword } from '@/api/users'
import { getRoles, type RoleItem } from '@/api/admin'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UserResponse } from '@/types/api'

const ROLE_MAP: Record<string, string> = {
  admin: '管理员', sales: '销售', designer: '设计师',
  production: '生产', installer: '安装', finance: '财务',
}
function roleLabel(name: string) { return ROLE_MAP[name] || name }

const loading = ref(false)
const saving = ref(false)
const list = ref<UserResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const showDialog = ref(false)
const isEditing = ref(false)
const editingId = ref('')
const roleOptions = ref<RoleItem[]>([])

const form = reactive({
  username: '', password: '', real_name: '', phone: '', email: '',
  role_ids: [] as string[], is_active: true,
})

function resetForm() {
  Object.assign(form, { username: '', password: '', real_name: '', phone: '', email: '', role_ids: [], is_active: true })
  isEditing.value = false
  editingId.value = ''
}

async function fetchData() {
  loading.value = true
  try {
    const data = await getUsers({ page: page.value, page_size: pageSize.value })
    list.value = data.items
    total.value = data.total
  } finally { loading.value = false }
}

async function loadRoles() {
  try { roleOptions.value = await getRoles() } catch { /* ignore */ }
}

function openCreate() {
  resetForm()
  showDialog.value = true
}

function openEdit(row: UserResponse) {
  isEditing.value = true
  editingId.value = row.id
  form.username = row.username
  form.real_name = row.real_name || ''
  form.phone = row.phone || ''
  form.email = row.email || ''
  form.is_active = row.is_active
  // Map role names to role IDs
  form.role_ids = roleOptions.value.filter(r => row.roles.includes(r.name)).map(r => r.id)
  showDialog.value = true
}

async function handleSave() {
  saving.value = true
  try {
    if (isEditing.value) {
      const payload: Record<string, unknown> = {}
      payload.real_name = form.real_name || null
      payload.phone = form.phone || null
      payload.email = form.email || null
      payload.is_active = form.is_active
      payload.role_ids = form.role_ids
      await updateUser(editingId.value, payload)
      ElMessage.success('用户已更新')
    } else {
      if (!form.username || !form.password) {
        ElMessage.warning('用户名和密码为必填')
        return
      }
      await createUser({
        username: form.username, password: form.password,
        real_name: form.real_name || null, phone: form.phone || null,
        email: form.email || null, role_ids: form.role_ids,
      } as unknown)
      ElMessage.success('用户已创建')
    }
    showDialog.value = false
    resetForm()
    fetchData()
  } catch { /* handled by interceptor */ } finally { saving.value = false }
}

async function handleResetPwd(row: UserResponse) {
  try {
    const { value } = await ElMessageBox.prompt('请输入新密码', `重置「${row.real_name || row.username}」的密码`, {
      confirmButtonText: '确定', cancelButtonText: '取消', inputPattern: /.{6,}/, inputErrorMessage: '密码至少6位',
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
.page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; color: var(--ad-text); }
</style>
