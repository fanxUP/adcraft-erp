<template>
  <div class="page">
    <div class="page-header">
      <h2>角色权限管理</h2>
      <el-button type="danger" @click="openCreate">新增角色</el-button>
    </div>

    <el-row :gutter="20">
      <!-- Role list -->
      <el-col :span="10">
        <el-card shadow="never">
          <el-table :data="roles" v-loading="loading" stripe highlight-current-row @current-change="onRoleSelect">
            <el-table-column prop="name" label="角色" width="120">
              <template #default="{ row }">{{ roleLabel(row.name) }}</template>
            </el-table-column>
            <el-table-column prop="description" label="说明" min-width="140" show-overflow-tooltip />
            <el-table-column label="权限数" width="80" align="center">
              <template #default="{ row }">{{ row.permissions.length }}</template>
            </el-table-column>
            <el-table-column label="操作" width="130" fixed="right">
              <template #default="{ row }">
                <el-button text type="primary" size="small" @click.stop="openEdit(row)">编辑</el-button>
                <el-button v-if="row.name !== 'admin'" text type="danger" size="small" @click.stop="handleDelete(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- Permission assignment -->
      <el-col :span="14">
        <el-card shadow="never">
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span>权限配置 — {{ selectedRole ? roleLabel(selectedRole.name) : '请选择角色' }}</span>
              <el-button v-if="selectedRole" type="danger" size="small" :loading="savingPerms" @click="handleSavePerms">保存权限</el-button>
            </div>
          </template>
          <div v-if="!selectedRole" style="color: #909399; text-align: center; padding: 40px 0">
            ← 请先在左侧选择一个角色
          </div>
          <div v-else>
            <el-checkbox v-model="checkAll" :indeterminate="isIndeterminate" @change="handleCheckAll" style="margin-bottom: 12px">
              全选
            </el-checkbox>
            <el-divider style="margin: 8px 0" />
            <div v-for="(perms, group) in groupedPerms" :key="group" style="margin-bottom: 16px">
              <div style="font-weight: bold; margin-bottom: 8px; color: var(--ad-text)">{{ groupLabels[group as string] || group }}</div>
              <el-checkbox-group v-model="checkedPermIds">
                <el-checkbox v-for="p in perms" :key="p.id" :value="p.id" style="margin-bottom: 4px">
                  {{ p.name }} <span style="color: #909399; font-size: 12px">({{ p.code }})</span>
                </el-checkbox>
              </el-checkbox-group>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Create/Edit Role Dialog -->
    <el-dialog v-model="showDialog" :title="isEditing ? '编辑角色' : '新增角色'" width="400px" :close-on-click-modal="false">
      <el-form :model="form" label-width="80px">
        <el-form-item label="角色名" required>
          <el-input v-model="form.name" placeholder="英文标识，如 designer" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.description" placeholder="角色描述" />
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
import { ref, reactive, computed, onMounted } from 'vue'
import { getRoles, createRole, updateRole, deleteRole, setRolePermissions, getPermissions, type RoleItem, type PermissionItem } from '@/api/admin'
import { ElMessage, ElMessageBox } from 'element-plus'

const ROLE_MAP: Record<string, string> = {
  admin: '管理员', sales: '销售', designer: '设计师',
  production: '生产', installer: '安装', finance: '财务',
}
function roleLabel(name: string) { return ROLE_MAP[name] || name }

const groupLabels: Record<string, string> = {
  system: '系统管理', user: '用户管理', customer: '客户管理',
  product: '产品管理', material: '材质管理', process: '工艺管理',
  quote: '报价管理', order: '订单管理', design_task: '设计任务',
  production_task: '生产任务', installation_task: '安装任务',
  payment: '收款管理', statement: '对账单', expense: '支出管理',
  inventory: '库存管理', outsource: '外协管理', report: '报表',
  backup: '备份管理', ai_quote: 'AI报价', ai_anomaly: 'AI异常',
  ai_knowledge: 'AI知识库', ai_report: 'AI报告',
}

const loading = ref(false)
const saving = ref(false)
const savingPerms = ref(false)
const roles = ref<RoleItem[]>([])
const allPerms = ref<PermissionItem[]>([])
const selectedRole = ref<RoleItem | null>(null)
const checkedPermIds = ref<string[]>([])
const showDialog = ref(false)
const isEditing = ref(false)
const editingId = ref('')
const form = reactive({ name: '', description: '' })

const groupedPerms = computed(() => {
  const groups: Record<string, PermissionItem[]> = {}
  for (const p of allPerms.value) {
    const group = p.code.split(':')[0]
    if (!groups[group]) groups[group] = []
    groups[group].push(p)
  }
  return groups
})

const checkAll = computed(() => checkedPermIds.value.length === allPerms.value.length && allPerms.value.length > 0)
const isIndeterminate = computed(() => checkedPermIds.value.length > 0 && checkedPermIds.value.length < allPerms.value.length)

function handleCheckAll(val: boolean) {
  checkedPermIds.value = val ? allPerms.value.map(p => p.id) : []
}

async function fetchRoles() {
  loading.value = true
  try { roles.value = await getRoles() } finally { loading.value = false }
}

async function fetchPerms() {
  try { allPerms.value = await getPermissions() } catch { /* ignore */ }
}

function onRoleSelect(role: RoleItem | null) {
  selectedRole.value = role
  if (role) {
    checkedPermIds.value = role.permissions.map(p => p.id)
  } else {
    checkedPermIds.value = []
  }
}

function openCreate() {
  form.name = ''; form.description = ''
  isEditing.value = false; editingId.value = ''
  showDialog.value = true
}

function openEdit(role: RoleItem) {
  form.name = role.name; form.description = role.description || ''
  isEditing.value = true; editingId.value = role.id
  showDialog.value = true
}

async function handleSave() {
  saving.value = true
  try {
    if (isEditing.value) {
      await updateRole(editingId.value, { name: form.name, description: form.description })
      ElMessage.success('角色已更新')
    } else {
      if (!form.name) { ElMessage.warning('角色名不能为空'); return }
      await createRole({ name: form.name, description: form.description })
      ElMessage.success('角色已创建')
    }
    showDialog.value = false
    fetchRoles()
  } catch { /* handled */ } finally { saving.value = false }
}

async function handleDelete(role: RoleItem) {
  try {
    await ElMessageBox.confirm(`确定删除角色「${roleLabel(role.name)}」吗？`, '确认删除', {
      confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning',
    })
    await deleteRole(role.id)
    ElMessage.success('已删除')
    if (selectedRole.value?.id === role.id) selectedRole.value = null
    fetchRoles()
  } catch { /* cancelled */ }
}

async function handleSavePerms() {
  if (!selectedRole.value) return
  savingPerms.value = true
  try {
    const updated = await setRolePermissions(selectedRole.value.id, checkedPermIds.value)
    // Update local data
    const idx = roles.value.findIndex(r => r.id === selectedRole.value!.id)
    if (idx >= 0) roles.value[idx].permissions = updated.permissions
    selectedRole.value.permissions = updated.permissions
    ElMessage.success('权限已保存')
  } catch { /* handled */ } finally { savingPerms.value = false }
}

onMounted(() => { fetchRoles(); fetchPerms() })
</script>

<style scoped>
.page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; color: var(--ad-text); }
</style>
