import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as Vue from 'vue'
import { compileScript, parse } from '@vue/compiler-sfc'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { ModuleKind, ScriptTarget, transpileModule } from 'typescript'
import type { PermissionItem, RoleItem, RolePermissionPreview } from '@/api/admin'
import * as permissionEditor from '@/utils/permissionEditor'
import { getErrorMessage } from '@/utils/error'
import * as password from '@/utils/password'

const api = {
  getRoles: vi.fn(), getPermissions: vi.fn(), getPermissionPacks: vi.fn(),
  previewRolePermissions: vi.fn(), setRolePermissions: vi.fn(),
  createRole: vi.fn(), updateRole: vi.fn(), deleteRole: vi.fn(),
  getUsers: vi.fn(), updateUser: vi.fn(), deleteUser: vi.fn(), resetPassword: vi.fn(),
}
const messages = { error: vi.fn(), warning: vi.fn(), success: vi.fn(), info: vi.fn() }
const confirm = vi.fn()
let leaveGuard: () => Promise<boolean>
const disposers: (() => void)[] = []

// Run the actual SFC setup in Vue, with in-memory rendering and mocked APIs.
// This exercises async handlers and watchers without a DOM dependency.
interface HostNode { parent: HostNode | null; children: HostNode[] }
const node = (): HostNode => ({ parent: null, children: [] })
const renderer = Vue.createRenderer<HostNode, HostNode>({
  createElement: node, createText: node, createComment: node,
  setText: () => {}, setElementText: () => {}, patchProp: () => {},
  parentNode: n => n.parent, nextSibling: () => null,
  insert(n, parent) { n.parent = parent; parent.children.push(n) },
  remove: () => {},
})
interface RoleEditorState {
  roles: RoleItem[]; selectedRole: RoleItem | null; checkedPermIds: string[]; dirty: boolean;
  showPreview: boolean; preview: RolePermissionPreview | null; catalogError: string;
  permissionGroups: { module: string; batchIds: string[] }[];
  onRoleSelect: (role: RoleItem) => Promise<void>;
  changeSelection: (ids: string[], selected: boolean) => void;
  handleSavePerms: () => Promise<void>; confirmSavePermissions: () => Promise<void>;
}
interface UserEditorState {
  rolesReady: boolean; rolesError: boolean; showDialog: boolean;
  form: { role_ids: string[] }; openEdit: (row: { id: string; roles: string[] }) => void;
  handleSave: () => Promise<void>;
}
function mountSetup<T>(filename: string): T {
  const { descriptor } = parse(readFileSync(fileURLToPath(new URL(filename, import.meta.url)), 'utf8'))
  const script = compileScript(descriptor, { id: filename })
  const code = transpileModule(script.content, { compilerOptions: { target: ScriptTarget.ES2020, module: ModuleKind.CommonJS } }).outputText
  const modules: Record<string, unknown> = {
    vue: Vue, 'vue-router': { onBeforeRouteLeave: (guard: typeof leaveGuard) => { leaveGuard = guard } },
    'element-plus': { ElMessage: messages, ElMessageBox: { confirm } },
    '@/api/admin': api, '@/api/users': api, '@/components/ui': {},
    '@/utils/permissionEditor': permissionEditor, '@/utils/error': { getErrorMessage },
    '@/utils/password': password,
  }
  const output: { exports: { default?: Vue.ComponentOptions } } = { exports: {} }
  new Function('require', 'module', 'exports', code)((id: string) => {
    if (!(id in modules)) throw new Error(`Unexpected module: ${id}`)
    return modules[id]
  }, output, output.exports)
  const component = output.exports.default!
  let state: T
  const app = renderer.createApp({
    setup(props, context) {
      const result = component.setup!(props, context as never)
      state = Vue.proxyRefs(result as object) as T
      return () => Vue.h('div')
    },
  })
  app.mount(node())
  disposers.push(() => app.unmount())
  return state!
}
async function settle() { for (let i = 0; i < 8; i++) { await Promise.resolve(); await Vue.nextTick() } }
const permission = (id: string, code: string, requires: string[] = []): PermissionItem => ({
  id, code, requires, name: code, module: code.split(':')[0]!, resource: '', action: '', kind: 'action', status: 'active', sensitivity: 'normal', sort_order: 0,
})
const read = permission('read', 'order:read')
const edit = permission('edit', 'order:update', ['order:read'])
const superAdmin = permission('super', 'system:super_admin')
function preview(valid = true): RolePermissionPreview {
  return { role_id: 'a', valid, issues: valid ? [] : [{ kind: 'conflict', code: 'conflict', message: '权限组合冲突', permissions: [] }], added_permissions: ['order:update'], removed_permissions: [], affected_user_count: 2, permissions: [read, edit] }
}

beforeEach(() => {
  vi.resetAllMocks()
  vi.stubGlobal('window', { addEventListener: vi.fn(), removeEventListener: vi.fn() })
  api.getRoles.mockResolvedValue([
    { id: 'a', name: 'custom-a', permissions: [read] },
    { id: 'b', name: 'custom-b', permissions: [] },
  ])
  api.getPermissions.mockResolvedValue([read, edit, superAdmin])
  api.getPermissionPacks.mockResolvedValue([])
  api.getUsers.mockResolvedValue({ items: [], total: 0 })
  api.previewRolePermissions.mockResolvedValue(preview())
  api.setRolePermissions.mockResolvedValue({ id: 'a', name: 'custom-a', permissions: [read, edit] })
  confirm.mockResolvedValue(true)
})
afterEach(() => { disposers.splice(0).forEach(dispose => dispose()); vi.unstubAllGlobals() })

describe('角色权限管理保存与失败边界', () => {
  it('预览及保存中阻止切换角色，返回结果只更新请求所属角色', async () => {
    const state = mountSetup<RoleEditorState>('./RoleManage.vue')
    await settle()
    await state.onRoleSelect(state.roles[0]!)
    state.changeSelection(['edit'], true)
    let resolvePreview!: (value: RolePermissionPreview) => void
    api.previewRolePermissions.mockReturnValue(new Promise(resolve => { resolvePreview = resolve }))
    const loading = state.handleSavePerms()
    await state.onRoleSelect(state.roles[1]!)
    expect(state.selectedRole?.id).toBe('a')
    resolvePreview(preview())
    await loading
    expect(state.showPreview).toBe(true)
    expect(state.preview?.affected_user_count).toBe(2)
    expect(api.setRolePermissions).not.toHaveBeenCalled()
    let resolveSave!: (value: RoleItem) => void
    api.setRolePermissions.mockReturnValue(new Promise(resolve => { resolveSave = resolve }))
    const saving = state.confirmSavePermissions()
    await state.onRoleSelect(state.roles[1]!)
    resolveSave({ id: 'a', name: 'custom-a', permissions: [read, edit] })
    await saving
    expect(api.setRolePermissions).toHaveBeenCalledExactlyOnceWith('a', ['read', 'edit'])
    expect(state.roles[1]!.permissions).toEqual([])
    expect(state.dirty).toBe(false)
  })

  it('校验冲突和预览网络失败时均不调用写入接口', async () => {
    const state = mountSetup<RoleEditorState>('./RoleManage.vue')
    await settle()
    await state.onRoleSelect(state.roles[0]!)
    state.changeSelection(['edit'], true)
    api.previewRolePermissions.mockResolvedValue(preview(false))
    await state.handleSavePerms()
    await state.confirmSavePermissions()
    expect(api.setRolePermissions).not.toHaveBeenCalled()
    state.showPreview = false
    api.previewRolePermissions.mockRejectedValue(new Error('offline'))
    await state.handleSavePerms()
    expect(state.dirty).toBe(true)
    expect(messages.error).toHaveBeenCalled()
    expect(api.setRolePermissions).not.toHaveBeenCalled()
  })

  it('未保存时取消切换或离开仍保留选择，确认放弃才切换', async () => {
    const state = mountSetup<RoleEditorState>('./RoleManage.vue')
    await settle()
    await state.onRoleSelect(state.roles[0]!)
    state.changeSelection(['edit'], true)
    confirm.mockRejectedValue('cancel')
    await state.onRoleSelect(state.roles[1]!)
    expect(state.selectedRole?.id).toBe('a')
    expect(await leaveGuard()).toBe(false)
    confirm.mockResolvedValue(true)
    await state.onRoleSelect(state.roles[1]!)
    expect(state.selectedRole?.id).toBe('b')
    expect(state.checkedPermIds).toEqual([])
  })

  it('保存接口拒绝时保留草稿和原有授权，必须重新预览', async () => {
    const state = mountSetup<RoleEditorState>('./RoleManage.vue')
    await settle()
    await state.onRoleSelect(state.roles[0]!)
    state.changeSelection(['edit'], true)
    await state.handleSavePerms()
    api.setRolePermissions.mockRejectedValue(new Error('用户权限组合已变化'))
    await state.confirmSavePermissions()
    expect(state.checkedPermIds).toEqual(['read', 'edit'])
    expect(state.roles[0]!.permissions).toEqual([read])
    expect(state.dirty).toBe(true)
    expect(state.showPreview).toBe(false)
    expect(state.preview).toBeNull()
    expect(messages.error).toHaveBeenCalled()
  })

  it('目录失败阻止授权写入；模块批量勾选不会授予超级管理能力', async () => {
    api.getPermissions.mockRejectedValueOnce(new Error('offline'))
    const failed = mountSetup<RoleEditorState>('./RoleManage.vue')
    await settle()
    await failed.onRoleSelect(failed.roles[0]!)
    failed.changeSelection(['edit'], true)
    await failed.handleSavePerms()
    expect(failed.catalogError).toBeTruthy()
    expect(failed.checkedPermIds).toEqual(['read'])
    expect(api.previewRolePermissions).not.toHaveBeenCalled()

    const state = mountSetup<RoleEditorState>('./RoleManage.vue')
    await settle()
    await state.onRoleSelect(state.roles[0]!)
    for (const group of state.permissionGroups) state.changeSelection(group.batchIds, true)
    expect(state.checkedPermIds).toContain('edit')
    expect(state.checkedPermIds).not.toContain('super')
  })
})

describe('用户管理角色目录保护', () => {
  it('角色接口失败时无法打开或提交空授权', async () => {
    api.getRoles.mockRejectedValue(new Error('offline'))
    const state = mountSetup<UserEditorState>('./UserManage.vue')
    await settle()
    expect(state.rolesReady).toBe(false)
    state.openEdit({ id: 'user', roles: ['custom-a'] })
    await state.handleSave()
    expect(state.showDialog).toBe(false)
    expect(api.updateUser).not.toHaveBeenCalled()
  })
  it('原有角色不在目录中时阻止编辑；完整加载时保留原有角色', async () => {
    const state = mountSetup<UserEditorState>('./UserManage.vue')
    await settle()
    state.openEdit({ id: 'user', roles: ['missing-role'] })
    expect(state.rolesError).toBe(true)
    expect(state.showDialog).toBe(false)
    expect(api.updateUser).not.toHaveBeenCalled()

    const valid = mountSetup<UserEditorState>('./UserManage.vue')
    await settle()
    valid.openEdit({ id: 'user', roles: ['custom-a'] })
    expect(valid.form.role_ids).toEqual(['a'])
    expect(valid.showDialog).toBe(true)
  })
})
