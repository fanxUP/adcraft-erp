import {
  getPageCapability,
  getPageQuickActions,
} from './page-capabilities'

export interface PageContext {
  page?: string
  page_title?: string
  page_purpose?: string
  business_type?: string
  business_id?: string
  workflow_stage?: string
  available_actions?: string[]
}

const pageContexts: Record<string, PageContext> = {
  Home: { page: 'dashboard' },
  CustomerList: { page: 'customer_list', business_type: 'customer' },
  CustomerDetail: { page: 'customer_detail', business_type: 'customer' },
  OrderList: { page: 'order_list', business_type: 'order' },
  OrderRecycle: { page: 'order_recycle', business_type: 'order' },
  OrderDetail: { page: 'order_detail', business_type: 'order' },
  QuoteList: { page: 'quote_list', business_type: 'quote' },
  QuoteCreate: { page: 'quote_create', business_type: 'quote' },
  QuoteEdit: { page: 'quote_edit', business_type: 'quote' },
  CDRQuoteList: { page: 'cdr_quote_list', business_type: 'quote' },
  CDRQuoteCreate: { page: 'cdr_quote_create', business_type: 'quote' },
  CDRQuoteDetail: { page: 'cdr_quote_detail', business_type: 'quote' },
  CDRQuoteEdit: { page: 'cdr_quote_edit', business_type: 'quote' },
  PriceRuleList: { page: 'price_rules', business_type: 'price' },
  CustomerAgreementList: { page: 'customer_agreements', business_type: 'price' },
  ContractList: { page: 'contract_list', business_type: 'contract' },
  FrameworkContractList: { page: 'framework_contract_list', business_type: 'contract' },
  FrameworkContractDetail: { page: 'framework_contract_detail', business_type: 'contract' },
  AcceptanceList: { page: 'acceptance_list', business_type: 'acceptance' },
  AcceptanceDetail: { page: 'acceptance_detail', business_type: 'acceptance' },
  DesignTaskList: { page: 'design_task_list', business_type: 'design_task' },
  DesignTaskDetail: { page: 'design_task_detail', business_type: 'design_task' },
  ProductionTaskList: { page: 'production_task_list', business_type: 'production_task' },
  ProductionTaskBoard: { page: 'production_task_board', business_type: 'production_task' },
  ProductionTaskDetail: { page: 'production_task_detail', business_type: 'production_task' },
  InstallationTaskList: { page: 'installation_task_list', business_type: 'installation_task' },
  InstallationTaskDetail: { page: 'installation_task_detail', business_type: 'installation_task' },
  ProductManage: { page: 'product_manage', business_type: 'product' },
  ReceivablesView: { page: 'receivables', business_type: 'finance' },
  ExpenseList: { page: 'expenses', business_type: 'finance' },
  StatementList: { page: 'statement_list', business_type: 'finance' },
  StatementDetail: { page: 'statement_detail', business_type: 'finance' },
  ProjectCostList: { page: 'project_cost_list', business_type: 'finance' },
  ProjectCostDetail: { page: 'project_cost_detail', business_type: 'finance' },
  QuoteCostDetail: { page: 'quote_cost_detail', business_type: 'finance' },
  CostDebtList: { page: 'cost_debt_list', business_type: 'finance' },
  OutsourceVendorList: { page: 'outsource_vendors', business_type: 'outsource' },
  OutsourceTaskList: { page: 'outsource_tasks', business_type: 'outsource' },
  OutsourceTaskRecycle: { page: 'outsource_task_recycle', business_type: 'outsource' },
  OutsourcePaymentList: { page: 'outsource_payments', business_type: 'outsource' },
  InventoryList: { page: 'inventory' },
  DailyReport: { page: 'daily_report', business_type: 'report' },
  MonthlyReport: { page: 'monthly_report', business_type: 'report' },
  AdminUserManage: { page: 'admin_users', business_type: 'admin' },
  AdminRoleManage: { page: 'admin_roles', business_type: 'admin' },
  AdminSettings: { page: 'admin_settings', business_type: 'admin' },
  AIProviderList: { page: 'ai_providers', business_type: 'admin' },
  AIKnowledgeHealth: { page: 'ai_knowledge_health', business_type: 'admin' },
  OperationLogList: { page: 'operation_logs', business_type: 'admin' },
  BackupManage: { page: 'backups', business_type: 'admin' },
  NotificationList: { page: 'notifications' },
  Chat: { page: 'chat' },
  VehicleDashboard: { page: 'vehicle_dashboard', business_type: 'vehicle' },
  VehicleList: { page: 'vehicle_list', business_type: 'vehicle' },
  DriverList: { page: 'driver_list', business_type: 'vehicle' },
  VehicleUseRequestList: { page: 'vehicle_use_requests', business_type: 'vehicle' },
  VehicleAgentDrafts: { page: 'vehicle_agent_drafts', business_type: 'vehicle' },
  VehicleDispatchList: { page: 'vehicle_dispatches', business_type: 'vehicle' },
  VehicleTripRecordList: { page: 'vehicle_trip_records', business_type: 'vehicle' },
  VehicleExpenseList: { page: 'vehicle_expenses', business_type: 'vehicle' },
  VehicleInsuranceInspection: { page: 'vehicle_insurance', business_type: 'vehicle' },
  VehicleIncidentList: { page: 'vehicle_incidents', business_type: 'vehicle' },
  VehicleReports: { page: 'vehicle_reports', business_type: 'vehicle' },
  AerialDashboard: { page: 'aerial_dashboard', business_type: 'aerial' },
  AerialLedgerList: { page: 'aerial_ledgers', business_type: 'aerial' },
  AerialPersonnelExpenseList: { page: 'aerial_personnel_expenses', business_type: 'aerial' },
  AerialPersonnelWageList: { page: 'aerial_personnel_wages', business_type: 'aerial' },
  AerialVehicleCostList: { page: 'aerial_vehicle_costs', business_type: 'aerial' },
  AerialSafetyCheckList: { page: 'aerial_safety_checks', business_type: 'aerial' },
  AerialReports: { page: 'aerial_reports', business_type: 'aerial' },
  AerialVehicleList: { page: 'aerial_vehicles', business_type: 'aerial' },
  AerialPersonnelList: { page: 'aerial_personnel', business_type: 'aerial' },
  AerialAgentDraftList: { page: 'aerial_agent_drafts', business_type: 'aerial' },
  AnomalyDashboard: { page: 'anomaly_dashboard', business_type: 'ai' },
  AIQuoteAssistant: { page: 'ai_quote_assistant', business_type: 'ai' },
  QuoteKnowledgeBase: { page: 'quote_knowledge_base', business_type: 'ai' },
  BusinessNarrativeReport: { page: 'business_narrative_report', business_type: 'ai' },
  SitePhotoRecognition: { page: 'site_photo_recognition', business_type: 'ai' },
  PaymentOCR: { page: 'payment_ocr', business_type: 'ai' },
}

export function resolvePageContext(
  routeName: string,
  params: Record<string, string | string[]>,
): PageContext {
  const routeContext = pageContexts[routeName]
  if (!routeContext) return {}

  const capability = routeContext.page
    ? getPageCapability(routeContext.page)
    : undefined
  const context: PageContext = {
    ...routeContext,
    ...(capability
      ? {
          page_title: capability.title,
          page_purpose: capability.purpose,
          workflow_stage: capability.workflowStage,
          available_actions: [...capability.availableActions],
        }
      : {}),
  }
  const businessId = params.id || params.orderId || params.quoteId
  if (typeof businessId === 'string') context.business_id = businessId
  return context
}

export { getPageCapability, getPageQuickActions }
