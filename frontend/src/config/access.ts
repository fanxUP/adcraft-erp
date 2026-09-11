/**
 * Frontend page visibility rules.
 *
 * These rules keep the shell and router consistent, but they are not the
 * security boundary. API permissions and object-state checks on the server
 * remain authoritative; this file only mirrors server-issued page entry
 * capabilities.
 */

export type AccessKey =
  | 'public'
  | 'authenticated'
  | 'sales'
  | 'customer'
  | 'quote'
  | 'quoteCreate'
  | 'quoteUpdate'
  | 'contract'
  | 'orderRead'
  | 'orderManage'
  | 'orderDelete'
  | 'acceptance'
  | 'cdrQuote'
  | 'cdrPriceRules'
  | 'product'
  | 'design'
  | 'designRead'
  | 'designListRead'
  | 'production'
  | 'productionRead'
  | 'productionListRead'
  | 'installation'
  | 'installationRead'
  | 'installationListRead'
  | 'boardRead'
  | 'taskCompletion'
  | 'finance'
  | 'payment'
  | 'expense'
  | 'statement'
  | 'projectCost'
  | 'costDebt'
  | 'outsourcePayment'
  | 'reports'
  | 'outsourceVendor'
  | 'outsourceTask'
  | 'outsourceTaskRecycle'
  | 'inventory'
  | 'resourceCenter'
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
  | 'aiQuote'
  | 'aiKnowledge'
  | 'aiAnomaly'
  | 'aiReports'
  | 'aiSitePhoto'
  | 'aiPaymentOcr'

type AccessRoles = readonly string[] | null

export type PermissionRequirement =
  | readonly string[]
  | { allOf?: readonly string[]; anyOf?: readonly string[] }

function isPermissionList(requirement: PermissionRequirement): requirement is readonly string[] {
  return Array.isArray(requirement)
}

/**
 * Role groups are deliberately about page visibility only. They do not grant
 * a write action and must not be used as a substitute for backend authz.
 */
export const ACCESS_ROLES: Record<AccessKey, AccessRoles> = {
  public: [],
  authenticated: null,
  sales: ['admin', 'sales'],
  customer: ['admin', 'sales'],
  quote: ['admin', 'sales'],
  quoteCreate: ['admin', 'sales'],
  quoteUpdate: ['admin', 'sales'],
  contract: ['admin', 'sales'],
  orderRead: ['admin', 'sales', 'finance'],
  orderManage: ['admin', 'sales'],
  orderDelete: ['admin'],
  acceptance: ['admin', 'sales'],
  cdrQuote: ['admin', 'sales'],
  cdrPriceRules: ['admin', 'sales'],
  product: ['admin', 'designer', 'production'],
  design: ['admin', 'designer'],
  designRead: ['admin', 'sales', 'designer', 'production', 'installer'],
  designListRead: ['admin', 'sales'],
  production: ['admin', 'production'],
  productionRead: ['admin', 'sales', 'designer', 'production', 'installer'],
  productionListRead: ['admin', 'sales'],
  installation: ['admin', 'installer'],
  installationRead: ['admin', 'sales', 'designer', 'production', 'installer'],
  installationListRead: ['admin', 'sales'],
  boardRead: ['admin', 'sales', 'designer', 'production', 'installer'],
  taskCompletion: ['admin', 'sales', 'designer', 'production', 'installer'],
  finance: ['admin', 'finance'],
  payment: ['admin', 'finance'],
  expense: ['admin', 'finance'],
  statement: ['admin', 'finance'],
  projectCost: ['admin', 'finance'],
  costDebt: ['admin', 'finance'],
  outsourcePayment: ['admin', 'finance'],
  reports: ['admin', 'sales', 'finance'],
  outsourceVendor: ['admin', 'finance', 'outsource_manager'],
  outsourceTask: ['admin', 'finance', 'outsource_manager'],
  outsourceTaskRecycle: ['admin', 'outsource_manager'],
  inventory: ['admin', 'production'],
  resourceCenter: ['admin', 'sales', 'finance', 'resource_manager'],
  system: ['admin'],
  vehicleRead: ['admin', 'sales', 'finance', 'resource_manager'],
  vehicleFleet: ['admin', 'finance', 'resource_manager'],
  vehicleDrivers: ['admin', 'resource_manager'],
  vehicleOperations: ['admin', 'resource_manager'],
  vehicleExpenses: ['admin', 'finance', 'resource_manager'],
  vehicleReports: ['admin', 'finance', 'resource_manager'],
  aerialRead: ['admin', 'sales', 'finance', 'resource_manager'],
  aerialOperations: ['admin', 'resource_manager'],
  aerialFinance: ['admin', 'finance', 'resource_manager'],
  aerialFinanceOperations: ['admin', 'finance', 'resource_manager'],
  aiQuote: ['admin', 'sales', 'finance'],
  aiKnowledge: ['admin', 'sales', 'finance'],
  aiAnomaly: ['admin', 'sales', 'finance'],
  aiReports: ['admin', 'sales', 'finance'],
  // Site-photo and payment-OCR APIs currently share the historical
  // ai_quote:read backend capability. Keep the page keys separate so a
  // future backend split does not require another broad any-of grant.
  aiSitePhoto: ['admin', 'sales', 'finance'],
  aiPaymentOcr: ['admin', 'sales', 'finance'],
}

/**
 * Permission requirements for custom roles.  The profile from /auth/me is the
 * source of truth after it has loaded; these are page-entry requirements only,
 * never data-field or write authorization.
 */
export const ACCESS_PERMISSIONS: Partial<Record<AccessKey, PermissionRequirement>> = {
  sales: { anyOf: ['customer:read', 'quote:read', 'contract:read', 'order:read'] },
  customer: ['customer:read'],
  quote: ['quote:read'],
  quoteCreate: ['quote:create'],
  quoteUpdate: ['quote:update'],
  contract: ['contract:read'],
  orderRead: ['order:read'],
  orderManage: ['order:update'],
  orderDelete: ['order:delete'],
  acceptance: ['acceptance:read'],
  cdrQuote: ['cdr_quote:read'],
  cdrPriceRules: ['cdr_rule_set:publish'],
  product: ['product:read'],
  design: ['design_task:read'],
  designRead: ['design_task:read'],
  designListRead: ['design_task:list'],
  production: ['production_task:read'],
  productionRead: ['production_task:read'],
  productionListRead: ['production_task:list'],
  installation: ['installation_task:read'],
  installationRead: ['installation_task:read'],
  installationListRead: ['installation_task:list'],
  boardRead: { anyOf: ['design_task:read', 'production_task:read', 'installation_task:read'] },
  taskCompletion: ['task_completion:read'],
  outsourceVendor: { allOf: ['outsource_center:read', 'outsource_vendor:read'] },
  outsourceTask: { allOf: ['outsource_center:read', 'outsource_task:read'] },
  outsourceTaskRecycle: { allOf: ['outsource_center:read', 'outsource_task:delete'] },
  inventory: ['inventory:read'],
  resourceCenter: ['resource_center:read'],
  vehicleRead: { allOf: ['resource_center:read', 'vehicle:read'] },
  vehicleFleet: { allOf: ['resource_center:read', 'vehicle:read'] },
  vehicleDrivers: { allOf: ['resource_center:read', 'vehicle:read'] },
  vehicleOperations: { allOf: ['resource_center:read', 'vehicle:read'] },
  vehicleExpenses: { allOf: ['resource_center:read', 'vehicle:read'] },
  vehicleReports: { allOf: ['resource_center:read', 'vehicle:read'] },
  aerialRead: { allOf: ['resource_center:read', 'aerial:read'] },
  aerialOperations: { allOf: ['resource_center:read', 'aerial:read'] },
  aerialFinance: { allOf: ['resource_center:read', 'aerial:read'] },
  aerialFinanceOperations: { allOf: ['resource_center:read', 'aerial:read'] },
  finance: { anyOf: ['payment:read', 'expense:read', 'statement:read', 'outsource_payment:read', 'finance:view_cost'] },
  payment: ['payment:read'],
  expense: ['expense:read'],
  statement: ['statement:read'],
  projectCost: { anyOf: ['expense:read', 'finance:view_cost'] },
  costDebt: { anyOf: ['expense:read', 'finance:view_cost'] },
  outsourcePayment: ['outsource_payment:read'],
  reports: { anyOf: ['report:read', 'report:view_financial'] },
  system: ['system:super_admin'],
  aiQuote: ['ai_quote:read'],
  aiKnowledge: { allOf: ['ai_knowledge:read', 'order:view_price'] },
  aiAnomaly: ['ai_anomaly:read'],
  aiReports: { allOf: ['ai_report:read', 'report:view_financial'] },
  aiSitePhoto: ['ai_quote:read'],
  aiPaymentOcr: ['ai_quote:read'],
}

const BUILTIN_ROLE_NAMES = new Set([
  'admin',
  'sales',
  'designer',
  'production',
  'installer',
  'finance',
  'resource_manager',
  'outsource_manager',
])

/** Route-level visibility uses the exact same keys as navigation items. */
export const ROUTE_ACCESS: Record<string, AccessKey> = {
  Login: 'public',
  Home: 'authenticated',
  ProfileCenter: 'authenticated',

  CustomerList: 'customer',
  CustomerDetail: 'customer',
  ProductManage: 'product',
  QuoteList: 'quote',
  QuoteCreate: 'quoteCreate',
  QuoteEdit: 'quoteUpdate',
  ContractList: 'contract',
  ContractDetail: 'contract',
  OrderList: 'orderRead',
  OrderRecycle: 'orderDelete',
  OrderEdit: 'orderManage',
  OrderDetail: 'orderRead',
  AcceptanceList: 'acceptance',
  AcceptanceDetail: 'acceptance',

  DesignTaskList: 'designListRead',
  DesignTaskDetail: 'designRead',
  ProductionTaskList: 'productionListRead',
  ProjectKanbanBoard: 'boardRead',
  ProductionTaskDetail: 'productionRead',
  InstallationTaskList: 'installationListRead',
  InstallationTaskDetail: 'installationRead',
  CompletedProjectDetail: 'taskCompletion',

  ReceivablesView: 'payment',
  ExpenseList: 'expense',
  StatementList: 'statement',
  StatementDetail: 'statement',
  ProjectCostList: 'projectCost',
  ProjectCostDetail: 'projectCost',
  QuoteCostDetail: 'projectCost',
  CostDebtList: 'costDebt',

  DailyReport: 'reports',
  MonthlyReport: 'reports',
  AnomalyDashboard: 'aiAnomaly',
  BusinessNarrativeReport: 'aiReports',

  OutsourceVendorList: 'outsourceVendor',
  OutsourceTaskList: 'outsourceTask',
  OutsourceTaskRecycle: 'outsourceTaskRecycle',
  OutsourcePaymentList: 'outsourcePayment',
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

  AIQuoteAssistant: 'aiQuote',
  QuoteKnowledgeBase: 'aiKnowledge',
  SitePhotoRecognition: 'aiSitePhoto',
  PaymentOCR: 'aiPaymentOcr',

  CDRQuoteList: 'cdrQuote',
  CDRQuoteCreate: 'cdrQuote',
  CDRQuoteDetail: 'cdrQuote',
  CDRQuoteEdit: 'cdrQuote',
  PriceRuleList: 'cdrPriceRules',

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
  CompletedProjectDetail: '完成项目详情',
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
  { label: 'AI 报价助手', path: '/ai/quotes', accessKey: 'aiQuote' },
  { label: '报价知识库', path: '/ai/knowledge', accessKey: 'aiKnowledge' },
  { label: '现场照片识别', path: '/ai/site-photos', accessKey: 'aiSitePhoto' },
  { label: '收款截图识别', path: '/ai/payment-ocr', accessKey: 'aiPaymentOcr' },
]

export function canAccess(
  accessKey: AccessKey,
  roles: readonly string[],
  permissions?: readonly string[],
): boolean {
  const requirement = ACCESS_PERMISSIONS[accessKey]

  // Once /auth/me has supplied a permission list, every mapped page is
  // permission-first.  Role names remain only as a compatibility fallback for
  // pure callers that intentionally omit the server profile.
  if (requirement && permissions !== undefined) {
    if (permissions.includes('system:super_admin')) return true
    if (isPermissionList(requirement)) {
      return requirement.every(permission => permissions.includes(permission))
    }
    const allOf = requirement.allOf || []
    const anyOf = requirement.anyOf || []
    return allOf.every(permission => permissions.includes(permission))
      && (anyOf.length === 0 || anyOf.some(permission => permissions.includes(permission)))
  }

  const allowedRoles = ACCESS_ROLES[accessKey]
  if (allowedRoles === null || allowedRoles.length === 0) return true
  if (allowedRoles.some(role => roles.includes(role))) return true

  // Other legacy keys keep their established built-in role matrix.
  // Custom roles, however, have no role-name entry in ACCESS_ROLES and can be
  // admitted by the server-issued module permission.
  if (roles.some(role => BUILTIN_ROLE_NAMES.has(role))) return false
  if (!requirement) return false
  if (isPermissionList(requirement)) {
    return requirement.every(permission => (permissions || []).includes(permission))
  }
  const allOf = requirement.allOf || []
  const anyOf = requirement.anyOf || []
  return allOf.every(permission => (permissions || []).includes(permission))
    && (anyOf.length === 0 || anyOf.some(permission => (permissions || []).includes(permission)))
}

export function canAccessRoute(
  routeName: unknown,
  roles: readonly string[],
  legacyRoles: readonly string[] = [],
  permissions?: readonly string[],
): boolean {
  if (permissions === undefined && legacyRoles.length > 0 && !legacyRoles.some(role => roles.includes(role))) {
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
