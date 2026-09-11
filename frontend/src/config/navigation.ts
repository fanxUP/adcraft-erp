import { canAccess, type AccessKey } from './access'

export interface NavigationItem {
  label: string
  path?: string
  icon?: string
  accessKey?: AccessKey
  children?: NavigationItem[]
}

export const navigationItems: NavigationItem[] = [
  { label: '工作台', path: '/', icon: 'DataAnalysis', accessKey: 'authenticated' },
  { label: '项目看板', path: '/production-tasks/board', icon: 'Grid', accessKey: 'boardRead' },
  {
    label: '客户与销售',
    icon: 'User',
    accessKey: 'sales',
    children: [
      { label: '客户管理', path: '/customers', accessKey: 'customer' },
      { label: '常规报价', path: '/quotes', accessKey: 'quote' },
      { label: '智能报价', path: '/cdr/quotes', accessKey: 'cdrQuote' },
      { label: '定价规则', path: '/cdr/price-rules', accessKey: 'cdrPriceRules' },
      { label: '合同管理', path: '/contracts', accessKey: 'contract' },
      { label: '订单管理', path: '/orders', accessKey: 'orderRead' },
    ],
  },
  {
    label: '项目交付',
    icon: 'List',
    accessKey: 'authenticated',
    children: [
      { label: '设计任务', path: '/design-tasks', accessKey: 'designListRead' },
      { label: '制作任务', path: '/production-tasks', accessKey: 'productionListRead' },
      { label: '安装任务', path: '/installation-tasks', accessKey: 'installationListRead' },
      { label: '验收管理', path: '/acceptances', accessKey: 'acceptance' },
      { label: '外协任务', path: '/outsource/tasks', accessKey: 'outsourceTask' },
      { label: '外协商', path: '/outsource/vendors', accessKey: 'outsourceVendor' },
      { label: '库存管理', path: '/inventory', accessKey: 'inventory' },
      { label: '产品/材质/工艺定价', path: '/products', accessKey: 'product' },
    ],
  },
  {
    label: '财务中心',
    icon: 'Money',
    accessKey: 'finance',
    children: [
      { label: '应收管理', path: '/receivables', accessKey: 'payment' },
      { label: '支出管理', path: '/expenses', accessKey: 'expense' },
      { label: '项目成本', path: '/project-costs', accessKey: 'projectCost' },
      { label: '成本欠款', path: '/cost-debts', accessKey: 'costDebt' },
      { label: '外协付款', path: '/outsource/payments', accessKey: 'outsourcePayment' },
      { label: '客户对账', path: '/statements', accessKey: 'statement' },
    ],
  },
  {
    label: '人事管理',
    icon: 'UserFilled',
    accessKey: 'system',
    children: [
      { label: '员工管理', path: '/employees', accessKey: 'system' },
      { label: '考勤记录', path: '/attendance/records', accessKey: 'system' },
      { label: '考勤规则', path: '/attendance/rules', accessKey: 'system' },
      { label: '部门管理', path: '/departments', accessKey: 'system' },
      { label: '工资管理', path: '/salaries', accessKey: 'system' },
      { label: '工资报表', path: '/salary-report', accessKey: 'system' },
      { label: '工资规则', path: '/salary-rules', accessKey: 'system' },
      { label: '员工履历', path: '/employment-histories', accessKey: 'system' },
      { label: '请假审批', path: '/leaves', accessKey: 'system' },
    ],
  },
  {
    label: '资源中心',
    icon: 'Van',
    accessKey: 'resourceCenter',
    children: [
      {
        label: '公司车辆',
        icon: 'Van',
        accessKey: 'resourceCenter',
        children: [
          { label: '车辆看板', path: '/vehicle-dashboard', accessKey: 'vehicleRead' },
          { label: '用车申请', path: '/vehicle-use-requests', accessKey: 'vehicleRead' },
          { label: '派车管理', path: '/vehicle-dispatches', accessKey: 'vehicleOperations' },
          { label: '出车台账', path: '/vehicle-trip-records', accessKey: 'vehicleOperations' },
          { label: '车辆费用', path: '/vehicle-expenses', accessKey: 'vehicleExpenses' },
          { label: '违章事故', path: '/vehicle-incidents', accessKey: 'vehicleRead' },
          { label: '车辆报表', path: '/vehicle-reports', accessKey: 'vehicleReports' },
          { label: '车辆档案', path: '/vehicles', accessKey: 'vehicleFleet' },
          { label: '司机管理', path: '/vehicle-drivers', accessKey: 'vehicleDrivers' },
          { label: '消息识别', path: '/vehicle-agent-drafts', accessKey: 'vehicleRead' },
        ],
      },
      {
        label: '高空作业车',
        icon: 'Platform',
        accessKey: 'resourceCenter',
        children: [
          { label: '经营看板', path: '/aerial-dashboard', accessKey: 'aerialRead' },
          { label: '出车台账', path: '/aerial-ledgers', accessKey: 'aerialRead' },
          { label: '安全检查', path: '/aerial-safety-checks', accessKey: 'aerialRead' },
          { label: '垫付报销', path: '/aerial-personnel-expenses', accessKey: 'aerialFinanceOperations' },
          { label: '人员工资', path: '/aerial-personnel-wages', accessKey: 'aerialFinance' },
          { label: '车辆费用', path: '/aerial-vehicle-costs', accessKey: 'aerialFinanceOperations' },
          { label: '经营报表', path: '/aerial-reports', accessKey: 'aerialFinanceOperations' },
          { label: '车辆档案', path: '/aerial-vehicles', accessKey: 'aerialOperations' },
          { label: '人员管理', path: '/aerial-personnel', accessKey: 'aerialOperations' },
          { label: '考勤表', path: '/aerial-attendance', accessKey: 'aerialOperations' },
          { label: 'Agent 草稿', path: '/aerial-agent-drafts', accessKey: 'aerialFinanceOperations' },
        ],
      },
    ],
  },
  {
    label: '经营分析',
    icon: 'TrendCharts',
    accessKey: 'reports',
    children: [
      { label: '销售日报', path: '/reports/daily', accessKey: 'reports' },
      { label: '销售月报', path: '/reports/monthly', accessKey: 'reports' },
      { label: '异常提醒', path: '/ai/anomalies', accessKey: 'aiAnomaly' },
      { label: '经营报告', path: '/ai/reports', accessKey: 'aiReports' },
    ],
  },
  {
    label: '系统管理',
    icon: 'Tools',
    accessKey: 'system',
    children: [
      { label: '用户管理', path: '/admin/users', accessKey: 'system' },
      { label: '角色权限', path: '/admin/roles', accessKey: 'system' },
      { label: '系统设置', path: '/admin/settings', accessKey: 'system' },
      { label: '操作日志', path: '/operation-logs', accessKey: 'system' },
      { label: '备份管理', path: '/backups', accessKey: 'system' },
      { label: 'AI 模型中心', path: '/admin/ai/providers', accessKey: 'system' },
      { label: 'AI 业务知识健康', path: '/admin/ai/knowledge-health', accessKey: 'system' },
    ],
  },
]

export function filterNavigation(
  items: NavigationItem[],
  roles: string[],
  permissions?: string[],
): NavigationItem[] {
  return items.flatMap(item => {
    if (!canAccess(item.accessKey || 'authenticated', roles, permissions)) return []
    const children = item.children
      ? filterNavigation(item.children, roles, permissions)
      : undefined
    if (item.children && !children?.length) return []
    return [{ ...item, children }]
  })
}
