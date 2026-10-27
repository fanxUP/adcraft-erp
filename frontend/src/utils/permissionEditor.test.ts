import { describe, expect, it } from 'vitest'
import type { PermissionItem } from '@/api/admin'
import { addPermissionSelection, removePermissionSelection, samePermissionSelection, resolveUserRoleIds, isBuiltinRole } from './permissionEditor'

const permission = (id: string, code: string, requires: string[] = [], status = 'active'): PermissionItem => ({
  id, code, name: code, requires, status, module: code.split(':')[0]!, resource: '', action: '', kind: 'action', sensitivity: 'normal', sort_order: 0,
})
const catalog = [
  permission('read', 'order:read'), permission('price', 'order:view_price', ['order:read']),
  permission('edit', 'order:update', ['order:view_price']), permission('other', 'customer:read'),
]

describe('权限编辑依赖与原有授权保护', () => {
  it('选择操作时补齐跨模块传递依赖且不修改原数组', () => {
    const previous = ['other']
    expect(new Set(addPermissionSelection(catalog, previous, ['edit'], []))).toEqual(new Set(['other', 'edit', 'price', 'read']))
    expect(previous).toEqual(['other'])
  })
  it('取消前置权限会同时取消传递依赖项，保留其他模块', () => {
    expect(removePermissionSelection(catalog, ['read', 'price', 'edit', 'other'], ['read'])).toEqual(['other'])
    expect(removePermissionSelection(catalog, ['read', 'price', 'edit', 'other'], ['edit'])).toEqual(['read', 'price', 'other'])
  })
  it('拒绝缺失或已停用依赖，避免部分勾选', () => {
    expect(() => addPermissionSelection(catalog.slice(1), [], ['edit'], [])).toThrow('缺少前置权限')
    const old = [permission('old', 'old:read', [], 'deprecated'), permission('new', 'new:read', ['old:read'])]
    expect(() => addPermissionSelection(old, [], ['new'], [])).toThrow('已停用')
    expect(addPermissionSelection(old, ['old'], ['new'], ['old'])).toEqual(['old', 'new'])
  })
  it('遗留权限可移除；取消后保存前可恢复，不能分配给其他角色', () => {
    const old = [permission('old', 'old:read', [], 'deprecated')]
    expect(removePermissionSelection(old, ['old'], ['old'])).toEqual([])
    expect(addPermissionSelection(old, [], ['old'], ['old'])).toEqual(['old'])
    expect(() => addPermissionSelection(old, [], ['old'], [])).toThrow('已停用')
  })
  it('前置权限已经选中时仍检查其完整依赖', () => {
    expect(new Set(addPermissionSelection(catalog, ['price'], ['edit'], []))).toEqual(new Set(['read', 'price', 'edit']))
  })
  it('比较权限集合忽略顺序与重复', () => {
    expect(samePermissionSelection(['read', 'edit'], ['edit', 'read'])).toBe(true)
    expect(samePermissionSelection(['read'], ['read', 'read'])).toBe(true)
    expect(samePermissionSelection(['read'], ['edit'])).toBe(false)
  })
  it('原有角色目录不完整时拒绝生成可提交的空授权', () => {
    const roles = [{ id: 'sales', name: 'sales', permissions: [] }]
    expect(resolveUserRoleIds(roles, ['sales'])).toEqual(['sales'])
    expect(resolveUserRoleIds(roles, [])).toEqual([])
    expect(() => resolveUserRoleIds([], ['sales'])).toThrow('原有角色未完整加载')
    expect(() => resolveUserRoleIds(roles, ['sales', 'custom'])).toThrow('custom')
  })
  it('内置角色保护优先使用服务端标记，兼容旧版本响应', () => {
    expect(isBuiltinRole({ id: 'x', name: 'designer', permissions: [] })).toBe(true)
    expect(isBuiltinRole({ id: 'x', name: 'new-built-in', permissions: [], is_builtin: true })).toBe(true)
    expect(isBuiltinRole({ id: 'x', name: 'custom', permissions: [], is_builtin: false })).toBe(false)
  })
})
