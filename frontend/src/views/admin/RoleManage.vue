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
              title="权限按服务端目录中的模块、动作和前置能力组合；保存前会校验冲突，并检查已绑定用户的最终权限。"
              type="info"
              :closable="false"
              show-icon
              style="margin-bottom: 12px"
            />
            <div v-if="permissionPacks.length" style="display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 12px">
              <span style="color: var(--ad-text-secondary); font-size: 13px">快捷加入权限包：</span>
              <el-button
                v-for="pack in permissionPacks"
                :key="pack.code"
                size="small"
                plain
                @click="applyPermissionPack(pack)"
              >
                {{ pack.name }}
              </el-button>
            </div>
            <el-checkbox :model-value="checkAll" :indeterminate="isIndeterminate" @change="handleCheckAll" style="margin-bottom: 12px">
              全选
            </el-checkbox>
            <el-divider style="margin: 8px 0" />
            <div v-for="(perms, group) in groupedPerms" :key="group" style="margin-bottom: 16px">
              <div style="font-weight: bold; margin-bottom: 8px; color: var(--ad-text)">{{ groupLabels[group as string] || group }}</div>
              <el-checkbox-group v-model="checkedPermIds" @change="handlePermissionGroupChange">
                <el-checkbox
                  v-for="p in perms"
                  :key="p.id"
                  :value="p.id"
                  :disabled="permissionDisabled(p)"
                  style="margin-bottom: 4px"
                >
                  {{ p.name }}
                  <span style="color: var(--ad-text-secondary); font-size: 12px">({{ p.code }})</span>
                  <el-tag v-if="p.kind === 'field' || p.sensitivity !== 'normal'" size="small" type="warning" effect="plain" style="margin-left: 6px">
                    {{ sensitivityLabel(p.sensitivity) }}
                  </el-tag>
                  <el-tag v-if="p.requires?.length" size="small" type="info" effect="plain" style="margin-left: 6px">
                    前置：{{ p.requires.join('、') }}
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
import { getRoles, createRole, updateRole, deleteRole, setRolePermissions, previewRolePermissions, getPermissions, getPermissionPacks, type RoleItem, type PermissionItem, type PermissionPackItem } from '@/api/admin'
import { ElMessage, ElMessageBox } from 'element-plus'
import { AppPage, DataTableShell, PageHeader, StatePanel } from '@/components/ui'
import { getErrorMessage } from '@/utils/error'

const ROLE_MAP: Record<string, string> = {
  admin: '管理员', sales: '销售', designer: '设计师',
  production: '生产', installer: '安装', finance: '财务', resource_manager: '资源管理员',
  outsource_manager: '外协管理员',
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
  inventory: '库存管理', outsource: '外协管理', outsource_center: '外协中心',
  outsource_vendor: '外协商管理', outsource_task: '外协任务管理', report: '报表',
  resource_center: '资源中心',
  vehicle: '资源中心 / 公司车辆', aerial: '资源中心 / 高空作业车',
  backup: '备份管理', ai_quote: 'AI报价', ai_anomaly: 'AI异常',
  ai_knowledge: 'AI知识库', ai_report: 'AI报告',
}

const loading = ref(false)
const saving = ref(false)
const savingPerms = ref(false)
const roles = ref<RoleItem[]>([])
const allPerms = ref<PermissionItem[]>([])
const permissionPacks = ref<PermissionPackItem[]>([])
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
    const group = p.module || p.code.split(':')[0]
    if (!groups[group]) groups[group] = []
    groups[group].push(p)
  }
  return groups
})

const assignablePerms = computed(() => allPerms.value.filter(permission => !permissionDisabled(permission)))
const assignablePermIds = computed(() => new Set(assignablePerms.value.map(permission => permission.id)))
const checkedAssignableCount = computed(() => checkedPermIds.value.filter(id => assignablePermIds.value.has(id)).length)
const checkAll = computed(() => assignablePerms.value.length > 0 && checkedAssignableCount.value === assignablePerms.value.length)
const isIndeterminate = computed(() => checkedAssignableCount.value > 0 && !checkAll.value)

function permissionDisabled(permission: PermissionItem): boolean {
  if (permission.status === 'active') return false
  // Deprecated permissions remain visible and removable, but cannot be newly
  // assigned. The server repeats this policy during save.
  return !selectedRole.value?.permissions.some(existing => existing.id === permission.id)
}

function sensitivityLabel(sensitivity: string): string {
  return {
    price: '价格字段',
    financial: '财务数据',
    external: '外协数据',
    security: '系统安全',
  }[sensitivity] || '敏感能力'
}

function handleCheckAll(val: boolean) {
  const assignableIds = assignablePerms.value.map(permission => permission.id)
  const assignableIdSet = new Set(assignableIds)
  const preservedIds = checkedPermIds.value.filter(id => !assignableIdSet.has(id))
  checkedPermIds.value = val ? normalizePermissionIds([...preservedIds, ...assignableIds]) : preservedIds
}

function normalizePermissionIds(ids: string[]): string[] {
  const byCode = new Map(allPerms.value.map(permission => [permission.code, permission.id]))
  const byId = new Map(allPerms.value.map(permission => [permission.id, permission]))
  const normalized = new Set(ids)
  const pending = [...normalized]
  while (pending.length) {
    const id = pending.pop()!
    const permission = byId.get(id)
    for (const requiredCode of permission?.requires || []) {
      const requiredId = byCode.get(requiredCode)
      if (requiredId && !normalized.has(requiredId)) {
        normalized.add(requiredId)
        pending.push(requiredId)
      }
    }
  }
  return [...normalized]
}

function handlePermissionGroupChange(value: string[] | number[]) {
  checkedPermIds.value = normalizePermissionIds(value.map(String))
}

function applyPermissionPack(pack: PermissionPackItem) {
  const idsByCode = new Map(allPerms.value.map(permission => [permission.code, permission.id]))
  const packIds = pack.permissions
    .map(code => idsByCode.get(code))
    .filter((id): id is string => Boolean(id))
  const missing = pack.permissions.filter(code => !idsByCode.has(code))
  checkedPermIds.value = normalizePermissionIds([...new Set([...checkedPermIds.value, ...packIds])])
  if (missing.length) {
    ElMessage.warning(`${pack.name}缺少目录权限：${missing.join('、')}`)
    return
  }
  ElMessage.success(`已加入权限包：${pack.name}，保存前仍会进行依赖和冲突校验`)
}

async function fetchRoles() {
  loading.value = true
  loadError.value = ''
  try { roles.value = await getRoles() } catch (error: unknown) { loadError.value = getErrorMessage(error); ElMessage.error(loadError.value) } finally { loading.value = false }
}

async function fetchPerms() {
  try { allPerms.value = await getPermissions() } catch { /* ignore */ }
}

async function fetchPermissionPacks() {
  try { permissionPacks.value = await getPermissionPacks() } catch { /* ignore */ }
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
    const preview = await previewRolePermissions(selectedRole.value.id, checkedPermIds.value)
    if (!preview.valid) {
      ElMessage.error(preview.issues.map(issue => issue.message).join('；') || '权限组合校验未通过，未保存')
      return
    }
    const updated = await setRolePermissions(selectedRole.value.id, checkedPermIds.value)
    // Update local data
    const idx = roles.value.findIndex(r => r.id === selectedRole.value!.id)
    if (idx >= 0) roles.value[idx].permissions = updated.permissions
    selectedRole.value.permissions = updated.permissions
    ElMessage.success('权限已保存')
  } catch { /* handled */ } finally { savingPerms.value = false }
}

onMounted(() => { fetchRoles(); fetchPerms(); fetchPermissionPacks() })
</script>
