import type { PermissionItem, RoleItem } from '@/api/admin'

const ROLE_LABELS: Record<string, string> = {
  admin: '管理员', manager: '经理', sales: '销售', designer: '设计师',
  production: '制作', installer: '安装', finance: '财务',
  resource_manager: '资源管理员', outsource_manager: '外协管理员',
}

const MODULE_LABELS: Record<string, string> = {
  system: '系统管理', user: '用户管理', customer: '客户管理',
  order: '订单管理', order_item: '订单明细', contract: '合同管理',
  acceptance: '验收管理', dashboard: '经营驾驶舱', chat: '业务沟通',
  task_queue: '项目看板', task_completion: '任务完成记录',
  design_task: '设计任务', production_task: '制作任务', installation_task: '安装任务',
  product: '产品/材质/工艺', material: '材质（兼容）', process: '工艺（兼容）',
  payment: '收款', statement: '对账单', expense: '支出', report: '经营报表',
  finance: '财务审核', company_account: '公司账户', catalog: '产品价格',
  outsource: '外协（兼容）', outsource_center: '外协中心', outsource_vendor: '外协商',
  outsource_task: '外协任务', outsource_payment: '外协付款',
  supplier_center: '供应商中心', supplier: '供应商',
  resource_center: '资源中心', inventory: '库存', vehicle: '公司车辆', aerial: '高空作业车',
  employee: '员工管理', department: '部门管理', attendance: '考勤', salary: '工资',
  backup: '数据备份', ai_quote: 'AI 业务助手', ai_anomaly: 'AI 异常检查',
  ai_knowledge: 'AI 知识库', ai_report: 'AI 报表',
  quote: '历史报价（兼容）', cdr_quote: '历史智能报价（兼容）',
  cdr_rule_set: '定价规则', cdr_customer_agreement: '客户协议价', cdr_device: '报价设备',
}

export const SUPER_ADMIN_PERMISSION = 'system:super_admin'
export function roleLabel(name: string): string { return ROLE_LABELS[name] || name }
export function moduleLabel(name: string): string { return MODULE_LABELS[name] || name }
export function isBuiltinRole(role: RoleItem): boolean {
  return role.is_builtin ?? Object.prototype.hasOwnProperty.call(ROLE_LABELS, role.name)
}

export function permissionAssignable(permission: PermissionItem, existingIds: readonly string[]): boolean {
  return permission.status === 'active' || existingIds.includes(permission.id)
}

/** Add the complete prerequisite closure, or reject the entire selection. */
export function addPermissionSelection(
  catalog: readonly PermissionItem[], current: readonly string[], requested: readonly string[], existing: readonly string[],
): string[] {
  const byId = new Map(catalog.map(p => [p.id, p]))
  const byCode = new Map(catalog.map(p => [p.code, p]))
  const result = new Set(current)
  const visited = new Set<string>()
  const pending = [...requested]
  while (pending.length) {
    const id = pending.pop()!
    if (visited.has(id)) continue
    visited.add(id)
    const permission = byId.get(id)
    if (!permission || !permissionAssignable(permission, existing)) {
      throw new Error(`权限「${permission?.name || id}」已停用或不在目录中，请重新加载后检查`)
    }
    result.add(id)
    for (const code of permission.requires || []) {
      const dependency = byCode.get(code)
      if (!dependency) throw new Error(`「${permission.name}」缺少前置权限「${code}」，请联系管理员检查权限目录`)
      pending.push(dependency.id)
    }
  }
  return [...result]
}

/** Removing a prerequisite also removes selected transitive dependents. */
export function removePermissionSelection(
  catalog: readonly PermissionItem[], current: readonly string[], requested: readonly string[],
): string[] {
  const removedIds = new Set(requested)
  const removedCodes = new Set(catalog.filter(p => removedIds.has(p.id)).map(p => p.code))
  let changed = true
  while (changed) {
    changed = false
    for (const permission of catalog) {
      if (!current.includes(permission.id) || removedIds.has(permission.id)) continue
      if (permission.requires?.some(code => removedCodes.has(code))) {
        removedIds.add(permission.id)
        removedCodes.add(permission.code)
        changed = true
      }
    }
  }
  return current.filter(id => !removedIds.has(id))
}

export function samePermissionSelection(a: readonly string[], b: readonly string[]): boolean {
  const unique = new Set(a)
  return unique.size === new Set(b).size && b.every(id => unique.has(id))
}

/** Never convert an incomplete role catalogue into an empty assignment. */
export function resolveUserRoleIds(roles: readonly RoleItem[], names: readonly string[]): string[] {
  const byName = new Map(roles.map(role => [role.name, role.id]))
  const missing = names.filter(name => !byName.has(name))
  if (missing.length) throw new Error(`原有角色未完整加载：${missing.map(roleLabel).join('、')}。请重新加载角色后再编辑`)
  return names.map(name => byName.get(name)!)
}
