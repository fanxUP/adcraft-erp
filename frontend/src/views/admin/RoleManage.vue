<template>
  <AppPage>
    <template #header>
      <PageHeader title="角色权限管理" description="选择角色，按业务模块配置权限，预览变更后保存。">
        <template #actions><el-button type="primary" :disabled="busy" @click="openCreate">新增角色</el-button></template>
      </PageHeader>
    </template>

    <div class="role-layout">
      <div class="compact-role-selector">
        <StatePanel v-if="loadError" state="error" :description="loadError" action-label="重新加载角色" @action="fetchRoles" />
        <template v-else>
          <label class="role-select-label" for="compact-role-select">配置角色</label>
          <div class="compact-role-controls">
            <el-select id="compact-role-select" :model-value="selectedRole?.id" aria-label="选择角色" placeholder="请选择需要配置的角色" filterable :loading="loading" :disabled="busy" @change="selectRoleId">
              <el-option v-for="role in roles" :key="role.id" :value="role.id" :label="`${roleLabel(role.name)}（${role.permissions.length} 项权限）`" />
            </el-select>
            <el-button :disabled="busy || !selectedRole" @click="selectedRole && openEdit(selectedRole)">编辑角色</el-button>
            <el-button v-if="selectedRole && !isBuiltinRole(selectedRole)" type="danger" plain :disabled="busy" @click="handleDelete(selectedRole)">删除角色</el-button>
          </div>
          <div v-if="selectedRole" class="muted">{{ isBuiltinRole(selectedRole) ? '内置角色' : '自定义角色' }} · {{ selectedRole.description || '暂无角色说明' }}</div>
        </template>
      </div>
      <DataTableShell class="role-table" :state="roleTableState" aria-label="角色列表">
        <el-table :data="roles" row-key="id" :row-class-name="roleRowClass" stripe @row-click="onRoleSelect">
          <el-table-column label="角色" min-width="130">
            <template #default="{ row }">
              <div>{{ roleLabel(row.name) }}</div>
              <span class="muted">{{ isBuiltinRole(row) ? '内置角色' : '自定义角色' }} · {{ row.permissions.length }} 项权限</span>
            </template>
          </el-table-column>
          <el-table-column prop="description" label="说明" min-width="120" show-overflow-tooltip />
          <el-table-column label="操作" width="110">
            <template #default="{ row }">
              <el-button text type="primary" size="small" :disabled="busy" @click.stop="openEdit(row)">编辑</el-button>
              <el-button v-if="!isBuiltinRole(row)" text type="danger" size="small" :disabled="busy" @click.stop="handleDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <template #error><StatePanel state="error" :description="loadError" action-label="重新加载角色" @action="fetchRoles" /></template>
      </DataTableShell>

      <el-card shadow="never" class="permission-panel">
        <template #header>
          <div class="panel-heading">
            <div>
              <strong>{{ selectedRole ? `${roleLabel(selectedRole.name)} · 权限配置` : '权限配置' }}</strong>
              <div v-if="selectedRole" class="muted" aria-live="polite">
                已选 {{ checkedPermIds.length }} 项
                <span v-if="dirty"> · 新增 {{ addedCount }} 项，移除 {{ removedCount }} 项 · 未保存</span>
              </div>
            </div>
            <div class="heading-actions" v-if="selectedRole">
              <el-button :disabled="busy || !dirty" @click="resetPermissions">重置</el-button>
              <el-button type="primary" :loading="savingPerms" :disabled="busy || !dirty || !catalogReady" @click="handleSavePerms">预览并保存</el-button>
            </div>
          </div>
        </template>

        <StatePanel v-if="!selectedRole" state="empty" title="请选择角色" description="选择需要配置的角色后，可在此设置权限。" />
        <StatePanel v-else-if="catalogLoading" state="loading" title="正在加载权限" />
        <StatePanel v-else-if="catalogError" state="error" :description="catalogError" action-label="重新加载权限" @action="fetchPerms" />
        <template v-else>
          <el-alert title="勾选操作会补齐前置权限；取消前置权限会同时取消依赖它的操作。保存前检查权限冲突及关联用户。" type="info" :closable="false" show-icon />
          <el-alert v-if="superAdminSelected" title="已选择超级管理员：可访问全部业务并跳过普通权限组合限制，请谨慎授予。" type="warning" :closable="false" show-icon class="section-gap" />

          <div v-if="permissionPacks.length" class="permission-packs section-gap">
            <span class="muted">快捷加入：</span>
            <el-button v-for="pack in permissionPacks" :key="pack.code" size="small" plain :title="pack.description" :disabled="busy" @click="applyPermissionPack(pack)">{{ pack.name }}</el-button>
          </div>
          <div v-if="packError" class="section-gap muted" role="status">
            权限包加载失败，可继续逐项配置。<el-button text type="primary" :disabled="busy" @click="fetchPermissionPacks">重试权限包</el-button>
          </div>

          <div class="permission-filters section-gap">
            <el-input v-model="keyword" aria-label="搜索权限" placeholder="搜索模块、权限名称或说明" clearable :disabled="busy" />
            <el-select v-model="permissionFilter" aria-label="权限筛选" :disabled="busy">
              <el-option label="全部权限" value="all" />
              <el-option label="仅已选" value="selected" />
              <el-option label="仅敏感权限" value="sensitive" />
            </el-select>
          </div>

          <StatePanel v-if="!permissionGroups.length" state="empty" title="没有匹配的权限" description="请调整搜索词或筛选条件。" />
          <section v-for="group in permissionGroups" :key="group.module" class="permission-group" :aria-label="moduleLabel(group.module)">
            <div class="group-heading">
              <strong>{{ moduleLabel(group.module) }}</strong>
              <el-checkbox
                :model-value="group.checked"
                :indeterminate="group.indeterminate"
                :disabled="busy || !group.batchIds.length"
                @change="value => changeSelection(group.batchIds, Boolean(value))"
              >{{ hasFilter ? '勾选本组匹配项' : '勾选本组' }}</el-checkbox>
            </div>
            <div class="permission-options">
              <div v-for="permission in group.permissions" :key="permission.id" class="permission-option">
                <el-checkbox
                  :model-value="checkedPermIds.includes(permission.id)"
                  :disabled="busy || !permissionAssignable(permission, originalIds)"
                  @change="value => changeSelection([permission.id], Boolean(value))"
                >
                  {{ permission.name }}
                  <el-tag v-if="permission.status !== 'active'" size="small" type="info" effect="plain">已停用</el-tag>
                  <el-tag v-else-if="permission.sensitivity !== 'normal'" size="small" type="warning" effect="plain">{{ sensitivityLabel(permission.sensitivity) }}</el-tag>
                </el-checkbox>
                <p v-if="permission.description" class="permission-description">{{ permission.description }}</p>
                <p v-if="permission.requires?.length" class="permission-description">前置：{{ permission.requires.map(permissionName).join('、') }}</p>
              </div>
            </div>
          </section>
        </template>
      </el-card>
    </div>

    <el-dialog v-model="showDialog" :title="isEditing ? '编辑角色' : '新增角色'" width="min(440px, 94vw)" :close-on-click-modal="false" :close-on-press-escape="!saving" :show-close="!saving">
      <el-form :model="form" label-width="80px" @submit.prevent="handleSave">
        <el-form-item label="角色名称" required>
          <el-input v-model="form.name" :disabled="saving || editingBuiltin" maxlength="64" placeholder="输入角色名称" />
          <span v-if="editingBuiltin" class="muted">内置角色名称固定，可修改说明和权限。</span>
        </el-form-item>
        <el-form-item label="说明"><el-input v-model="form.description" :disabled="saving" type="textarea" placeholder="说明这个角色负责的业务" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button :disabled="saving" @click="showDialog = false">取消</el-button>
        <el-button :loading="saving" type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showPreview" title="确认权限变更" width="min(640px, 94vw)" :close-on-click-modal="false" :close-on-press-escape="!savingPerms" :show-close="!savingPerms">
      <template v-if="preview">
        <p>{{ previewRoleName }}：新增 {{ preview.added_permissions.length }} 项，移除 {{ preview.removed_permissions.length }} 项；影响 {{ preview.affected_user_count }} 个用户账号（包含停用账号）。</p>
        <el-alert v-if="preview.valid" title="权限组合校验通过，保存后关联用户按新权限执行操作。" type="success" :closable="false" show-icon />
        <el-alert v-else title="权限组合未通过校验，请返回调整。" type="error" :closable="false" show-icon />
        <ul v-if="preview.issues.length" class="preview-issues"><li v-for="(issue, index) in preview.issues" :key="index">{{ readableIssue(issue.message) }}</li></ul>
        <section v-for="change in previewChanges" :key="change.label" class="section-gap">
          <strong>{{ change.label }}（{{ change.codes.length }}）</strong>
          <div class="preview-tags"><el-tag v-for="code in change.codes" :key="code" :type="change.type" effect="plain">{{ permissionName(code) }}</el-tag><span v-if="!change.codes.length" class="muted">无</span></div>
        </section>
      </template>
      <template #footer>
        <el-button :disabled="savingPerms" @click="showPreview = false">返回调整</el-button>
        <el-button type="primary" :loading="savingPerms" :disabled="!preview?.valid || !previewHasChanges" @click="confirmSavePermissions">确认保存</el-button>
      </template>
    </el-dialog>
  </AppPage>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getRoles, createRole, updateRole, deleteRole, setRolePermissions, previewRolePermissions, getPermissions, getPermissionPacks, type RoleItem, type PermissionItem, type PermissionPackItem, type RolePermissionPreview } from '@/api/admin'
import { AppPage, DataTableShell, PageHeader, StatePanel } from '@/components/ui'
import { getErrorMessage } from '@/utils/error'
import { SUPER_ADMIN_PERMISSION, roleLabel, moduleLabel, isBuiltinRole, permissionAssignable, addPermissionSelection, removePermissionSelection, samePermissionSelection } from '@/utils/permissionEditor'

const loading = ref(false)
const saving = ref(false)
const savingPerms = ref(false)
const roles = ref<RoleItem[]>([])
const allPerms = ref<PermissionItem[]>([])
const permissionPacks = ref<PermissionPackItem[]>([])
const selectedRole = ref<RoleItem | null>(null)
const selectingRole = ref(false)
const checkedPermIds = ref<string[]>([])
const showDialog = ref(false)
const isEditing = ref(false)
const editingId = ref('')
const form = reactive({ name: '', description: '' })
const loadError = ref('')
const catalogLoading = ref(true)
const catalogError = ref('')
const packError = ref(false)
const keyword = ref('')
const permissionFilter = ref('all')
const showPreview = ref(false)
const preview = ref<RolePermissionPreview | null>(null)
const previewSnapshot = ref<{ roleId: string; ids: string[] } | null>(null)
const previewRoleName = ref('')
const busy = computed(() => saving.value || savingPerms.value || showPreview.value)
const originalIds = computed(() => selectedRole.value?.permissions.map(p => p.id) || [])
const dirty = computed(() => !!selectedRole.value && !samePermissionSelection(checkedPermIds.value, originalIds.value))
const addedCount = computed(() => checkedPermIds.value.filter(id => !originalIds.value.includes(id)).length)
const removedCount = computed(() => originalIds.value.filter(id => !checkedPermIds.value.includes(id)).length)
const catalogReady = computed(() => !catalogLoading.value && !catalogError.value)
const roleTableState = computed(() => loading.value ? 'loading' : loadError.value ? 'error' : roles.value.length ? 'ready' : 'empty')
const editingBuiltin = computed(() => isEditing.value && !!roles.value.find(role => role.id === editingId.value && isBuiltinRole(role)))
const catalog = computed(() => [...new Map([...(selectedRole.value?.permissions || []), ...allPerms.value].map(p => [p.id, p])).values()])
const superAdminSelected = computed(() => catalog.value.some(p => p.code === SUPER_ADMIN_PERMISSION && checkedPermIds.value.includes(p.id)))
const hasFilter = computed(() => !!keyword.value.trim() || permissionFilter.value !== 'all')
const previewHasChanges = computed(() => !!preview.value && !!(preview.value.added_permissions.length || preview.value.removed_permissions.length))
const previewChanges = computed(() => [
  { label: '新增权限', codes: preview.value?.added_permissions || [], type: 'success' as const },
  { label: '移除权限', codes: preview.value?.removed_permissions || [], type: 'danger' as const },
])

const permissionGroups = computed(() => {
  const groups = new Map<string, PermissionItem[]>()
  const query = keyword.value.trim().toLocaleLowerCase()
  for (const p of [...catalog.value].sort((a, b) => a.sort_order - b.sort_order || a.code.localeCompare(b.code))) {
    const selected = checkedPermIds.value.includes(p.id)
    if (['quote', 'cdr_quote'].includes(p.module) && !originalIds.value.includes(p.id)) continue
    if (!permissionAssignable(p, originalIds.value)) continue
    if (permissionFilter.value === 'selected' && !selected) continue
    if (permissionFilter.value === 'sensitive' && p.sensitivity === 'normal') continue
    if (query && !`${moduleLabel(p.module)} ${p.name} ${p.description || ''} ${p.code}`.toLocaleLowerCase().includes(query)) continue
    const group = groups.get(p.module) || []
    group.push(p)
    groups.set(p.module, group)
  }
  return [...groups].map(([module, permissions]) => {
    // Super-admin must be granted explicitly, never through a batch action.
    const batchIds = permissions.filter(p => p.status === 'active' && p.code !== SUPER_ADMIN_PERMISSION).map(p => p.id)
    const count = batchIds.filter(id => checkedPermIds.value.includes(id)).length
    return { module, permissions, batchIds, checked: batchIds.length > 0 && count === batchIds.length, indeterminate: count > 0 && count < batchIds.length }
  })
})

function permissionName(code: string): string { return catalog.value.find(p => p.code === code)?.name || code }
function readableIssue(message: string): string {
  return message.replace(/[a-z_]+(?::[a-z_]+)+/g, code => permissionName(code))
}
function sensitivityLabel(value: string): string {
  return ({ price: '价格', financial: '财务', external: '外协', security: '系统安全' } as Record<string, string>)[value] || '敏感权限'
}

function changeSelection(ids: string[], checked: boolean) {
  if (busy.value || !catalogReady.value) return
  try {
    const previous = checkedPermIds.value
    const next = checked
      ? addPermissionSelection(catalog.value, previous, ids, originalIds.value)
      : removePermissionSelection(catalog.value, previous, ids)
    checkedPermIds.value = next
    const extra = checked ? next.filter(id => !previous.includes(id) && !ids.includes(id)).length : previous.filter(id => !next.includes(id) && !ids.includes(id)).length
    if (extra) ElMessage.info(checked ? `已同时勾选 ${extra} 项前置权限` : `已同时取消 ${extra} 项依赖权限`)
  } catch (error) { ElMessage.warning(getErrorMessage(error)) }
}

function applyPermissionPack(pack: PermissionPackItem) {
  const byCode = new Map(catalog.value.map(p => [p.code, p.id]))
  if (pack.permissions.some(code => !byCode.has(code))) {
    ElMessage.warning('权限包目录不完整，请重新加载权限后再试')
    return
  }
  changeSelection(pack.permissions.map(code => byCode.get(code)!), true)
}

async function fetchRoles() {
  loading.value = true
  loadError.value = ''
  try { roles.value = await getRoles() }
  catch (error) { loadError.value = getErrorMessage(error) }
  finally { loading.value = false }
}
async function fetchPerms() {
  catalogLoading.value = true
  catalogError.value = ''
  try {
    const permissions = await getPermissions()
    if (!permissions.length) throw new Error('权限目录为空，请重新加载或联系管理员检查')
    allPerms.value = permissions
  } catch (error) { catalogError.value = getErrorMessage(error) }
  finally { catalogLoading.value = false }
}
async function fetchPermissionPacks() {
  packError.value = false
  try { permissionPacks.value = await getPermissionPacks() }
  catch { packError.value = true }
}

async function mayDiscardChanges(): Promise<boolean> {
  if (busy.value) return false
  if (!dirty.value) return true
  try {
    await ElMessageBox.confirm('当前权限修改尚未保存，确定放弃这些修改吗？', '未保存的权限', { confirmButtonText: '放弃修改', cancelButtonText: '继续编辑', type: 'warning' })
    return true
  } catch { return false }
}
async function onRoleSelect(role: RoleItem) {
  if (selectingRole.value || role.id === selectedRole.value?.id) return
  selectingRole.value = true
  try {
    if (!await mayDiscardChanges()) return
    selectedRole.value = role
    checkedPermIds.value = role.permissions.map(p => p.id)
    keyword.value = ''
    permissionFilter.value = 'all'
  } finally { selectingRole.value = false }
}
function roleRowClass({ row }: { row: RoleItem }): string { return row.id === selectedRole.value?.id ? 'selected-role-row' : '' }
function selectRoleId(id: string) {
  const role = roles.value.find(role => role.id === id)
  if (role) return onRoleSelect(role)
}
function resetPermissions() {
  if (!busy.value) checkedPermIds.value = [...originalIds.value]
}
function openCreate() {
  form.name = ''; form.description = ''
  isEditing.value = false; editingId.value = ''; showDialog.value = true
}
function openEdit(role: RoleItem) {
  form.name = role.name; form.description = role.description || ''
  isEditing.value = true; editingId.value = role.id; showDialog.value = true
}
async function handleSave() {
  if (saving.value) return
  const name = form.name.trim()
  if (!name) { ElMessage.warning('角色名称不能为空'); return }
  saving.value = true
  try {
    if (isEditing.value) {
      await updateRole(editingId.value, { name, description: form.description })
      const role = roles.value.find(r => r.id === editingId.value)
      if (role) { role.name = name; role.description = form.description }
    } else {
      const role = await createRole({ name, description: form.description })
      roles.value.push(role)
    }
    showDialog.value = false
    ElMessage.success(isEditing.value ? '角色已更新' : '角色已创建，请选择角色配置权限')
  } catch (error) { ElMessage.error(getErrorMessage(error)) }
  finally { saving.value = false }
}
async function handleDelete(role: RoleItem) {
  if (busy.value) return
  saving.value = true
  try {
    await ElMessageBox.confirm(`确定删除角色「${roleLabel(role.name)}」吗？已绑定用户的角色需要先解除绑定。`, '确认删除', { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' })
    await deleteRole(role.id)
    roles.value = roles.value.filter(r => r.id !== role.id)
    if (selectedRole.value?.id === role.id) { selectedRole.value = null; checkedPermIds.value = [] }
    ElMessage.success('角色已删除')
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(getErrorMessage(error))
  }
  finally { saving.value = false }
}
async function handleSavePerms() {
  if (!selectedRole.value || busy.value || !dirty.value || !catalogReady.value) return
  const snapshot = { roleId: selectedRole.value.id, ids: [...checkedPermIds.value] }
  previewRoleName.value = roleLabel(selectedRole.value.name)
  savingPerms.value = true
  try {
    const result = await previewRolePermissions(snapshot.roleId, snapshot.ids)
    if (selectedRole.value?.id !== snapshot.roleId || !samePermissionSelection(checkedPermIds.value, snapshot.ids)) return
    previewSnapshot.value = snapshot
    preview.value = result
    showPreview.value = true
  } catch (error) { ElMessage.error(getErrorMessage(error)) }
  finally { savingPerms.value = false }
}
async function confirmSavePermissions() {
  const snapshot = previewSnapshot.value
  if (savingPerms.value || !preview.value?.valid || !previewHasChanges.value || !snapshot) return
  if (selectedRole.value?.id !== snapshot.roleId || !samePermissionSelection(checkedPermIds.value, snapshot.ids)) {
    showPreview.value = false
    ElMessage.warning('权限选择已变化，请重新预览')
    return
  }
  savingPerms.value = true
  try {
    const updated = await setRolePermissions(snapshot.roleId, snapshot.ids)
    const role = roles.value.find(r => r.id === snapshot.roleId)
    if (role) role.permissions = updated.permissions
    if (selectedRole.value?.id === snapshot.roleId) {
      selectedRole.value.permissions = updated.permissions
      checkedPermIds.value = updated.permissions.map(p => p.id)
    }
    showPreview.value = false
    ElMessage.success('权限已保存')
  } catch (error) {
    showPreview.value = false
    preview.value = null
    ElMessage.error(getErrorMessage(error))
  } finally { savingPerms.value = false }
}

function beforeUnload(event: BeforeUnloadEvent) {
  if (!dirty.value && !savingPerms.value) return
  event.preventDefault()
  event.returnValue = ''
}
onBeforeRouteLeave(mayDiscardChanges)
onMounted(() => { fetchRoles(); fetchPerms(); fetchPermissionPacks(); window.addEventListener('beforeunload', beforeUnload) })
onBeforeUnmount(() => window.removeEventListener('beforeunload', beforeUnload))
</script>

<style scoped>
.role-layout { display: grid; grid-template-columns: minmax(330px, 2fr) minmax(0, 3fr); align-items: start; gap: 20px; }
.permission-panel { min-width: 0; }
.compact-role-selector { display: none; }
.role-select-label { display: block; margin-bottom: 8px; font-weight: 600; }
.compact-role-controls { display: flex; gap: 12px; align-items: center; margin-bottom: 8px; }
.compact-role-controls :deep(.el-select) { flex: 1; min-width: 0; }
.compact-role-controls :deep(.el-button) { margin-left: 0; }
:deep(.el-table .selected-role-row > .el-table__cell) { background: var(--el-color-primary-light-9); }
.panel-heading, .group-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.heading-actions, .permission-packs, .preview-tags { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.heading-actions :deep(.el-button), .permission-packs :deep(.el-button) { margin-left: 0; }
.muted, .permission-description { color: var(--el-text-color-secondary); font-size: 13px; line-height: 1.6; }
.section-gap { margin-top: 16px; }
.permission-filters { display: grid; grid-template-columns: minmax(0, 1fr) 150px; gap: 12px; }
.permission-group { padding: 16px 0; border-bottom: 1px solid var(--el-border-color-lighter); }
.permission-group:last-child { border-bottom: 0; }
.permission-options { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 4px 16px; }
.permission-option { min-width: 0; padding: 4px 0; }
.permission-option :deep(.el-checkbox) { max-width: 100%; height: auto; min-height: 36px; white-space: normal; align-items: flex-start; }
.permission-option :deep(.el-checkbox__input) { margin-top: 8px; }
.permission-option :deep(.el-checkbox__label) { white-space: normal; line-height: 1.8; overflow-wrap: anywhere; }
.permission-option :deep(.el-tag) { margin-left: 4px; }
.permission-description { margin: 0 0 4px 22px; overflow-wrap: anywhere; }
.preview-tags { margin-top: 8px; }
.preview-tags :deep(.el-tag) { height: auto; white-space: normal; }
.preview-issues { padding-left: 20px; line-height: 1.8; }
@media (max-width: 1100px) {
  .role-layout { grid-template-columns: 1fr; }
  .compact-role-selector { display: block; }
  .role-table { display: none; }
}
@media (max-width: 600px) {
  .permission-options, .permission-filters { grid-template-columns: 1fr; }
  .compact-role-controls { flex-wrap: wrap; }
  .compact-role-controls :deep(.el-select) { flex-basis: 100%; }
}
</style>
