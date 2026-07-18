// ============================================================
// Shared API response types — mirrors backend Pydantic schemas
// Interceptor unwraps ApiResponse<Data>, so these are the inner
// `Data` shapes that every `get<T>()` / `post<T>()` returns.
// ============================================================

// ---- Common ----

export interface PaginatedData<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

// ---- Auth ----

export interface LoginResponse {
  token: string
  username: string
  real_name?: string
}

export interface UserProfile {
  id: string
  username: string
  real_name?: string
  phone?: string
  email?: string
  is_active: boolean
  roles: string[]
}

// ---- User ----

export interface UserResponse {
  id: string
  username: string
  real_name?: string
  phone?: string
  email?: string
  is_active: boolean
  created_at?: string
  roles: string[]
}

// ---- Customer ----

export interface ContactResponse {
  id: string
  name: string
  phone?: string
  wechat?: string
  position?: string
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
  total_amount: number
  paid_amount: number
  unpaid_amount: number
  department?: string
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
  unit_price: number
  process_fee: number
  installation_fee: number
  design_fee: number
  transport_fee: number
  other_fee: number
  subtotal_amount: number
  remark?: string
  image_url?: string
  sort_order: number
  group_name?: string
  material_process?: string
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
  total_amount: number
  paid_amount: number
  unpaid_amount: number
  delivery_deadline?: string
  installation_address?: string
  remark?: string
  department?: string
  contact_person?: string
  contact_phone?: string
  created_at?: string
  items: OrderItemResponse[]
  status_logs: OrderStatusLogResponse[]
  cost_amount?: number
  gross_profit?: number
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

export interface DesignTaskResponse {
  id: string
  design_no: string
  order_id: string
  customer_id: string
  project_name: string
  status: string
  assigned_to?: string
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
  customer_id: string
  project_name: string
  status: string
  assigned_to?: string
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
  customer_id: string
  project_name: string
  status: string
  assigned_to?: string
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
  unit: string
  pricing_method: string
  default_price: number
  min_charge: number
  remark?: string
  is_active: boolean
  created_at?: string
}

export interface MaterialResponse {
  id: string
  name: string
  spec?: string
  unit: string
  purchase_price: number
  sale_price: number
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
  default_price: number
  remark?: string
  is_active: boolean
  created_at?: string
}

// ---- Payment / Statement / Expense ----

export interface PaymentResponse {
  id: string
  payment_no: string
  order_id: string
  order_no?: string
  customer_id: string
  customer_name?: string
  project_name?: string
  amount: number
  payment_method?: string
  paid_at?: string
  remark?: string
  is_voided: boolean
  void_reason?: string
  voided_at?: string
  receipt_url?: string
  created_at?: string
  created_by?: string
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
  confirmed_at?: string
  confirmed_by?: string
  created_at?: string
}

export interface StatementOrderItem {
  id: string
  order_no: string
  project_name: string
  status: string
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
  amount: number
  description?: string
  expense_date?: string
  receipt_url?: string
  created_by?: string
  created_at?: string
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
  quote_item_id?: string
  order_item_name?: string
  quote_item_name?: string
  group_name?: string
  customer_id?: string
  customer_name?: string
  project_name?: string
  category: string
  amount: number
  quantity?: number
  unit?: string
  unit_price?: number
  payment_method?: string
  payee_company_name?: string
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
  status: string
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
  contact_person?: string
  phone?: string
  address?: string
  service_type?: string
  coop_rating?: string
  remark?: string
  is_active: boolean
  created_at?: string
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
  task_type: string
  description?: string
  quantity: number
  unit_price: number
  total_amount: number
  paid_amount: number
  unpaid_amount: number
  status: string
  expected_at?: string
  completed_at?: string
  remark?: string
  created_at?: string
  deleted_at?: string
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
  process_fee: number
  installation_fee: number
  design_fee: number
  transport_fee: number
  other_fee: number
  subtotal_amount: number
  remark?: string
  image_url?: string
  sort_order: number
  group_name?: string
  material_process?: string
  specification?: string
}

export interface QuoteListResponse {
  id: string
  quote_no: string
  customer_id?: string
  customer_name?: string
  project_name: string
  status: string
  total_amount: number
  valid_until?: string
  created_at?: string
  department?: string
  contact_person?: string
  contact_phone?: string
}

export interface QuoteDetailResponse {
  id: string
  quote_no: string
  customer_id?: string
  customer_name?: string
  project_name: string
  sales_user_id?: string
  status: string
  subtotal_amount: number
  discount_amount: number
  tax_rate: number
  tax_amount: number
  total_amount: number
  valid_until?: string
  remark?: string
  department?: string
  contact_person?: string
  contact_phone?: string
  created_at?: string
  items: QuoteItemResponse[]
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
  sign_date?: string
  start_date?: string
  end_date?: string
  created_at?: string
}

export interface SimpleOrderRef {
  id: string
  order_no: string
  project_name: string
  total_amount: number
}

export interface SimpleQuoteRef {
  id: string
  quote_no: string
  project_name: string
  total_amount: number
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
  quotes: SimpleQuoteRef[]
}

export interface ContractResourceItem {
  id: string
  order_no?: string
  quote_no?: string
  project_name: string
  customer_id?: string
  customer_name?: string
}

export interface ContractAvailableResources {
  orders: ContractResourceItem[]
  quotes: ContractResourceItem[]
  used_project_names: string[]
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
  contract_type?: string
}

export interface CustomerDebtOrder {
  id: string
  order_no: string
  project_name: string
  total_amount: number
  paid_amount: number
  unpaid_amount: number
  status: string
}

export interface CustomerDebtQuote {
  id: string
  quote_no: string
  project_name: string
  total_amount: number
  status: string
}

export interface CustomerDebtItem {
  customer_id: string
  customer_name: string
  debt_amount: number
  total_order_amount: number
  total_paid: number
  contract_count: number
  order_count: number
  quote_count: number
  last_payment_date: string | null
  contracts: CustomerDebtContract[]
  orders: CustomerDebtOrder[]
  quotes: CustomerDebtQuote[]
}

export interface DashboardData {
  today_order_amount: number
  today_payment_amount: number
  month_order_amount: number
  month_payment_amount: number
  month_unpaid_amount: number
  pending_design_count: number
  pending_production_count: number
  pending_installation_count: number
  overdue_order_count: number
  customer_debt_ranking: CustomerDebtItem[]
}

export interface DailyReportOrder {
  order_no: string
  project_name: string
  total_amount: number
  paid_amount: number
  unpaid_amount: number
  status: string
}

export interface DailyReportPayment {
  payment_no: string
  amount: number
  payment_method?: string
  is_voided: boolean
}

export interface DailyReportData {
  date: string
  order_count: number
  order_amount: number
  payment_count: number
  payment_amount: number
  new_customer_count: number
  orders: DailyReportOrder[]
  payments: DailyReportPayment[]
}

export interface MonthlyReportOrder {
  order_no: string
  project_name: string
  total_amount: number
  paid_amount: number
  unpaid_amount: number
  status: string
}

export interface MonthlyReportData {
  order_count: number
  order_amount: number
  payment_count: number
  payment_amount: number
  unpaid_amount: number
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
  length?: number
  width?: number
  height?: number
  quantity: number
  unit: string
  product_id?: string
  material_id?: string
  process_id?: string
  unit_price?: number
  design_fee: number
  installation_fee: number
  process_fee: number
  transport_fee: number
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
  order_id: string
  order_no?: string
  customer_name?: string
  project_name?: string
  department?: string
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
