export interface NavigationItem {
  label: string
  path?: string
  icon?: string
  roles?: string[]
  children?: NavigationItem[]
}

const SALES_ROLES = ['admin', 'sales']
const DELIVERY_ROLES = ['admin', 'sales', 'designer', 'production', 'installer']
const FINANCE_ROLES = ['admin', 'finance']

export const navigationItems: NavigationItem[] = [
  { label: '工作台', path: '/', icon: 'DataAnalysis' },
  {
    label: '客户与销售',
    icon: 'User',
    roles: SALES_ROLES,
    children: [
      { label: '客户管理', path: '/customers' },
      { label: '常规报价', path: '/quotes' },
      { label: '智能报价', path: '/cdr/quotes' },
      { label: '定价规则', path: '/cdr/price-rules' },
      { label: '客户协议价', path: '/cdr/customer-agreements' },
      { label: '合同管理', path: '/contracts' },
      { label: '订单管理', path: '/orders' },
    ],
  },
  {
    label: '项目交付',
    icon: 'List',
    roles: DELIVERY_ROLES,
    children: [
      { label: '设计任务', path: '/design-tasks', roles: ['admin', 'designer'] },
      { label: '制作任务', path: '/production-tasks', roles: ['admin', 'production'] },
      { label: '项目看板', path: '/production-tasks/board', roles: ['admin', 'production'] },
      { label: '安装任务', path: '/installation-tasks', roles: ['admin', 'installer'] },
      { label: '验收管理', path: '/acceptances', roles: SALES_ROLES },
      { label: '外协任务', path: '/outsource/tasks', roles: ['admin', 'production'] },
      { label: '外协商', path: '/outsource/vendors', roles: ['admin', 'production'] },
      { label: '库存管理', path: '/inventory', roles: ['admin', 'production'] },
      { label: '产品/材质/工艺定价', path: '/products', roles: ['admin', 'designer', 'production'] },
    ],
  },
  {
    label: '财务中心',
    icon: 'Money',
    roles: FINANCE_ROLES,
    children: [
      { label: '应收管理', path: '/receivables' },
      { label: '支出管理', path: '/expenses' },
      { label: '项目成本', path: '/project-costs' },
      { label: '成本欠款', path: '/cost-debts' },
      { label: '外协付款', path: '/outsource/payments' },
      { label: '客户对账', path: '/statements' },
    ],
  },
  {
    label: '人事管理',
    icon: 'UserFilled',
    roles: ['admin'],
    children: [
      { label: '员工管理', path: '/employees' },
      { label: '考勤记录', path: '/attendance/records' },
      { label: '考勤规则', path: '/attendance/rules' },
      { label: "部门管理", path: "/departments" },
      { label: "工资管理", path: "/salaries" },
      { label: "工资规则", path: "/salary-rules" },
      { label: "员工履历", path: "/employment-histories" },
      { label: "请假审批", path: "/leaves" },
    ],
  },
  {
    label: '资源中心',
    icon: 'Van',
    children: [
      {
        label: '公司车辆',
        icon: 'Van',
        children: [
          { label: '车辆看板', path: '/vehicle-dashboard' },
          { label: '用车申请', path: '/vehicle-use-requests' },
          { label: '派车管理', path: '/vehicle-dispatches', roles: ['admin', 'production', 'installer'] },
          { label: '出车台账', path: '/vehicle-trip-records', roles: ['admin', 'production', 'installer'] },
          { label: '车辆费用', path: '/vehicle-expenses', roles: ['admin', 'production', 'installer', 'finance'] },
          { label: '保险年检', path: '/vehicle-insurance', roles: FINANCE_ROLES },
          { label: '违章事故', path: '/vehicle-incidents' },
          { label: '车辆报表', path: '/vehicle-reports', roles: ['admin', 'finance', 'production'] },
          { label: '车辆档案', path: '/vehicles', roles: ['admin', 'production', 'installer'] },
          { label: '司机管理', path: '/vehicle-drivers', roles: ['admin', 'production', 'installer'] },
          { label: '消息识别', path: '/vehicle-agent-drafts' },
        ],
      },
      {
        label: '高空作业车',
        icon: 'Platform',
        children: [
          { label: '经营看板', path: '/aerial-dashboard' },
          { label: '出车台账', path: '/aerial-ledgers' },
          { label: '安全检查', path: '/aerial-safety-checks' },
          { label: '垫付报销', path: '/aerial-personnel-expenses', roles: ['admin', 'finance', 'production'] },
          { label: '人员工资', path: '/aerial-personnel-wages', roles: FINANCE_ROLES },
          { label: '车辆费用', path: '/aerial-vehicle-costs', roles: ['admin', 'finance', 'production'] },
          { label: '经营报表', path: '/aerial-reports', roles: ['admin', 'finance', 'production'] },
          { label: '车辆档案', path: '/aerial-vehicles', roles: ['admin', 'production'] },
          { label: '人员管理', path: '/aerial-personnel', roles: ['admin', 'production'] },
          { label: '考勤表', path: '/aerial-attendance', roles: ['admin', 'production'] },
          { label: 'Agent 草稿', path: '/aerial-agent-drafts', roles: ['admin', 'finance', 'production'] },
        ],
      },
    ],
  },
  {
    label: '经营分析',
    icon: 'TrendCharts',
    roles: ['admin', 'sales', 'finance'],
    children: [
      { label: '销售日报', path: '/reports/daily' },
      { label: '销售月报', path: '/reports/monthly' },
      { label: '异常提醒', path: '/ai/anomalies' },
      { label: '经营报告', path: '/ai/reports' },
    ],
  },
  {
    label: '系统管理',
    icon: 'Tools',
    roles: ['admin'],
    children: [
      { label: '用户管理', path: '/admin/users' },
      { label: '角色权限', path: '/admin/roles' },
      { label: '系统设置', path: '/admin/settings' },
      { label: '操作日志', path: '/operation-logs' },
      { label: '备份管理', path: '/backups' },
      { label: 'AI 模型中心', path: '/admin/ai/providers' },
      { label: 'AI 业务知识健康', path: '/admin/ai/knowledge-health' },
    ],
  },
]

export function filterNavigation(
  items: NavigationItem[],
  roles: string[],
): NavigationItem[] {
  return items.flatMap(item => {
    if (item.roles && !item.roles.some(role => roles.includes(role))) return []
    const children = item.children
      ? filterNavigation(item.children, roles)
      : undefined
    if (item.children && !children?.length) return []
    return [{ ...item, children }]
  })
}
