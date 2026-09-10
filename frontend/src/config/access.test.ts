import { describe, expect, it } from 'vitest'
import {
  canAccess,
  canAccessRoute,
  filterSmartTools,
  getRouteTitle,
  ROUTE_ACCESS,
} from './access'
import { navigationItems } from './navigation'

function findNavigationItem(path: string) {
  const queue = [...navigationItems]
  while (queue.length) {
    const item = queue.shift()!
    if (item.path === path) return item
    queue.push(...(item.children || []))
  }
  return undefined
}

describe('page access matrix', () => {
  it('allows authenticated pages and blocks protected role pages for the wrong role', () => {
    expect(canAccess('authenticated', [])).toBe(true)
    expect(canAccess('production', ['production'])).toBe(true)
    expect(canAccess('production', ['sales'])).toBe(false)
    expect(canAccess('production', ['admin'])).toBe(true)
  })

  it('shares role groups while allowing read-only routes to be broader than navigation', () => {
    expect(ROUTE_ACCESS.ProductionTaskList).toBe('productionListRead')
    expect(canAccessRoute('ProductionTaskList', ['production'])).toBe(false)
    expect(canAccessRoute('ProductionTaskList', ['sales'])).toBe(true)
    expect(canAccessRoute('ProductionTaskDetail', ['production'])).toBe(true)
    expect(canAccessRoute('OrderList', ['finance'])).toBe(true)
    expect(canAccessRoute('OrderEdit', ['finance'])).toBe(false)

    for (const [path, routeName, navigationRole] of [
      ['/orders', 'OrderList', 'sales'],
      ['/project-costs', 'ProjectCostList', 'finance'],
    ] as const) {
      const item = findNavigationItem(path)
      expect(item?.accessKey).toBeDefined()
      expect(canAccess(item!.accessKey!, [navigationRole])).toBe(true)
      expect(canAccessRoute(routeName, [navigationRole])).toBe(true)
    }
  })

  it('hides task-list routes from execution roles while preserving direct task details', () => {
    for (const [listRoute, detailRoute, listKey, role] of [
      ['DesignTaskList', 'DesignTaskDetail', 'designListRead', 'designer'],
      ['ProductionTaskList', 'ProductionTaskDetail', 'productionListRead', 'production'],
      ['InstallationTaskList', 'InstallationTaskDetail', 'installationListRead', 'installer'],
    ] as const) {
      expect(ROUTE_ACCESS[listRoute]).toBe(listKey)
      expect(canAccessRoute(listRoute, [role])).toBe(false)
      expect(canAccessRoute(detailRoute, [role])).toBe(true)
    }
  })

  it('keeps legacy route meta roles as an additional guard', () => {
    expect(canAccessRoute('Home', ['sales'], ['admin'])).toBe(false)
    expect(canAccessRoute('Home', ['admin'], ['admin'])).toBe(true)
  })

  it('returns stable titles for shell context without changing business rules', () => {
    expect(getRouteTitle('ProjectKanbanBoard')).toBe('项目看板')
    expect(getRouteTitle('UnknownRoute')).toBe('AdCraft ERP')
  })

  it('does not expose smart tools that would only lead to a forbidden page', () => {
    expect(filterSmartTools(['admin'])).toHaveLength(4)
    expect(filterSmartTools(['production'])).toHaveLength(0)
  })

  it('uses server permissions for custom roles without changing built-in role behavior', () => {
    expect(canAccess('design', ['custom-operator'], ['design_task:read'])).toBe(true)
    expect(canAccessRoute(
      'InstallationTaskList',
      ['custom-operator'],
      [],
      ['installation_task:list'],
    )).toBe(true)
    expect(canAccess('production', ['sales'], ['production_task:read'])).toBe(false)
  })

  it('connects resource-center page access to explicit server permissions', () => {
    const vehiclePermissions = ['resource_center:read', 'vehicle:read']
    const aerialPermissions = ['resource_center:read', 'aerial:read']
    expect(canAccess('resourceCenter', ['resource-reader'], ['resource_center:read'])).toBe(true)
    expect(canAccess('vehicleRead', ['resource-reader'], vehiclePermissions)).toBe(true)
    expect(canAccess('aerialRead', ['resource-reader'], aerialPermissions)).toBe(true)
    expect(canAccessRoute('VehicleDashboard', ['resource-reader'], [], vehiclePermissions)).toBe(true)
    expect(canAccessRoute('AerialDashboard', ['resource-reader'], [], aerialPermissions)).toBe(true)
    expect(canAccess('vehicleRead', ['resource-reader'], ['vehicle:read'])).toBe(false)
    expect(canAccess('aerialRead', ['resource-reader'], ['aerial:read'])).toBe(false)
    expect(canAccess('vehicleRead', ['designer'], [])).toBe(false)
    expect(canAccess('aerialRead', ['designer'], [])).toBe(false)
    expect(canAccess('vehicleRead', ['production'], [])).toBe(false)
    expect(canAccessRoute('AerialDashboard', ['production'], [], [])).toBe(false)
  })

  it('keeps external vendor and task entries independently permissioned', () => {
    expect(ROUTE_ACCESS.OutsourceVendorList).toBe('outsourceVendor')
    expect(ROUTE_ACCESS.OutsourceTaskList).toBe('outsourceTask')
    expect(ROUTE_ACCESS.OutsourceTaskRecycle).toBe('outsourceTaskRecycle')

    const taskRead = ['outsource_center:read', 'outsource_task:read']
    const vendorRead = ['outsource_center:read', 'outsource_vendor:read']
    expect(canAccess('outsourceTask', ['custom-outsourcing'], taskRead)).toBe(true)
    expect(canAccess('outsourceVendor', ['custom-outsourcing'], taskRead)).toBe(false)
    expect(canAccess('outsourceVendor', ['custom-outsourcing'], vendorRead)).toBe(true)
    expect(canAccess('outsourceTask', ['custom-outsourcing'], vendorRead)).toBe(false)
    expect(canAccess('outsourceTask', ['custom-outsourcing'], ['outsource_task:read'])).toBe(false)
    expect(canAccess('outsourceTask', ['designer'], [])).toBe(false)
  })
})
