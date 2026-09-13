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

  it('lets any delivery-stage operator enter the shared project board', () => {
    expect(findNavigationItem('/production-tasks/board')?.accessKey).toBe('boardRead')
    expect(canAccess('boardRead', ['designer'], ['design_task:read'])).toBe(true)
    expect(canAccess('boardRead', ['production'], ['production_task:read'])).toBe(true)
    expect(canAccess('boardRead', ['installer'], ['installation_task:read'])).toBe(true)
  })

  it('gives the manager operational read access without commercial or write access', () => {
    const managerPermissions = [
      'dashboard:read',
      'report:read',
      'order:read',
      'task_queue:read',
      'design_task:read',
      'production_task:read',
      'installation_task:read',
      'task_completion:read',
      'task_completion:view_all',
    ]

    expect(canAccess('boardRead', ['manager'], managerPermissions)).toBe(true)
    expect(canAccess('orderRead', ['manager'], managerPermissions)).toBe(true)
    expect(canAccess('orderManage', ['manager'], managerPermissions)).toBe(false)
    expect(canAccess('reports', ['manager'], managerPermissions)).toBe(true)
    expect(canAccess('taskCompletion', ['manager'], managerPermissions)).toBe(true)
    expect(canAccess('finance', ['manager'], managerPermissions)).toBe(false)
  })

  it('protects the standalone completed-project detail route with completion read permission', () => {
    expect(ROUTE_ACCESS.CompletedProjectDetail).toBe('taskCompletion')
    expect(canAccess('taskCompletion', ['custom'], ['task_completion:read'])).toBe(true)
    expect(canAccess('taskCompletion', ['custom'], ['design_task:read'])).toBe(false)
    expect(canAccessRoute('CompletedProjectDetail', ['custom'], [], ['task_completion:read'])).toBe(true)
    expect(canAccessRoute('CompletedProjectDetail', ['custom'], [], [])).toBe(false)
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
    expect(canAccess('production', ['sales'], ['production_task:read'])).toBe(true)
  })

  it('uses atomic permissions for sales, order and finance pages', () => {
    expect(canAccess('customer', ['custom'], ['customer:read'])).toBe(true)
    expect(canAccess('quote', ['custom'], ['customer:read'])).toBe(false)
    expect(canAccess('orderManage', ['custom'], ['order:read'])).toBe(false)
    expect(canAccess('orderRead', ['custom'], ['order:read'])).toBe(true)
    expect(canAccess('finance', ['custom'], ['expense:read'])).toBe(true)
    expect(canAccess('projectCost', ['custom'], ['expense:read'])).toBe(true)
    expect(canAccess('statement', ['custom'], ['expense:read'])).toBe(false)
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

  it('keeps AI pages aligned with their exact backend permission contracts', () => {
    const custom = ['custom-ai']

    expect(canAccessRoute('AIQuoteAssistant', custom, [], ['ai_quote:read'])).toBe(true)
    expect(canAccessRoute('QuoteKnowledgeBase', custom, [], ['ai_knowledge:read'])).toBe(false)
    expect(canAccessRoute(
      'QuoteKnowledgeBase',
      custom,
      [],
      ['ai_knowledge:read', 'order:view_price'],
    )).toBe(true)
    expect(canAccessRoute('AnomalyDashboard', custom, [], ['ai_anomaly:read'])).toBe(true)
    expect(canAccessRoute('BusinessNarrativeReport', custom, [], ['ai_report:read'])).toBe(false)
    expect(canAccessRoute(
      'BusinessNarrativeReport',
      custom,
      [],
      ['ai_report:read', 'report:view_financial'],
    )).toBe(true)
    expect(canAccessRoute('SitePhotoRecognition', custom, [], ['ai_quote:read'])).toBe(true)
    expect(canAccessRoute('PaymentOCR', custom, [], ['ai_quote:read'])).toBe(true)
  })
})
