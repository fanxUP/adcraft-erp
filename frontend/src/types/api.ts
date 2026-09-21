// ============================================================
// Shared API response types — mirrors backend Pydantic schemas
// Interceptor unwraps ApiResponse<Data>, so these are the inner
// `Data` shapes that every `get<T>()` / `post<T>()` returns.
// ============================================================

// ---- Common ----

export type UiTone = 'brand' | 'success' | 'warning' | 'danger' | 'info' | 'neutral'

export interface ApiMeta {
  request_id?: string
  timestamp?: string
}

export interface ApiFieldError {
  loc: Array<string | number>
  msg: string
  type?: string
}

export interface ApiEnvelope<T> {
  code: number
  message: string
  data: T | null
  meta?: ApiMeta
}

export interface StatusView {
  code: string
  label: string
  tone: UiTone
  terminal: boolean
}

export interface ActionCapability {
  allowed: boolean
  disabled_reason?: string | null
  requires_confirmation: boolean
}

export interface PaginatedData<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

// ---- Auth ----

export type { UserPreferences } from '@/config/userPreferences'
import type { UserPreferences } from '@/config/userPreferences'

export interface LoginResponse {
  token: string
  username: string
  real_name?: string
  must_change_password?: boolean
}

export interface UserProfile {
  id: string
  username: string
  real_name?: string
  phone?: string
  email?: string
  is_active: boolean
  must_change_password?: boolean
  roles: string[]
  permissions: string[]
  capabilities: {
    view_order_price: boolean
    view_order_item_price: boolean
    view_catalog_price: boolean
    view_cost: boolean
    view_financial_report: boolean
  }
  preferences?: UserPreferences
}

// ---- User ----

export interface UserResponse {
  id: string
  username: string
  real_name?: string
  phone?: string
  email?: string
  is_active: boolean
  must_change_password?: boolean
  created_at?: string
  roles: string[]
  linked_employee?: {
    id: string
    employee_no: string
    name: string
    department?: string | null
  } | null
}

// ---- Customer ----

export interface ContactResponse {
  id: string
  name: string
  phone?: string | null
  wechat?: string | null
  position?: string | null
  is_primary: boolean
  remark?: string
}

export interface CustomerResponse {
  id: string
  customer_no: string
  name: string
  customer_type?: string
  level?: string
  phone?: string
  wechat?: string
  address?: string
  tax_no?: string
  invoice_info?: string
  default_payment_days: number
  default_discount: number
  remark?: string
  created_at?: string
  contacts: ContactResponse[]
}

// ---- Order ----

export interface OrderListResponse {
  id: string
  order_no: string
  customer_id: string
  customer_name?: string
  project_name: string
  status: string
  status_view?: StatusView | null
  total_amount: number
  paid_amount: number
  unpaid_amount: number
  department?: string
  order_date?: string
  created_at?: string
}

export interface OrderItemResponse {
  id: string
  item_name: string
  product_id?: string
  material_id?: string
  process_id?: string
  length?: number
  length_unit?: string
  width?: number
  width_unit?: string
  height?: number
  height_unit?: string
  quantity: number
  unit?: string
  use_area?: boolean
  quantity_mode?: 'piece' | 'area'
  area?: number
  pieces?: number
  unit_price: number
  process_fee?: number
  installation_fee?: number
  design_fee?: number
  transport_fee?: number
  other_fee: number
  subtotal_amount: number
  remark?: string
  image_url?: string
  sort_order: number
  group_id?: string
  group_name?: string
  material_process?: string
  specification?: string
  lifecycle_status?: string
}

export type OrderItemStage =
  | 'designing'
  | 'in_production'
  | 'in_installation'
  | 'completed'
  | 'not_ready'

export interface TaskOrderItemOption extends Omit<OrderItemResponse,
  | 'unit_price'
  | 'process_fee'
  | 'installation_fee'
  | 'design_fee'
  | 'transport_fee'
  | 'other_fee'
  | 'subtotal_amount'
> {
  // Task-facing APIs omit line price fields unless the caller has the
  // explicit order_item:view_price permission.
  unit_price?: number
  process_fee?: number
  installation_fee?: number
  design_fee?: number
  transport_fee?: number
  other_fee?: number
  subtotal_amount?: number
  stage: OrderItemStage
  stage_label: string
  stage_view: StatusView
  can_select: boolean
  disabled_reason?: string | null
  is_linked: boolean
  task_status?: string | null
  task_status_label?: string | null
  task_status_view?: StatusView | null
  task_progress_pct?: number | null
  assignee_user_id?: string | null
  assignee_name?: string | null
  assignee_state: 'unassigned' | 'claimed' | 'historical_unknown' | 'terminal' | 'rolled_back'
  capabilities?: Record<string, ActionCapability>
  actions?: TaskItemAction[]
  outsource_blocked: boolean
  outsource_status?: 'pending' | 'in_progress' | null
  outsource_status_label?: string | null
  outsource_task_count: number
  outsource_task_nos: string[]
}

export interface TaskItemAction {
  key: string
  to_status: string
  label: string
  allowed: boolean
  disabled_reason?: string | null
  kind: 'primary' | 'secondary'
  requires_confirmation?: boolean
  operation?: 'status_change' | 'rollback'
  target_stage?: 'design' | 'production' | 'installation' | null
}

export interface OrderItemMutationFields {
  item_name?: string
  product_id?: string | null
  material_id?: string | null
  process_id?: string | null
  length?: number | null
  length_unit?: string | null
  width?: number | null
  width_unit?: string | null
  height?: number | null
  height_unit?: string | null
  quantity?: number
  unit?: string | null
  use_area?: boolean
  quantity_mode?: string
  pieces?: number | null
  unit_price?: number
  process_fee?: number
  installation_fee?: number
  design_fee?: number
  transport_fee?: number
  other_fee?: number
  remark?: string | null
  image_url?: string | null
  sort_order?: number
  group_name?: string | null
  group_id?: string | null
  material_process?: string | null
}

export interface OrderEditItem extends OrderItemMutationFields {
  id?: string
}

export interface OrderEditGroup {
  group_id: string
  group_name?: string | null
  sort_order: number
}

export interface OrderEditHeader {
  customer_id?: string | null
  customer_name?: string | null
  project_name?: string | null
  department?: string | null
  contact_person?: string | null
  contact_phone?: string | null
  delivery_deadline?: string | null
  installation_address?: string | null
  remark?: string | null
}

export interface OrderEditRequest {
  reason: string
  expected_updated_at: string
  header: OrderEditHeader
  items: OrderEditItem[]
  groups: OrderEditGroup[]
  preview_id?: string
  plan_hash?: string
  preview_expires_at?: string
  confirm_high_risk?: boolean
}

export interface OrderEditItemDiff {
  operation: 'add' | 'update' | 'delete'
  item_id?: string | null
  item_name?: string | null
  changed_fields: string[]
  before?: Record<string, unknown> | null
  after?: Record<string, unknown> | null
}

export interface OrderEditImpactResponse {
  order_id: string
  order_no: string
  status: string
  updated_at?: string
  operation: 'batch'
  preview_id: string
  preview_expires_at: string
  plan_hash: string
  change_status?: 'PREVIEWED' | string
  verification_status?: 'PENDING' | string
  before: OrderItemFinancialSnapshot
  after: OrderItemFinancialSnapshot
  delta: number
  diff: {
    added: number
    updated: number
    deleted: number
    header_changed: number
    groups_changed: boolean
  }
  header_diff: Array<{ field: string; before: unknown; after: unknown }>
  item_diffs: OrderEditItemDiff[]
  decision: 'DIRECT_APPLY' | 'CONFIRM_AND_REFRESH' | 'APPROVAL_AND_ADJUSTMENT' | 'BLOCK' | string
  associated_edit_enabled?: boolean
  requires_confirmation: boolean
  requires_high_risk_ack: boolean
  association_count: number
  lock_reasons: Array<{ code: string; message: string }>
  can_apply: boolean
  auto_recycle?: boolean
  recycle_reason?: string | null
  association_catalog: OrderItemRelationCatalogEntry[]
  refresh_plan?: OrderItemRelationCatalogEntry[]
  relations: Record<string, unknown>
}

export interface OrderGroupResponse {
  id: string
  quote_id: string
  group_id: string
  group_name?: string | null
  sort_order: number
}

export interface OrderItemRelationCatalogEntry {
  module: string
  label: string
  relation_type: 'document' | 'item' | 'snapshot' | 'source' | string
  record_id: string
  record_no?: string | null
  status?: string | null
  action: string
  risk: 'low' | 'medium' | 'high' | string
  fields?: string[]
  note?: string
}

export interface OrderItemFinancialSnapshot {
  total_amount: number
  paid_amount: number
  unpaid_amount: number
  cost_amount: number
  gross_profit: number
  line_count: number
  active_item_count?: number
}

export interface OrderItemEditabilityResponse {
  order_id: string
  order_no: string
  status: string
  updated_at?: string
  can_edit_items: boolean
  associated_edit_enabled?: boolean
  editable_statuses: string[]
  decision: 'DIRECT_APPLY' | 'CONFIRM_AND_REFRESH' | 'APPROVAL_AND_ADJUSTMENT' | 'BLOCK' | string
  requires_confirmation: boolean
  requires_high_risk_ack: boolean
  association_count: number
  lock_reasons: Array<{ code: string; message: string }>
  association_catalog: OrderItemRelationCatalogEntry[]
  relations: Record<string, unknown>
}

export interface OrderItemRefreshResult {
  status: 'VERIFIED' | 'PENDING_ADJUSTMENT' | 'BLOCKED' | string
  change_batch_id: string
  auto_refreshed: Array<Record<string, unknown>>
  preserved_facts: Array<Record<string, unknown>>
  pending_review: Array<Record<string, unknown>>
  adjustments: Array<Record<string, unknown>>
  blocked: Array<Record<string, unknown>>
  counts?: Record<string, number>
}

export interface OrderItemChangeBatch {
  change_batch_id: string
  version_id: string
  version_no: number
  created_at?: string | null
  created_by?: string | null
  operator_id?: string | null
  change_type?: string | null
  reason?: string | null
  status: string
  status_history?: string[]
  verification_status: string
  counts?: Record<string, number>
  before?: Record<string, unknown> | null
  after?: Record<string, unknown> | null
  impact?: Record<string, unknown> | null
  refresh_result?: OrderItemRefreshResult
}

export interface OrderItemChangeBatchListResponse {
  order_id: string
  order_no: string
  total: number
  batches: OrderItemChangeBatch[]
}

export interface OrderItemReconciliationCheck {
  ok: boolean
  actual: number | string | null
  expected: number | string | null
}

export interface OrderItemReconciliationResponse {
  order_id: string
  order_no: string
  checked_at: string
  status: 'PASS' | 'ATTENTION' | string
  checks: Record<string, OrderItemReconciliationCheck>
  financials: Record<string, number | string | null>
  associations: Record<string, unknown>
  orphan_references: Array<Record<string, unknown>>
  history: Record<string, unknown>
  change_batch?: OrderItemChangeBatch | null
}

export interface OrderItemMutationImpactResponse {
  order_id: string
  order_no: string
  status: string
  updated_at?: string
  operation: 'add' | 'update' | 'delete'
  item_id?: string | null
  before: OrderItemFinancialSnapshot
  after: OrderItemFinancialSnapshot
  delta: number
  projected_item?: Record<string, unknown> | null
  associated_edit_enabled?: boolean
  decision: 'DIRECT_APPLY' | 'CONFIRM_AND_REFRESH' | 'APPROVAL_AND_ADJUSTMENT' | 'BLOCK' | string
  requires_confirmation: boolean
  requires_high_risk_ack: boolean
  association_count: number
  lock_reasons: Array<{ code: string; message: string }>
  can_apply: boolean
  auto_recycle?: boolean
  recycle_reason?: string | null
  preview_id: string
  preview_expires_at: string
  plan_hash: string
  change_status?: 'PREVIEWED' | string
  verification_status?: 'PENDING' | string
  association_catalog: OrderItemRelationCatalogEntry[]
  refresh_plan?: OrderItemRelationCatalogEntry[]
  relations: Record<string, unknown>
}

export interface OrderStatusLogResponse {
  id: string
  from_status?: string
  to_status: string
  reason?: string
  operated_by?: string
  operated_at: string
}

export interface OrderDetailResponse {
  id: string
  order_id?: string
  order_no: string
  related_doc_id?: string
  related_doc_type?: string
  related_project_name?: string
  customer_id: string
  customer_name?: string
  project_name: string
  sales_user_id?: string
  status: string
  status_view?: StatusView | null
  total_amount: number
  paid_amount: number
  unpaid_amount: number
  delivery_deadline?: string
  installation_address?: string
  remark?: string
  department?: string
  contact_person?: string
  contact_phone?: string
  order_date?: string
  created_at?: string
  updated_at?: string
  source_quote_id?: string
  items: OrderItemResponse[]
  groups: OrderGroupResponse[]
  status_logs: OrderStatusLogResponse[]
  change_batch?: {
    change_batch_id: string
    status: string
    status_history?: string[]
    verification_status?: string
    idempotent_replay?: boolean
    auto_recycled?: boolean
    refresh_result?: OrderItemRefreshResult
  }
  cost_amount?: number
  gross_profit?: number
}

export interface TaskAssigneeOption {
  id: string
  name: string
  employee_no: string
  user_id: string
}

export interface OrderTaskAssigneesResponse {
  order_id: string
  employee_ids: string[]
  employees: TaskAssigneeOption[]
  is_restricted: boolean
}

// ---- Task ----

export interface AttachmentResponse {
  id: string
  related_type: string
  related_id: string
  filename: string
  file_path: string
  file_size?: number
  file_type?: string
  category?: string
  uploaded_by?: string
  remark?: string
  created_at?: string
}

/** Order-detail task materials intentionally omit the server storage path. */
export interface OrderTaskAttachmentResponse {
  id: string
  related_type: 'order_stage' | 'design_task' | 'production_task' | 'installation_task'
  related_id: string
  order_id?: string | null
  order_item_id?: string | null
  order_item_name?: string | null
  order_item_label?: string | null
  order_item_sort_order?: number | null
  stage?: TaskType | null
  filename: string
  file_size?: number | null
  file_type?: string | null
  category?: string | null
  uploaded_by?: string | null
  uploaded_by_name?: string | null
  remark?: string | null
  created_at?: string | null
}

export interface OrderTaskAttachmentTask {
  task_id: string
  task_no?: string | null
  status: string
  status_label: string
  completed_at?: string | null
  upload_allowed: boolean
  read_only_reason?: string | null
  attachments: OrderTaskAttachmentResponse[]
}

export interface OrderTaskAttachmentGroup {
  task_type: TaskType
  stage?: TaskType
  label: string
  task_label: string
  accept: string
  task_count?: number
  attachment_count: number
  can_upload?: boolean
  can_delete?: boolean
  attachments: OrderTaskAttachmentResponse[]
  /** Kept only for one release so older clients can decode the response. */
  tasks?: OrderTaskAttachmentTask[]
}

export interface OrderTaskAttachmentsResponse {
  order_id: string
  groups: OrderTaskAttachmentGroup[]
}

export type TaskType = 'design' | 'production' | 'installation'

export interface TaskOrderItemState {
  status: string
  status_label?: string | null
  progress_pct: number
  status_view?: StatusView | null
  capabilities?: Record<string, ActionCapability>
}

export interface DesignTaskResponse {
  id: string
  design_no: string
  order_id: string
  order_item_id?: string | null
  order_item_ids?: string[]
  order_item_states?: Record<string, TaskOrderItemState>
  customer_id: string
  order_no?: string
  customer_name?: string
  department?: string
  contact_name?: string
  contact_phone?: string
  total_amount?: number
  source?: string
  project_name: string
  item_name?: string | null
  item_names?: string[]
  status: string
  progress_pct: number
  review_required?: boolean
  review_reason?: string | null
  status_view?: StatusView | null
  capabilities?: Record<string, ActionCapability>
  planned_start_at?: string | null
  planned_end_at?: string | null
  is_overdue?: boolean
  overdue_days?: number
  is_outsourced?: boolean
  assigned_to?: string
  assigned_to_name?: string
    description?: string
  design_file_url?: string
  client_comments?: string
  completed_at?: string
  created_at?: string
  updated_at?: string
  attachments: AttachmentResponse[]
}

export interface ProductionTaskResponse {
  id: string
  production_no: string
  order_id: string
  order_item_id?: string | null
  order_item_ids?: string[]
  order_item_states?: Record<string, TaskOrderItemState>
  customer_id: string
  order_no?: string
  customer_name?: string
  department?: string
  contact_name?: string
  contact_phone?: string
  total_amount?: number
  source?: string
  project_name: string
  item_name?: string | null
  item_names?: string[]
  status: string
  progress_pct: number
  review_required?: boolean
  review_reason?: string | null
  status_view?: StatusView | null
  capabilities?: Record<string, ActionCapability>
  planned_start_at?: string | null
  planned_end_at?: string | null
  is_overdue?: boolean
  overdue_days?: number
  is_outsourced?: boolean
  assigned_to?: string
  assigned_to_name?: string
  material_id?: string
  process_id?: string
  length?: number
  width?: number
  height?: number
  quantity: number
  qc_result?: string
  rework_reason?: string
  completed_at?: string
  created_at?: string
  updated_at?: string
  attachments: AttachmentResponse[]
}

export interface InstallationTaskResponse {
  id: string
  installation_no: string
  order_id: string
  order_item_id?: string | null
  order_item_ids?: string[]
  order_item_states?: Record<string, TaskOrderItemState>
  customer_id: string
  order_no?: string
  customer_name?: string
  department?: string
  total_amount?: number
  source?: string
  project_name: string
  item_name?: string | null
  item_names?: string[]
  status: string
  progress_pct: number
  review_required?: boolean
  review_reason?: string | null
  status_view?: StatusView | null
  capabilities?: Record<string, ActionCapability>
  planned_start_at?: string | null
  planned_end_at?: string | null
  is_overdue?: boolean
  overdue_days?: number
  is_outsourced?: boolean
  assigned_to?: string
  assigned_to_name?: string
  address?: string
  contact_name?: string
  contact_phone?: string
  scheduled_at?: string
  acceptance_result?: string
  completed_at?: string
  created_at?: string
  updated_at?: string
  attachments: AttachmentResponse[]
}

export interface TaskQueueItem {
  id: string
  task_type: 'design' | 'production' | 'installation'
  stage: 'design' | 'production' | 'installation'
  task_no: string
  document_id: string
  order_id?: string
  order_item_id?: string | null
  order_item_ids?: string[]
  order_no?: string
  customer_name?: string | null
  department?: string | null
  project_name: string
  item_name?: string | null
  item_names?: string[]
  status: string
  progress_pct: number
  review_required?: boolean
  review_reason?: string | null
  total_amount?: number | null
  status_view?: StatusView | null
  capabilities?: Record<string, ActionCapability>
  planned_start_at?: string | null
  planned_end_at?: string | null
  is_overdue?: boolean
  overdue_days?: number
  assigned_to?: string
  assigned_to_name?: string
  is_outsourced?: boolean
  completed_at?: string
  created_at?: string
  updated_at?: string
}

export interface CompletedProjectCard {
  kind: 'project'
  project_id: string
  project_no: string
  project_name: string
  customer_name?: string | null
  department?: string | null
  status: 'completed'
  completed_at?: string | null
  completed_detail_count: number
  completed_work_unit_count: number
  stages: TaskCompletionType[]
  scope: 'all' | 'own'
  total_amount?: number | null
}

export interface CompletedProjectDetailItem {
  kind: 'detail'
  project_id: string
  project_no: string
  project_name: string
  order_item_id: string
  item_name: string
  material_process?: string | null
  specification?: string | null
  quantity?: number | null
  unit?: string | null
  stages: Partial<Record<TaskCompletionType, CompletedProjectStage | null>>
}

export interface CompletedProjectStage {
  status: 'completed'
  status_label: string
  employee_id?: string | null
  employee_name: string
  completed_at?: string | null
  task_id: string
  task_no?: string | null
  source: string
}

export interface CompletedProjectResourceTask {
  task_id: string
  task_no?: string | null
  attachments: AttachmentResponse[]
}

export interface CompletedProjectResourceSection {
  task_type: TaskCompletionType
  task_label: string
  task_count: number
  attachment_count: number
  tasks: CompletedProjectResourceTask[]
}

export interface CompletedProjectDetail extends CompletedProjectCard {
  items: CompletedProjectDetailItem[]
  resources: Partial<Record<TaskCompletionType, CompletedProjectResourceSection>>
}

// ---- Product / Material / Process ----

export interface ProductCategoryResponse {
  id: string
  name: string
  parent_id?: string
  sort_order: number
}

export interface ProductResponse {
  id: string
  category_id?: string
  name: string
  material_name?: string
  process_name?: string
  unit: string
  pricing_method: string
  default_price?: number
  min_charge?: number
  remark?: string
  is_active: boolean
  created_at?: string
}

export interface MaterialResponse {
  id: string
  name: string
  spec?: string
  unit: string
  purchase_price?: number
  sale_price?: number
  loss_rate: number
  safe_stock: number
  remark?: string
  is_active: boolean
  created_at?: string
}

export interface ProcessResponse {
  id: string
  name: string
  charge_method: string
  default_price?: number
  remark?: string
  is_active: boolean
  created_at?: string
}

// ---- Payment / Statement / Expense ----

export interface PaymentResponse {
  id: string
  payment_no: string
  document_id?: string | null
  order_id?: string | null
  contract_id?: string | null
  contract_no?: string | null
  order_no?: string
  customer_id: string
  customer_name?: string
  project_name?: string
  department?: string
  amount: number
  payment_method?: string
  paid_at?: string
  remark?: string
  is_voided: boolean
  status_view?: StatusView | null
  void_reason?: string
  voided_at?: string
  receipt_url?: string
  created_at?: string
  created_by?: string
  allocation_status?: string
  allocation_total?: number
  allocations?: PaymentAllocationResponse[]
}

export interface PaymentAllocationResponse {
  id: string
  contract_id: string
  document_id?: string | null
  order_id?: string | null
  amount: number
  allocation_type: string
}

export interface StatementResponse {
  id: string
  statement_no: string
  customer_id: string
  start_date?: string
  end_date?: string
  total_order_amount: number
  total_paid_amount: number
  total_unpaid_amount: number
  status: string
  status_view?: StatusView | null
  capabilities?: Record<string, ActionCapability>
  confirmed_at?: string
  confirmed_by?: string
  created_at?: string
}

export interface StatementOrderItem {
  id: string
  order_no: string
  project_name: string
  status: string
  status_view?: StatusView | null
  total_amount: number
  paid_amount: number
  unpaid_amount: number
}

export interface StatementPaymentItem {
  id: string
  payment_no: string
  amount: number
  payment_method?: string
  paid_at?: string
  is_voided: boolean
}

export interface StatementDetailResponse extends StatementResponse {
  orders: StatementOrderItem[]
  payments: StatementPaymentItem[]
}

export interface ExpenseResponse {
  id: string
  expense_no: string
  category?: string
  payment_method?: string | null
  amount: number
  payee_name?: string
  supplier_id?: string | null
  supplier_name?: string | null
  payable_amount: number
  initial_paid_amount?: number
  payable_paid_amount?: number
  total_paid_amount?: number
  remaining_payable_amount?: number
  payable_status?: string
  payable_payment_count?: number
  description?: string
  expense_date?: string
  receipt_url?: string
  created_by?: string
  created_at?: string
}

export interface ExpenseDeleteConfirmedResponse {
  deleted: boolean
  payment_ids: string[]
  payment_count: number
  paid_amount: number
}

export interface PayablePaymentResponse {
  id: string
  payment_no: string
  source_type: 'expense' | 'project_cost' | string
  source_id: string
  amount: number
  payment_method: string
  paid_at?: string
  remark?: string
  receipt_url?: string
  is_voided: boolean
  void_reason?: string
  voided_at?: string
  created_at?: string
  created_by?: string
}

export interface PayableResponse {
  id: string
  source_type: 'expense' | 'project_cost' | string
  source_id: string
  source_label: string
  source_no: string
  source_total_amount: number
  payable_total_amount: number
  paid_amount: number
  remaining_amount: number
  payee_name?: string
  supplier_id?: string | null
  supplier_name?: string | null
  status: string
  status_view?: StatusView | null
  capabilities?: Record<string, ActionCapability>
  order_no?: string
  quote_no?: string
  project_name?: string
  customer_name?: string
  document_item_name?: string
  category?: string
  description?: string
  remark?: string
  payment_method?: string
  source_date?: string
  payments?: PayablePaymentResponse[]
}

export interface ProjectCostResponse {
  id: string
  cost_no: string
  source_type: string
  order_id?: string
  related_doc_id?: string
  related_doc_type?: string
  related_project_name?: string
  quote_no?: string
  order_item_id?: string
  order_item_ids?: string[]
  quote_item_id?: string
  order_item_name?: string
  quote_item_name?: string
  item_scopes?: ProjectCostItemScope[]
  scope_type?: 'document' | 'item'
  group_name?: string
  customer_id?: string
  customer_name?: string
  project_name?: string
  category: string
  amount: number
  payment_amount?: number
  status_view?: StatusView | null
  capabilities?: Record<string, ActionCapability>
  quantity?: number
  unit?: string
  unit_price?: number
  payment_method?: string
  payee_company_name?: string
  supplier_id?: string | null
  supplier_name?: string | null
  debt_amount?: number
  is_debt: boolean
  is_settled: boolean
  settled_at?: string
  specification?: string
  description?: string
  summary?: string
  cost_date?: string
  receipt_url?: string
  remark?: string
  created_by?: string
  created_at?: string
  attachment_count?: number
  attachments?: AttachmentResponse[]
}

export interface ProjectCostItemScope {
  order_item_id: string
  order_item_name?: string
}

export interface DebtResponse {
  id: string
  cost_no: string
  source_type: string
  order_id?: string
  related_doc_id?: string
  related_doc_type?: string
  related_project_name?: string
  order_no?: string
  quote_no?: string
  project_name?: string
  customer_id?: string
  customer_name?: string
  category: string
  quantity?: number
  unit?: string
  unit_price?: number
  amount: number
  payment_method?: string
  payee_company_name?: string
  debt_amount: number
  is_settled: boolean
  status_view?: StatusView | null
  capabilities?: Record<string, ActionCapability>
  settled_at?: string
  cost_date?: string
  description?: string
  remark?: string
  created_by?: string
  created_at?: string
}

export interface QuoteCostResponse {
  id: string
  quote_no: string
  project_name: string
  customer_name?: string
  department?: string
  status: string
  status_view?: StatusView | null
  total_amount: number
  cost_amount: number
  created_at?: string
}

export interface ProjectCostImportResponse {
  created: number
  errors: Array<{ row: number; error: string }>
}

export interface ProjectCostSummaryResponse {
  costs: Record<string, number>
}

export interface ProjectCostItemSummary {
  order_item_id: string
  total_registered: number
  record_count: number
}

export interface ProjectCostItemSummaryResponse {
  order_id: string
  total_registered: number
  order_scope_registered: number
  item_scope_registered: number
  items: ProjectCostItemSummary[]
}

// ---- Inventory ----

export interface InventoryItemResponse {
  id: string
  material_name: string
  material_unit?: string
  category?: string
  spec?: string
  quantity: number
  min_quantity: number
  unit_cost: number
  remark?: string
  created_at?: string
}

export interface StockRecordResponse {
  id: string
  item_id: string
  item_name?: string
  record_type: string
  quantity: number
  unit_cost: number
  total_cost: number
  order_id?: string
  remark?: string
  operated_at?: string
  created_at?: string
}

// ---- Outsource ----

export interface VendorResponse {
  id: string
  vendor_no: string
  name: string
  short_name?: string | null
  supplier_type?: string
  supplier_type_label?: string | null
  contact_person?: string
  phone?: string
  email?: string | null
  address?: string
  tax_id?: string | null
  bank_name?: string | null
  bank_account?: string | null
  tax_rate?: number | null
  settlement_method?: string | null
  settlement_days?: number | null
  service_type?: string
  coop_rating?: string
  remark?: string
  is_active: boolean
  created_at?: string
}

export interface SupplierStats {
  project_cost_count: number
  project_cost_amount: number
  project_cost_payable: number
  project_cost_paid: number
  project_cost_remaining: number
  expense_count: number
  expense_amount: number
  expense_payable: number
  expense_paid: number
  expense_remaining: number
  outsource_task_count: number
  outsource_task_amount: number
  outsource_task_unpaid: number
}

export interface SupplierResponse extends VendorResponse {
  supplier_type: string
  supplier_type_label?: string | null
  stats?: SupplierStats | null
}

export interface OutsourceTaskResponse {
  id: string
  task_no: string
  vendor_id: string
  vendor_name?: string
  related_doc_id?: string
  related_doc_type?: string
  related_project_name?: string
  order_id?: string
  order_item_id?: string | null
  order_item_name?: string | null
  source_task_type?: string
  source_task_id?: string
  task_type: string
  description?: string
  quantity: number
  unit_price: number
  total_amount: number
  paid_amount: number
  unpaid_amount: number
  status: string
  status_view?: StatusView | null
  capabilities?: Record<string, ActionCapability>
  expected_at?: string
  completed_at?: string
  remark?: string
  created_at?: string
  deleted_at?: string
}

export interface OutsourceTaskGroupResponse {
  group_key: string
  group_kind: 'source_task' | 'related_document' | 'unresolved_source' | 'unresolved_document' | 'unlinked' | string
  group_label: string
  source_task_type?: string | null
  source_task_id?: string | null
  source_task_no?: string | null
  source_task_status?: string | null
  source_task_exists?: boolean | null
  related_doc_type?: string | null
  related_doc_id?: string | null
  related_doc_no?: string | null
  related_project_name?: string | null
  related_project_amount?: number | null
  consistency_warning?: string | null
  task_count: number
  active_task_count: number
  status_counts: Record<string, number>
  planned_amount: number
  recognized_cost: number
  paid_amount: number
  unpaid_amount: number
}

export interface OutsourceOrderItemSummary {
  id: string
  item_name: string
  quantity: number
  unit?: string | null
  group_name?: string | null
  sort_order: number
  lifecycle_status?: string
  allocated_quantity: number
  remaining_quantity: number
  planned_amount: number
  recognized_cost: number
  active_task_count: number
  status: string
  can_send: boolean
  requires_reason: boolean
  block_reason?: string | null
}

export interface OutsourceOrderItemSummaryResponse {
  order_id: string
  order_no: string
  project_name: string
  task_type?: string | null
  source_task_type?: string | null
  source_task_id?: string | null
  items: OutsourceOrderItemSummary[]
  order_level_task_count: number
  order_level_planned_amount: number
  order_level_recognized_cost: number
}

export interface OutsourcePaymentResponse {
  id: string
  payment_no: string
  vendor_id: string
  vendor_name?: string
  task_id?: string
  amount: number
  payment_method?: string
  payee_company_name?: string
  paid_at?: string
  remark?: string
  created_by?: string
  created_at?: string
}

// ---- Operation Log ----

export interface OperationLogResponse {
  id: string
  user_id?: string
  user_name?: string
  object_type?: string
  object_id?: string
  action: string
  before_data?: Record<string, unknown>
  after_data?: Record<string, unknown>
  ip_address?: string
  created_at?: string
}

// ---- Quote ----

export interface QuoteItemResponse {
  id: string
  quote_id: string
  product_id?: string
  material_id?: string
  process_id?: string
  item_name: string
  length?: number
  length_unit?: string
  width?: number
  width_unit?: string
  height?: number
  height_unit?: string
  quantity: number
  unit?: string
  use_area?: boolean
  quantity_mode?: 'piece' | 'area'
  area?: number
  pieces?: number
  unit_price: number
  process_fee?: number
  installation_fee?: number
  design_fee?: number
  transport_fee?: number
  other_fee: number
  subtotal_amount: number
  remark?: string
  image_url?: string
  sort_order: number
  group_id?: string
  group_name?: string
  material_process?: string
  specification?: string
}

export interface QuoteListResponse {
  id: string
  quote_no: string
  quote_mode?: 'regular' | 'cdr'
  customer_id?: string
  customer_name?: string
  project_name: string
  status: string
  status_view?: StatusView | null
  total_amount: number
  valid_until?: string
  quote_date?: string
  created_at?: string
  department?: string
  contact_person?: string
  contact_phone?: string
}

export interface QuoteGroupResponse {
  id: string
  quote_id: string
  group_id: string
  group_name?: string | null
  sort_order: number
}

export interface QuoteGroupInput {
  group_id: string
  group_name?: string | null
  sort_order?: number
}

export interface QuoteDetailResponse {
  id: string
  quote_no: string
  quote_mode?: 'regular' | 'cdr'
  customer_id?: string
  customer_name?: string
  project_name: string
  sales_user_id?: string
  status: string
  status_view?: StatusView | null
  subtotal_amount: number
  discount_amount: number
  tax_rate: number
  tax_amount: number
  total_amount: number
  valid_until?: string | null
  quote_date?: string | null
  remark?: string
  department?: string
  contact_person?: string
  contact_phone?: string
  created_at?: string
  items: QuoteItemResponse[]
  groups: QuoteGroupResponse[]
}

export interface SchoolQuoteImportItemPreview {
  row: number
  item_name: string
  quantity: number
  source_unit: string
  unit: string
  measure_kind: 'area' | 'quantity' | 'length' | 'volume' | 'weight'
  quantity_mode: 'piece' | 'area'
  unit_price: number
  subtotal_amount: number
  remark?: string | null
  length?: number | null
  length_unit?: string | null
  width?: number | null
  width_unit?: string | null
  height?: number | null
  height_unit?: string | null
  dimension_status: 'auto' | 'review' | 'none'
  dimension_source?: string | null
  dimension_reason?: string | null
}

export interface SchoolQuoteImportSchoolPreview {
  department: string
  item_count: number
  area_item_count: number
  dimension_auto_count: number
  dimension_review_count: number
  subtotal_amount: number
  unit_counts: Record<string, number>
  items: SchoolQuoteImportItemPreview[]
}

export interface SchoolQuoteImportPreview {
  preview_id: string
  source_sha256: string
  customer_name: string
  project_name: string
  valid: boolean
  school_count: number
  item_count: number
  total_amount: number
  dimension_auto_count: number
  dimension_review_count: number
  dimension_empty_count: number
  skipped_rows: Array<{ row: number; reason: string }>
  errors: Array<{ row: number; message: string }>
  warnings: Array<{ row: number; message: string }>
  schools: SchoolQuoteImportSchoolPreview[]
}

export interface SchoolQuoteImportCommitResponse {
  preview_id: string
  school_count: number
  item_count: number
  total_amount: number
  quotes: Array<{
    id: string
    quote_no: string
    department: string
    item_count: number
    total_amount: number
  }>
}

export interface SchoolQuoteDimensionBackfillRow {
  department: string
  quote_no?: string
  item_id?: string
  row?: number
  item_name?: string
  dimension_source?: string | null
  reason?: string
  fields?: Record<string, string | null>
  length?: number | null
  length_unit?: string | null
  width?: number | null
  width_unit?: string | null
  height?: number | null
  height_unit?: string | null
}

export interface SchoolQuoteDimensionBackfillReport {
  valid: boolean
  preview_id: string
  customer_name: string
  project_name: string
  expected_quote_count: number
  matched_quote_count: number
  change_count: number
  unchanged_count: number
  review_count: number
  skipped_count: number
  conflict_count: number
  changes: SchoolQuoteDimensionBackfillRow[]
  review_rows: SchoolQuoteDimensionBackfillRow[]
  skipped_rows: SchoolQuoteDimensionBackfillRow[]
  conflicts: SchoolQuoteDimensionBackfillRow[]
}

export interface SchoolQuoteDimensionBackfillPreview {
  source: SchoolQuoteImportPreview
  backfill: SchoolQuoteDimensionBackfillReport
}

// ---- Contract ----

export interface ContractListResponse {
  id: string
  contract_no: string
  customer_name: string
  project_name: string
  total_amount: number
  paid_amount: number
  unpaid_amount: number
  contract_type?: string
  status: string
  status_view?: StatusView | null
  sign_date?: string
  start_date?: string
  end_date?: string
  created_at?: string
}

export interface SimpleOrderRef {
  id: string
  order_no: string
  project_name: string
  department?: string
  total_amount: number
  paid_amount?: number
  unpaid_amount?: number
  status?: string
}

export interface ContractDetailResponse extends ContractListResponse {
  customer_id: string
  our_signatory?: string
  customer_signatory?: string
  attachment_path?: string
  attachment_name?: string
  content?: string
  remark?: string
  created_by?: string
  orders: SimpleOrderRef[]
}

export interface ContractResourceItem {
  id: string
  doc_type?: string
  doc_no?: string
  order_no?: string
  quote_no?: string
  project_name: string
  total_amount?: number
  department?: string
  status?: string
  customer_id?: string
  customer_name?: string
}

export interface ContractAvailableResources {
  orders: ContractResourceItem[]
  used_project_names: string[]
}

export interface OrderWithoutContractItem {
  id: string
  order_no?: string
  customer_id?: string
  customer_name?: string
  project_name: string
  department?: string
  status?: string
  status_view?: StatusView | null
  total_amount?: number
  created_at?: string
}

// ---- Framework Contract ----

export interface FrameworkContractProjectResponse {
  id: string
  contract_id: string
  customer_id: string
  customer_name: string
  department?: string
  project_name: string
  project_amount: number
  remark?: string
  attachment_path?: string
  attachment_name?: string
  created_at?: string
}

export interface FrameworkContractProjectDetailResponse extends FrameworkContractProjectResponse {
  orders: SimpleOrderRef[]
}

export interface FrameworkContractAvailableResources {
  orders: ContractResourceItem[]
  project_names: string[]
}

// ---- Backup ----

export interface BackupItem {
  filename: string
  size_display: string
  created_at: string
}

export interface BackupListResponse {
  backups: BackupItem[]
  total: number
  total_size_display: string
}

export interface CreateBackupResponse {
  message: string
  backup: BackupItem
  output?: string
}

export interface ImportBackupResponse {
  message: string
  backup: BackupItem
}

// ---- Reports ----

export interface CustomerDebtContract {
  id: string
  contract_no: string
  project_name: string
  total_amount: number
  paid_amount: number
  unpaid_amount: number
  status: string
  status_view?: StatusView | null
  contract_type?: string
  department?: string
  orders?: CustomerDebtOrder[]
  quotes?: CustomerDebtQuote[]
}

export interface CustomerDebtOrder {
  id: string
  order_no: string
  project_name: string
  department?: string
  total_amount: number
  paid_amount: number
  unpaid_amount: number
  status: string
  status_view?: StatusView | null
}

export interface CustomerDebtQuote {
  id: string
  quote_no: string
  project_name: string
  department?: string
  total_amount: number
  status: string
  status_view?: StatusView | null
}

export interface CustomerDebtItem {
  customer_id: string
  customer_name: string
  debt_amount: number
  total_order_amount: number
  total_paid: number
  contract_count: number
  last_payment_date: string | null
  contracts: CustomerDebtContract[]
}

export interface DashboardData {
  today_order_amount?: number
  today_payment_amount?: number
  month_order_amount?: number
  month_payment_amount?: number
  month_unpaid_amount?: number
  pending_design_count: number
  pending_production_count: number
  pending_installation_count: number
  overdue_order_count: number
  customer_debt_ranking?: CustomerDebtItem[]
}

export type TaskCompletionPeriod = 'all' | 'month'
export type TaskCompletionType = 'design' | 'production' | 'installation'
export type TaskCompletionKind = 'project' | 'detail'

export interface TaskCompletionStats {
  completed_project_count: number
  completed_work_unit_count: number
  stage_breakdown: Record<TaskCompletionType, number>
}

export interface TaskCompletionOrganizationStats extends TaskCompletionStats {
  completed_order_project_count: number
  completed_detail_count: number
  backfill_work_unit_count: number
  unknown_completion_time_count: number
}

export interface TaskCompletionEmployee {
  employee_id: string | null
  user_id: string | null
  employee_no: string | null
  name: string
  is_active: boolean
  employment_status: string | null
}

export interface TaskCompletionEmployeeStats extends TaskCompletionEmployee, TaskCompletionStats {}

export interface TaskCompletionSummary {
  period: TaskCompletionPeriod
  period_start: string | null
  period_end: string | null
  scope: 'own' | 'all'
  employee: TaskCompletionEmployee | null
  own: TaskCompletionStats
  organization: TaskCompletionOrganizationStats | null
  employees: TaskCompletionEmployeeStats[]
  unassigned: TaskCompletionStats
  message: string | null
}

export interface TaskCompletionProjectRow {
  kind: 'project'
  project_id: string
  project_no: string
  project_name: string
  completed_detail_count: number
  completed_work_unit_count: number
  stages: TaskCompletionType[]
  last_completed_at: string | null
}

export interface TaskCompletionDetailRow {
  kind: 'detail'
  project_id: string
  project_no: string
  project_name: string
  order_item_id: string
  item_name: string
  task_type: TaskCompletionType
  task_label: string
  task_id: string
  task_no: string | null
  employee_id: string | null
  employee_name: string
  completed_at: string | null
  status: string
  source: string
}

export type TaskCompletionRow = TaskCompletionProjectRow | TaskCompletionDetailRow

export interface TaskCompletionDetailsResponse extends PaginatedData<TaskCompletionRow> {
  scope: 'own' | 'all'
  employee?: TaskCompletionEmployee | null
  message?: string | null
}

export interface DailyReportOrder {
  id: string
  order_no: string
  project_name: string
  department?: string
  total_amount?: number
  status: string
}

export interface DailyReportPayment {
  payment_no: string
  amount?: number
  payment_method?: string
  is_voided: boolean
}

export interface DailyReportData {
  date: string
  order_count: number
  order_amount: number | null
  payment_count: number | null
  payment_amount: number | null
  new_customer_count: number
  orders: DailyReportOrder[]
  payments: DailyReportPayment[]
}

export interface MonthlyReportOrder {
  id: string
  order_no: string
  project_name: string
  department?: string
  total_amount?: number
  paid_amount?: number
  unpaid_amount?: number
  status: string
}

export interface MonthlyReportData {
  order_count: number
  order_amount: number | null
  payment_count: number | null
  payment_amount: number | null
  unpaid_amount: number | null
  status_breakdown: Record<string, number>
  orders: MonthlyReportOrder[]
}

// ---- Common Responses ----

export interface SuccessResponse {
  message: string
}

export interface ImportResponse {
  message: string
  succeeded: number
  failed: number
  errors?: Array<{ row: number; message: string }>
}

export interface UploadResponse {
  message: string
  url: string
}

// ============================================================
// AI Module Types (Phase 10)
// ============================================================

export interface DraftQuoteItem {
  item_name: string
  width?: number
  height?: number
  quantity: number
  unit: string
  product_id?: string
  material_id?: string
  process_id?: string
  material_process?: string
  unit_price?: number
  design_fee?: number
  installation_fee?: number
  process_fee?: number
  transport_fee?: number
  other_fee: number
  subtotal: number
  remark: string
}

export interface SimilarQuoteItem {
  quote_id: string
  quote_no: string
  project_name: string
  total_area?: number
  items_summary: string
  total_amount: number
  gross_profit?: number
  profit_margin?: number
  created_at?: string
}

export interface AIQuoteAssistResponse {
  mode: string
  project_name: string
  items: DraftQuoteItem[]
  total_estimate: number
  confidence: string
  similar_quotes_count: number
  similar_quotes: SimilarQuoteItem[]
  ai_analysis: string
  risk_notes: string[]
}

export interface AnomalyAlert {
  type: string
  severity: string
  object_type: string
  object_id: string
  title: string
  detail: string
  created_at: string
}

export interface AnomalySummary {
  critical: number
  warning: number
  info: number
}

export interface AnomalyScanResponse {
  mode: string
  alerts: AnomalyAlert[]
  summary: AnomalySummary
}

export interface SimilarQuoteResult {
  quote_id: string
  quote_no: string
  project_name: string
  total_area?: number
  items_summary: string
  total_amount: number
  gross_profit?: number
  profit_margin?: number
  created_at?: string
}

export interface PricingSummary {
  price_range: number[]
  avg_price: number
  avg_margin: number
  recommended_price: number
}

export interface SimilarQuotesResponse {
  mode: string
  items: SimilarQuoteResult[]
  pricing_summary: PricingSummary
}

export interface PhotoChecklist {
  wall_condition: string
  height_risk: string
  scaffolding_needed: string
  obstacles_found: string
  cost_impact_estimated: boolean
  notes: string
}

export interface SitePhotoAnalyzeResponse {
  mode: string
  photo_url: string
  checklist: PhotoChecklist
  ai_findings?: Record<string, unknown>
}

export interface OCRExtracted {
  amount?: number
  paid_at?: string
  payer_name?: string
  remark?: string
  payment_method?: string
}

export interface OCRRecognizeResponse {
  mode: string
  image_url: string
  extracted: OCRExtracted
  confidence: string
  order_context?: Record<string, unknown>
}

export interface BusinessNarrativeStats {
  order_count: number
  order_amount: number
  payment_count: number
  payment_amount: number
  unpaid_amount?: number
  overdue_count: number
  collection_rate?: number
  status_breakdown?: Record<string, number>
}

export interface BusinessNarrativeResponse {
  mode: string
  ai_confidence?: string
  ai_meta?: Record<string, unknown>
  period: string
  year: number
  month?: number
  week?: number
  stats: BusinessNarrativeStats
  narrative: string
  suggestions: string[]
}

// ---- Notification ----

export interface NotificationResponse {
  id: string
  user_id: string
  sender_id?: string
  sender_name?: string
  type: string
  title: string
  content: string
  link?: string
  is_read: boolean
  read_at?: string
  created_at: string
}

export interface UnreadCountResponse {
  count: number
}

// ---- Acceptance ----

export interface AcceptanceItemResponse {
  id: string
  acceptance_id: string
  order_item_id?: string
  item_name: string
  material_process?: string
  specification?: string
  quantity?: number
  unit?: string
  area?: number
  unit_price?: number
  subtotal?: number
  image_url?: string
  item_status: string
  remark?: string
  group_id?: string
  group_name?: string
}

export interface AcceptanceAttachmentResponse {
  id: string
  acceptance_id: string
  filename: string
  filepath: string
  filesize?: number
  upload_by?: string
}

export interface AcceptanceListResponse {
  id: string
  acceptance_no: string
  order_id?: string
  order_no?: string
  quote_id?: string
  quote_no?: string
  customer_name?: string
  project_name?: string
  department?: string
  total_amount: number
  status: string
  accepted_at?: string
  accepted_by?: string
  created_at: string
}

export interface AcceptanceDetailResponse extends AcceptanceListResponse {
  customer_phone?: string
  customer_address?: string
  contact_person?: string
  contact_phone?: string
  order_date?: string
  our_acceptor_id?: string
  our_acceptor_name?: string
  remark?: string
  reject_reason?: string
  discount_amount: number
  advance_amount: number
  updated_at: string
  items: AcceptanceItemResponse[]
  attachments: AcceptanceAttachmentResponse[]
}


// Customer tree for pricing center navigation
export interface CustomerTreeCustomer {
  id: string
  name: string
}
export interface CustomerTreeLevel {
  level: string
  customers: CustomerTreeCustomer[]
  count: number
}
export interface CustomerTreeNode {
  customer_type: string
  levels: CustomerTreeLevel[]
  count: number
}
