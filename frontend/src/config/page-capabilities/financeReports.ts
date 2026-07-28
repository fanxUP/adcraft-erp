import type { PageCapabilityMap } from './types'

export const financeReportCapabilities: PageCapabilityMap = {
  receivables: {
    title: '应收管理',
    purpose: '查看订单应收、已收、欠款并登记客户收款',
    workflowStage: 'receivables',
    availableActions: ['查询客户欠款', '查看订单应收', '登记收款'],
    quickActions: [{ label: '欠款客户', prompt: '有哪些欠款客户' }],
  },
  expenses: {
    title: '支出管理',
    purpose: '登记和查询经营及项目支出',
    workflowStage: 'finance',
    availableActions: ['查询支出', '登记支出', '查看支出详情'],
  },
  statement_list: {
    title: '对账单列表',
    purpose: '生成、查询和跟踪客户对账单',
    workflowStage: 'statement',
    availableActions: ['查询对账单', '生成对账单', '查看确认状态'],
  },
  statement_detail: {
    title: '对账单详情',
    purpose: '核对客户订单、收款和欠款明细',
    workflowStage: 'statement',
    availableActions: ['核对明细', '更新对账状态', '打印对账单'],
  },
  project_cost_list: {
    title: '项目成本列表',
    purpose: '查看订单收入、直接成本和利润汇总',
    workflowStage: 'cost',
    availableActions: ['查询项目成本', '查看利润', '进入成本详情'],
  },
  project_cost_detail: {
    title: '项目成本详情',
    purpose: '核对订单材料、外协、人工和其他成本',
    workflowStage: 'cost',
    availableActions: ['查看成本构成', '登记成本', '核对利润'],
  },
  quote_cost_detail: {
    title: '报价成本详情',
    purpose: '评估报价项目的预计成本和利润空间',
    workflowStage: 'cost',
    availableActions: ['查看预计成本', '检查利润率', '返回报价'],
  },
  cost_debt_list: {
    title: '成本欠款列表',
    purpose: '查看项目相关供应商和外协未付款项',
    workflowStage: 'payables',
    availableActions: ['查询未付款', '筛选供应商', '查看关联项目'],
  },
  outsource_payments: {
    title: '外协付款',
    purpose: '查询外协应付和付款记录并登记付款',
    workflowStage: 'payables',
    availableActions: ['查询外协应付', '登记付款', '查看付款记录'],
  },
  daily_report: {
    title: '销售日报',
    purpose: '查看当日新增订单、收款和业务完成情况',
    workflowStage: 'report',
    availableActions: ['选择日期', '查看日报', '分析异常'],
  },
  monthly_report: {
    title: '销售月报',
    purpose: '查看月度订单、收款、欠款和业务趋势',
    workflowStage: 'report',
    availableActions: ['选择月份', '查看月报', '分析趋势'],
  },
}
