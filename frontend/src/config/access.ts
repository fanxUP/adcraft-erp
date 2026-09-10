/**
 * Frontend page visibility rules.
 *
 * These rules keep the shell and router consistent, but they are not the
 * security boundary. API permissions and object-state checks on the server
 * remain authoritative; P04 will add the server-provided action capabilities.
 */

export type AccessKey =
  | 'public'
  | 'authenticated'
  | 'sales'
  | 'orderRead'
  | 'product'
  | 'design'
  | 'designRead'
  | 'production'
  | 'productionRead'
  | 'installation'
  | 'installationRead'
  | 'boardRead'
  | 'finance'
  | 'reports'
  | 'outsource'
  | 'inventory'
  | 'system'
  | 'vehicleRead'
  | 'vehicleFleet'
  | 'vehicleDrivers'
  | 'vehicleOperations'
  | 'vehicleExpenses'
  | 'vehicleReports'
  | 'aerialRead'
  | 'aerialOperations'
  | 'aerialFinance'
  | 'aerialFinanceOperations'
  | 'aiSales'
  | 'aiReports'

type AccessRoles = readonly string[] | null

/**
 * Role groups are deliberately about page visibility only. They do not grant
 * a write action and must not be used as a substitute for backend authz.
 */
export const ACCESS_ROLES: Record<AccessKey, AccessRoles> = {
  public: [],
  authenticated: null,
  sales: ['admin', 'sales'],
  orderRead: ['admin', 'sales', 'finance'],
  product: ['admin', 'designer', 'production'],
  design: ['admin', 'designer'],
  designRead: ['admin', 'sales', 'designer'],
  production: ['admin', 'production'],
  productionRead: ['admin', 'sales', 'designer', 'production'],
  installation: ['admin', 'installer'],
  installationRead: ['admin', 'sales', 'designer', 'installer'],
  boardRead: ['admin', 'sales', 'designer', 'production', 'installer'],
  finance: ['admin', 'finance'],
  reports: ['admin', 'sales', 'finance'],
  outsource: ['admin', 'production'],
  inventory: ['admin', 'production'],
  system: ['admin'],
  vehicleRead: ['admin', 'sales', 'production', 'installer', 'finance'],
  vehicleFleet: ['admin', 'production', 'installer', 'finance'],
  vehicleDrivers: ['admin', 'production', 'installer'],
  vehicleOperations: ['admin', 'production', 'installer'],
  vehicleExpenses: ['admin', 'production', 'installer', 'finance'],
  vehicleReports: ['admin', 'finance', 'production'],
  aerialRead: ['admin', 'sales', 'production', 'installer', 'finance'],
  aerialOperations: ['admin', 'production'],
  aerialFinance: ['admin', 'finance'],
  aerialFinanceOperations: ['admin', 'finance', 'production'],
  aiSales: ['admin', 'sales', 'finance'],
  aiReports: ['admin', 'sales', 'finance'],
}

/**
 * Permission fallbacks for custom roles. A resource-center key also becomes
 * permission-first whenever the authenticated profile has supplied the
 * server permission list, so an admin can revoke a built-in role's resource
 * access without leaving a stale navigation entry. These are page-entry
 * permissions only, never data-field or write authorization.
 */
export const ACCESS_PERMISSIONS: Partial<Record<AccessKey, readonly string[]>> = {
  product: ['product:read'],
  design: ['design_task:read'],
  designRead: ['design_task:read'],
  production: ['production_task:read'],
  productionRead: ['production_task:read'],
  installation: ['installation_task:read'],
  installationRead: ['installation_task:read'],
  boardRead: ['design_task:read', 'production_task:read', 'installation_task:read'],
  outsource: ['outsource:read'],
  inventory: ['inventory:read'],
  vehicleRead: ['vehicle:read'],
  vehicleFleet: ['vehicle:read'],
  vehicleDrivers: ['vehicle:read'],
  vehicleOperations: ['vehicle:read'],
  vehicleExpenses: ['vehicle:read'],
  vehicleReports: ['vehicle:read'],
  aerialRead: ['aerial:read'],
  aerialOperations: ['aerial:read'],
  aerialFinance: ['aerial:read'],
  aerialFinanceOperations: ['aerial:read'],
  finance: ['payment:read', 'expense:read', 'statement:read'],
  reports: ['report:read'],
}

const BUILTIN_ROLE_NAMES = new Set([
  'admin',
  'sales',
  'designer',
  'production',
  'installer',
  'finance',
])

const RESOURCE_CENTER_PERMISSION_FIRST_KEYS = new Set<AccessKey>([
  'vehicleRead', 'vehicleFleet', 'vehicleDrivers', 'vehicleOperations',
  'vehicleExpenses', 'vehicleReports', 'aerialRead', 'aerialOperations',
  'aerialFinance', 'aerialFinanceOperations',
])

/** Route-level visibility uses the exact same keys as navigation items. */
export const ROUTE_ACCESS: Record<string, AccessKey> = {
  Login: 'public',
  Home: 'authenticated',
  ProfileCenter: 'authenticated',

  CustomerList: 'sales',
  CustomerDetail: 'sales',
  ProductManage: 'product',
  QuoteList: 'sales',
  QuoteCreate: 'sales',
  QuoteEdit: 'sales',
  ContractList: 'sales',
  ContractDetail: 'sales',
  OrderList: 'orderRead',
  OrderRecycle: 'system',
  OrderEdit: 'sales',
  OrderDetail: 'orderRead',
  AcceptanceList: 'sales',
  AcceptanceDetail: 'sales',

  DesignTaskList: 'designRead',
  DesignTaskDetail: 'designRead',
  ProductionTaskList: 'productionRead',
  ProjectKanbanBoard: 'boardRead',
  ProductionTaskDetail: 'productionRead',
  InstallationTaskList: 'installationRead',
  InstallationTaskDetail: 'installationRead',

  ReceivablesView: 'finance',
  ExpenseList: 'finance',
  StatementList: 'finance',
  StatementDetail: 'finance',
  ProjectCostList: 'finance',
  ProjectCostDetail: 'finance',
  QuoteCostDetail: 'finance',
  CostDebtList: 'finance',

  DailyReport: 'reports',
  MonthlyReport: 'reports',
  AnomalyDashboard: 'aiReports',
  BusinessNarrativeReport: 'aiReports',

  OutsourceVendorList: 'outsource',
  OutsourceTaskList: 'outsource',
  OutsourceTaskRecycle: 'system',
  OutsourcePaymentList: 'finance',
  InventoryList: 'inventory',

  OperationLogList: 'system',
  BackupManage: 'system',
  AdminUserManage: 'system',
  AdminRoleManage: 'system',
  AdminSettings: 'system',
  AIProviderList: 'system',
  EmployeeList: 'system',
  DepartmentList: 'system',
  SalaryList: 'system',
  SalaryReport: 'system',
  SalaryRuleList: 'system',
  EmploymentHistoryList: 'system',
  LeaveRequestList: 'system',
  AttendanceRecordList: 'system',
  AttendanceRuleList: 'system',
  AIKnowledgeHealth: 'system',

  NotificationList: 'authenticated',
  Chat: 'authenticated',

  VehicleDashboard: 'vehicleRead',
  VehicleList: 'vehicleFleet',
  DriverList: 'vehicleDrivers',
  VehicleUseRequestList: 'vehicleRead',
  VehicleAgentDrafts: 'vehicleRead',
  VehicleDispatchList: 'vehicleOperations',
  VehicleTripRecordList: 'vehicleOperations',
  VehicleExpenseList: 'vehicleExpenses',
  VehicleIncidentList: 'vehicleRead',
  VehicleReports: 'vehicleReports',

  AerialDashboard: 'aerialRead',
  AerialLedgerList: 'aerialRead',
  AerialPersonnelExpenseList: 'aerialFinanceOperations',
  AerialPersonnelWageList: 'aerialFinance',
  AerialVehicleCostList: 'aerialFinanceOperations',
  AerialSafetyCheckList: 'aerialRead',
  AerialReports: 'aerialFinanceOperations',
  AerialVehicleList: 'aerialOperations',
  AerialPersonnelList: 'aerialOperations',
  AerialAgentDraftList: 'aerialFinanceOperations',
  AerialAttendanceList: 'aerialOperations',

  AIQuoteAssistant: 'aiSales',
  QuoteKnowledgeBase: 'aiSales',
  SitePhotoRecognition: 'aiSales',
  PaymentOCR: 'aiSales',

  CDRQuoteList: 'sales',
  CDRQuoteCreate: 'sales',
  CDRQuoteDetail: 'sales',
  CDRQuoteEdit: 'sales',
  PriceRuleList: 'sales',

  MobileHome: 'authenticated',
  MobileInstallation: 'authenticated',
  MobileProfile: 'authenticated',
  Forbidden: 'authenticated',
}

export const ROUTE_TITLES: Record<string, string> = {
  Home: '工作台',
  ProfileCenter: '个人中心',
  CustomerList: '客户管理',
  CustomerDetail: '客户详情',
  ProductManage: '产品 / 材质 / 工艺定价',
  QuoteList: '常规报价',
  QuoteCreate: '新建报价',
  QuoteEdit: '编辑报价',
  ContractList: '合同管理',
  ContractDetail: '合同详情',
  OrderList: '订单管理',
  OrderRecycle: '订单回收站',
  OrderEdit: '编辑订单',
  OrderDetail: '订单详情',
  AcceptanceList: '验收管理',
  AcceptanceDetail: '验收详情',
  DesignTaskList: '设计任务',
  DesignTaskDetail: '设计任务详情',
  ProductionTaskList: '制作任务',
  ProjectKanbanBoard: '项目看板',
  ProductionTaskDetail: '制作任务详情',
  InstallationTaskList: '安装任务',
  InstallationTaskDetail: '安装任务详情',
  ReceivablesView: '应收管理',
  ExpenseList: '支出管理',
  StatementList: '客户对账',
  StatementDetail: '对账详情',
  ProjectCostList: '项目成本',
  ProjectCostDetail: '项目成本详情',
  QuoteCostDetail: '报价成本详情',
  CostDebtList: '成本欠款',
  DailyReport: '销售日报',
  MonthlyReport: '销售月报',
  AnomalyDashboard: '异常提醒',
  BusinessNarrativeReport: '经营报告',
  OutsourceVendorList: '外协商',
  OutsourceTaskList: '外协任务',
  OutsourceTaskRecycle: '外协任务回收站',
  OutsourcePaymentList: '外协付款',
  InventoryList: '库存管理',
  OperationLogList: '操作日志',
  BackupManage: '备份管理',
  AdminUserManage: '用户管理',
  AdminRoleManage: '角色权限',
  AdminSettings: '系统设置',
  AIProviderList: 'AI 模型中心',
  AIKnowledgeHealth: 'AI 业务知识健康',
  NotificationList: '消息通知',
  Chat: '即时沟通',
  VehicleDashboard: '车辆看板',
  VehicleList: '车辆档案',
  DriverList: '司机管理',
  VehicleUseRequestList: '用车申请',
  VehicleAgentDrafts: '消息识别',
  VehicleDispatchList: '派车管理',
  VehicleTripRecordList: '出车台账',
  VehicleExpenseList: '车辆费用',
  VehicleIncidentList: '违章事故',
  VehicleReports: '车辆报表',
  AerialDashboard: '高空车经营看板',
  AerialLedgerList: '高空车出车台账',
  AerialPersonnelExpenseList: '高空车垫付报销',
  AerialPersonnelWageList: '高空车人员工资',
  AerialVehicleCostList: '高空车车辆费用',
  AerialSafetyCheckList: '高空车安全检查',
  AerialReports: '高空车经营报表',
  AerialVehicleList: '高空车车辆档案',
  AerialPersonnelList: '高空车人员管理',
  AerialAgentDraftList: '高空车 Agent 草稿',
  AerialAttendanceList: '高空车考勤表',
  AIQuoteAssistant: 'AI 报价助手',
  QuoteKnowledgeBase: '报价知识库',
  SitePhotoRecognition: '现场照片识别',
  PaymentOCR: '收款截图识别',
  CDRQuoteList: '智能报价',
  CDRQuoteCreate: '新建智能报价',
  CDRQuoteDetail: '智能报价详情',
  CDRQuoteEdit: '编辑智能报价',
  PriceRuleList: '定价规则',
  MobileHome: '移动工作台',
  MobileInstallation: '安装任务',
  MobileProfile: '我的',
  Forbidden: '无权访问',
}

export interface SmartToolItem {
  label: string
  path: string
  accessKey: AccessKey
}

export const SMART_TOOL_ITEMS: SmartToolItem[] = [
  { label: 'AI 报价助手', path: '/ai/quotes', accessKey: 'aiSales' },
  { label: '报价知识库', path: '/ai/knowledge', accessKey: 'aiSales' },
  { label: '现场照片识别', path: '/ai/site-photos', accessKey: 'aiSales' },
  { label: '收款截图识别', path: '/ai/payment-ocr', accessKey: 'aiSales' },
]

export function canAccess(
  accessKey: AccessKey,
  roles: readonly string[],
  permissions?: readonly string[],
): boolean {
  const requiredPermissions = ACCESS_PERMISSIONS[accessKey] || []

  // The profile's permission array is the source of truth for resource-center
  // entries once it has been loaded. Keeping the role fallback for an omitted
  // argument preserves pure route-matrix callers and the loading state before
  // /auth/me has completed.
  if (RESOURCE_CENTER_PERMISSION_FIRST_KEYS.has(accessKey) && permissions !== undefined) {
    return requiredPermissions.some(permission => permissions.includes(permission))
  }

  const allowedRoles = ACCESS_ROLES[accessKey]
  if (allowedRoles === null || allowedRoles.length === 0) return true
  if (allowedRoles.some(role => roles.includes(role))) return true

  // Non-resource legacy keys keep their established built-in role matrix.
  // Custom roles, however, have no role-name entry in ACCESS_ROLES and can be
  // admitted by the server-issued module permission.
  if (roles.some(role => BUILTIN_ROLE_NAMES.has(role))) return false
  return requiredPermissions.some(permission => (permissions || []).includes(permission))
}

export function canAccessRoute(
  routeName: unknown,
  roles: readonly string[],
  legacyRoles: readonly string[] = [],
  permissions?: readonly string[],
): boolean {
  if (legacyRoles.length > 0 && !legacyRoles.some(role => roles.includes(role))) {
    return false
  }
  if (typeof routeName !== 'string') return true
  const accessKey = ROUTE_ACCESS[routeName]
  return accessKey ? canAccess(accessKey, roles, permissions) : true
}

export function getRouteTitle(routeName: unknown): string {
  if (typeof routeName !== 'string') return 'AdCraft ERP'
  return ROUTE_TITLES[routeName] || 'AdCraft ERP'
}

export function filterSmartTools(
  roles: readonly string[],
  permissions?: readonly string[],
): SmartToolItem[] {
  return SMART_TOOL_ITEMS.filter(item => canAccess(item.accessKey, roles, permissions))
}
