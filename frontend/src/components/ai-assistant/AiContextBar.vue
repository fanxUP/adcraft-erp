<template>
  <div v-if="hasContext" class="ai-context-bar">
    <div class="ai-context-dot" />
    <el-icon :size="13"><InfoFilled /></el-icon>
    <span class="ai-context-text">{{ contextText }}</span>
    <el-button text size="small" class="ai-context-clear" @click="store.setPageContext({})">
      <el-icon :size="11"><Close /></el-icon>
    </el-button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAiAssistantStore } from '@/stores/aiAssistantStore'

const store = useAiAssistantStore()

const hasContext = computed(() => {
  const ctx = store.pageContext
  return !!(ctx.page || ctx.customer_name || ctx.order_no || ctx.quote_no || ctx.business_type)
})

const contextText = computed(() => {
  const ctx = store.pageContext
  const parts: string[] = []
  if (ctx.page) parts.push(pageLabel(ctx.page))
  if (ctx.customer_name) parts.push(`客户: ${ctx.customer_name}`)
  if (ctx.order_no) parts.push(`订单: ${ctx.order_no}`)
  if (ctx.quote_no) parts.push(`报价: ${ctx.quote_no}`)
  if (ctx.project_name) parts.push(`项目: ${ctx.project_name}`)
  return parts.join(' · ') || '当前页面'
})

const pageLabels: Record<string, string> = {
  dashboard: '驾驶舱',
  customer_list: '客户列表',
  customer_detail: '客户详情',
  order_list: '订单列表',
  order_detail: '订单详情',
  order_recycle: '订单回收站',
  quote_list: '报价列表',
  quote_create: '新建报价',
  quote_edit: '编辑报价',
  quote_detail: '报价详情',
  cdr_quote_list: '智能报价列表',
  cdr_quote_create: '新建智能报价',
  cdr_quote_detail: '智能报价详情',
  cdr_quote_edit: '编辑智能报价',
  price_rules: '定价规则',
  customer_agreements: '客户协议价',
  contract_list: '合同列表',
  framework_contract_list: '框架合同列表',
  framework_contract_detail: '框架合同详情',
  acceptance_list: '验收列表',
  acceptance_detail: '验收详情',
  design_task_list: '设计任务列表',
  design_task_detail: '设计任务详情',
  production_task_list: '制作任务列表',
  production_task_board: '制作看板',
  production_task_detail: '制作任务详情',
  installation_task_list: '安装任务列表',
  installation_task_detail: '安装任务详情',
  product_manage: '产品管理',
  material_process: '材质工艺',
  receivables: '应收管理',
  expenses: '支出管理',
  statement_list: '对账单列表',
  statement_detail: '对账单详情',
  project_cost_list: '项目成本列表',
  project_cost_detail: '项目成本详情',
  quote_cost_detail: '报价成本详情',
  cost_debt_list: '成本欠款列表',
  outsource_vendors: '外协商列表',
  outsource_tasks: '外协任务列表',
  outsource_task_recycle: '外协任务回收站',
  outsource_payments: '外协付款',
  inventory: '库存管理',
  daily_report: '销售日报',
  monthly_report: '销售月报',
  notifications: '消息中心',
  chat: '即时通讯',
  admin_users: '用户管理',
  admin_roles: '角色权限',
  admin_settings: '系统设置',
  ai_providers: 'AI 模型中心',
  operation_logs: '操作日志',
  backups: '备份管理',
  vehicle_dashboard: '车辆看板',
  vehicle_list: '车辆档案',
  driver_list: '司机管理',
  vehicle_use_requests: '用车申请',
  vehicle_agent_drafts: '车辆消息识别',
  vehicle_dispatches: '派车管理',
  vehicle_trip_records: '出车收车台账',
  vehicle_expenses: '车辆费用',
  vehicle_insurance: '保险年检',
  vehicle_incidents: '违章事故',
  vehicle_reports: '车辆报表',
  aerial_dashboard: '高空车看板',
  aerial_ledgers: '高空车出车台账',
  aerial_personnel_expenses: '高空车垫付报销',
  aerial_personnel_wages: '高空车人员工资',
  aerial_vehicle_costs: '高空车车辆费用',
  aerial_safety_checks: '高空车安全检查',
  aerial_reports: '高空车统计报表',
  aerial_vehicles: '高空车档案',
  aerial_personnel: '高空车人员管理',
  aerial_agent_drafts: '高空车Agent草稿',
  anomaly_dashboard: '智能异常提醒',
  ai_quote_assistant: 'AI 报价助手',
  quote_knowledge_base: '报价知识库',
  business_narrative_report: '智能经营报告',
  site_photo_recognition: '现场照片识别',
  payment_ocr: '收款截图识别',
}

function pageLabel(key: string): string {
  return pageLabels[key] || key
}
</script>

<style scoped>
.ai-context-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 16px;
  background: linear-gradient(90deg, rgba(245,108,108,0.06), rgba(245,108,108,0.02));
  border-bottom: 1px solid var(--ai-border, #2a2a4a);
  font-size: 12px;
  color: var(--ai-text-secondary, #8888aa);
  flex-shrink: 0;
}
.ai-context-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--ai-accent, #f56c6c);
  flex-shrink: 0;
}
.ai-context-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ai-context-clear {
  color: var(--ai-text-muted, #666688);
  opacity: 0.6;
  transition: opacity 0.2s;
}
.ai-context-clear:hover {
  opacity: 1;
  color: var(--ai-text-secondary);
}
</style>
