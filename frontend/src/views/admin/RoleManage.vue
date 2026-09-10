<template>
  <AppPage>
    <template #header><PageHeader title="角色权限管理" description="维护角色与权限配置，角色列表和权限面板保持同一页面层级。">
      <template #actions><el-button @click="openCreate" type="primary">新增角色</el-button></template>
    </PageHeader></template>

    <el-row :gutter="20">
      <!-- Role list -->
      <el-col :span="10">
        <DataTableShell :state="roleTableState" aria-label="角色列表">
          <el-table :data="roles" stripe highlight-current-row @current-change="onRoleSelect">
            <el-table-column prop="name" label="角色" width="120">
              <template #default="{ row }">{{ roleLabel(row.name) }}</template>
            </el-table-column>
            <el-table-column prop="description" label="说明" min-width="180" show-overflow-tooltip />
            <el-table-column label="权限数" width="80" align="center">
              <template #default="{ row }">{{ row.permissions.length }}</template>
            </el-table-column>
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <el-button text type="primary" size="small" @click.stop="openEdit(row)">编辑</el-button>
                <el-button v-if="row.name !== 'admin'" text type="danger" size="small" @click.stop="handleDelete(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <template #error><StatePanel state="error" action-label="重新加载" @action="fetchRoles" /></template>
        </DataTableShell>
      </el-col>

      <!-- Permission assignment -->
      <el-col :span="14">
        <el-card shadow="never">
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span>权限配置 — {{ selectedRole ? roleLabel(selectedRole.name) : '请选择角色' }}</span>
              <el-button v-if="selectedRole" size="small" :loading="savingPerms" @click="handleSavePerms" type="primary">保存权限</el-button>
            </div>
          </template>
          <div v-if="!selectedRole" style="color: var(--ad-text-secondary); text-align: center; padding: 40px 0">
            ← 请先在左侧选择一个角色
          </div>
          <div v-else>
            <el-alert
              v-if="selectedRoleIsExecution"
              title="设计、制作、安装角色不能配置报价、合同、财务或价格权限"
              type="info"
              :closable="false"
              show-icon
              style="margin-bottom: 12px"
            />
            <el-checkbox :model-value="checkAll" :indeterminate="isIndeterminate" @change="handleCheckAll" style="margin-bottom: 12px">
              全选
            </el-checkbox>
            <el-divider style="margin: 8px 0" />
            <div v-for="(perms, group) in groupedPerms" :key="group" style="margin-bottom: 16px">
              <div style="font-weight: bold; margin-bottom: 8px; color: var(--ad-text)">{{ groupLabels[group as string] || group }}</div>
              <el-checkbox-group v-model="checkedPermIds">
                <el-checkbox
                  v-for="p in perms"
                  :key="p.id"
                  :value="p.id"
                  :disabled="permissionDisabled(p)"
                  style="margin-bottom: 4px"
                >
                  {{ p.name }}
                  <span style="color: var(--ad-text-secondary); font-size: 12px">({{ p.code }})</span>
                  <el-tag v-if="isSensitivePermission(p.code)" size="small" type="warning" effect="plain" style="margin-left: 6px">
                    {{ selectedRoleIsExecution ? '执行角色禁用' : '敏感数据' }}
                  </el-tag>
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
        <el-button :loading="saving" @click="handleSave" type="primary">保存</el-button>
      </template>
    </el-dialog>
  </AppPage>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { getRoles, createRole, updateRole, deleteRole, setRolePermissions, getPermissions, type RoleItem, type PermissionItem } from '@/api/admin'
import { ElMessage, ElMessageBox } from 'element-plus'
import { AppPage, DataTableShell, PageHeader, StatePanel } from '@/components/ui'
import { getErrorMessage } from '@/utils/error'

const ROLE_MAP: Record<string, string> = {
  admin: '管理员', sales: '销售', designer: '设计师',
  production: '生产', installer: '安装', finance: '财务',
}
function roleLabel(name: string) { return ROLE_MAP[name] || name }

const groupLabels: Record<string, string> = {
  system: '系统管理', user: '用户管理', customer: '客户管理',
  product: '产品/材质/工艺', material: '产品/材质/工艺（兼容权限）', process: '产品/材质/工艺（兼容权限）',
  quote: '报价管理', order: '订单管理', design_task: '设计任务',
  production_task: '生产任务', installation_task: '安装任务',
  contract: '合同管理', cdr_quote: '智能报价', cdr_rule_set: '智能报价规则',
  cdr_customer_agreement: '客户协议价',
  payment: '收款管理', statement: '对账单', expense: '支出管理',
  inventory: '库存管理', outsource: '外协管理', report: '报表',
  backup: '备份管理', ai_quote: 'AI报价', ai_anomaly: 'AI异常',
  ai_knowledge: 'AI知识库', ai_report: 'AI报告',
}

const EXECUTION_ROLE_NAMES = new Set(['designer', 'production', 'installer'])
const EXECUTION_PERMISSION_CODES = new Set([
  'design_task:read', 'design_task:create', 'design_task:update',
  'design_task:change_status', 'design_task:delete',
  'production_task:read', 'production_task:create', 'production_task:update',
  'production_task:change_status', 'production_task:delete',
  'installation_task:read', 'installation_task:create', 'installation_task:update',
  'installation_task:change_status', 'installation_task:delete',
])
const SENSITIVE_PERMISSION_CODES = new Set([
  'quote:read', 'quote:create', 'quote:update', 'quote:delete',
  'quote:confirm', 'quote:convert',
  'contract:read', 'contract:create', 'contract:update', 'contract:delete',
  'contract:change_status',
  'cdr_quote:read', 'cdr_quote:create', 'cdr_quote:update', 'cdr_quote:delete',
  'cdr_quote:view_cost', 'cdr_quote:view_profit', 'cdr_quote:adjust_price',
  'cdr_quote:approve', 'cdr_quote:convert', 'cdr_rule_set:publish',
  'cdr_customer_agreement:manage',
  'order:view_price', 'order_item:view_price', 'catalog:view_price',
  'finance:view_cost', 'report:view_financial', 'report:read',
  'payment:read', 'payment:create', 'payment:void',
  'statement:read', 'statement:create', 'statement:confirm',
  'expense:read', 'expense:create', 'expense:update', 'expense:delete',
  'outsource_payment:read', 'outsource_payment:create',
])

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
const loadError = ref('')
const roleTableState = computed(() => loading.value ? 'loading' : loadError.value ? 'error' : roles.value.length ? 'ready' : 'empty')

const groupedPerms = computed(() => {
  const groups: Record<string, PermissionItem[]> = {}
  for (const p of allPerms.value) {
    const group = p.code.split(':')[0]
    if (!groups[group]) groups[group] = []
    groups[group].push(p)
  }
  return groups
})

const selectedRoleIsExecution = computed(() => {
  const role = selectedRole.value
  if (!role || role.name === 'admin') return false
  if (EXECUTION_ROLE_NAMES.has(role.name)) return true

  // 新建或编辑自定义角色时，勾选执行权限后立即收紧敏感权限，
  // 不等到保存接口返回错误才提示管理员。
  const executionPermissionIds = new Set(
    allPerms.value
      .filter(permission => EXECUTION_PERMISSION_CODES.has(permission.code))
      .map(permission => permission.id),
  )
  return checkedPermIds.value.some(id => executionPermissionIds.has(id))
})

const assignablePerms = computed(() => allPerms.value.filter(permission => !permissionDisabled(permission)))
const assignablePermIds = computed(() => new Set(assignablePerms.value.map(permission => permission.id)))
const checkedAssignableCount = computed(() => checkedPermIds.value.filter(id => assignablePermIds.value.has(id)).length)
const checkAll = computed(() => assignablePerms.value.length > 0 && checkedAssignableCount.value === assignablePerms.value.length)
const isIndeterminate = computed(() => checkedAssignableCount.value > 0 && !checkAll.value)

function isSensitivePermission(code: string): boolean {
  return SENSITIVE_PERMISSION_CODES.has(code)
}

function permissionDisabled(permission: PermissionItem): boolean {
  if (!selectedRoleIsExecution.value || !isSensitivePermission(permission.code)) return false

  // 历史上已经误配的敏感权限必须保持可取消，否则管理员无法修复角色。
  return !selectedRole.value?.permissions.some(existing => existing.id === permission.id)
}

function handleCheckAll(val: boolean) {
  const assignableIds = assignablePerms.value.map(permission => permission.id)
  const assignableIdSet = new Set(assignableIds)
  const preservedIds = checkedPermIds.value.filter(id => !assignableIdSet.has(id))
  checkedPermIds.value = val ? [...preservedIds, ...assignableIds] : preservedIds
}

async function fetchRoles() {
  loading.value = true
  loadError.value = ''
  try { roles.value = await getRoles() } catch (error: unknown) { loadError.value = getErrorMessage(error); ElMessage.error(loadError.value) } finally { loading.value = false }
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
