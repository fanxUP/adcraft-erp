import { get, post, patch, del, apiClient } from './index'
import type { PaginatedData } from '@/types/api'

// ── Types ──────────────────────────────────────────────────────────────────

export interface AerialVehicle {
  id: string
  plate_number: string
  vehicle_name: string
  brand_model?: string
  max_working_height?: string
  platform_capacity?: string
  purchase_date?: string
  status: string
  default_driver_id?: string
  default_driver_name?: string
  insurance_expire_date?: string
  inspection_expire_date?: string
  maintenance_due_date?: string
  remark?: string
  created_at?: string
  updated_at?: string
}

export interface AerialDriver {
  id: string
  driver_name: string
  phone?: string
  license_no?: string
  license_type?: string
  license_expire_date?: string
  is_external: boolean
  status: string
  remark?: string
  created_at?: string
  updated_at?: string
}

export interface AerialLedger {
  id: string
  ledger_no: string
  work_date: string
  aerial_vehicle_id: string
  plate_number?: string
  driver_id: string
  driver_name?: string
  assistant_names?: string
  customer_name?: string
  contact_name?: string
  contact_phone?: string
  related_order_no?: string
  related_task_no?: string
  work_location: string
  work_type?: string
  work_content?: string
  billing_method: string
  unit_price: number
  quantity: number
  receivable_amount: number
  discount_amount: number
  final_amount: number
  received_amount: number
  unpaid_amount: number
  settlement_type: string
  payment_status: string
  payment_method?: string
  payment_time?: string
  driver_wage_amount: number
  reimbursement_amount: number
  vehicle_direct_cost: number
  gross_profit: number
  estimated_profit: number
  abnormal_flag: boolean
  abnormal_description?: string
  status: string
  audit_status: string
  void_reason?: string
  remark?: string
  created_at?: string
  // detail fields
  planned_start_time?: string
  planned_end_time?: string
  actual_start_time?: string
  actual_end_time?: string
  start_mileage?: number
  end_mileage?: number
  distance_km?: number
  invoice_required?: boolean
  invoice_status?: string
  created_by?: string
  reviewed_by?: string
  reviewed_at?: string
  voided_by?: string
  voided_at?: string
}

export interface AerialDriverExpense {
  id: string
  ledger_id: string
  expense_date: string
  driver_id: string
  driver_name?: string
  expense_type: string
  amount: number
  payment_method?: string
  paid_by_driver: boolean
  receipt_url?: string
  description?: string
  review_status: string
  reimbursement_status: string
  reimbursed_at?: string
  created_at?: string
}

export interface AerialDriverWage {
  id: string
  ledger_id?: string
  wage_month?: string
  driver_id: string
  driver_name?: string
  wage_type: string
  base_wage: number
  trip_wage: number
  hourly_wage: number
  commission_amount: number
  allowance_amount: number
  deduction_amount: number
  final_wage_amount: number
  payment_status: string
  paid_at?: string
  remark?: string
  created_at?: string
}

export interface AerialVehicleCost {
  id: string
  aerial_vehicle_id: string
  plate_number?: string
  ledger_id?: string
  cost_date: string
  cost_type: string
  amount: number
  handler_id?: string
  payer_id?: string
  payment_method?: string
  is_driver_advance: boolean
  need_reimbursement: boolean
  receipt_url?: string
  allocation_type: string
  allocation_month?: string
  review_status: string
  remark?: string
  created_at?: string
}

export interface AerialSafetyCheck {
  id: string
  ledger_id: string
  check_type: string
  checker_id?: string
  vehicle_appearance_ok: boolean
  tire_ok: boolean
  brake_ok: boolean
  light_ok: boolean
  hydraulic_system_ok: boolean
  outriggers_ok: boolean
  platform_ok: boolean
  safety_belt_ok: boolean
  warning_equipment_ok: boolean
  extinguisher_ok: boolean
  documents_ok: boolean
  weather_ok: boolean
  site_risk_ok: boolean
  issue_description?: string
  photo_urls?: string
  check_result: string
  checked_at?: string
}

export interface AerialAttachment {
  id: string
  ledger_id: string
  attachment_type: string
  file_url: string
  file_name?: string
  uploaded_by?: string
  uploaded_at?: string
  remark?: string
}

// ── Vehicle API ────────────────────────────────────────────────────────────

export const getAerialVehicles = (params?: any) =>
  get<PaginatedData<AerialVehicle>>('/aerial/vehicles', { params })

export const getAerialVehicle = (id: string) =>
  get<AerialVehicle>(`/aerial/vehicles/${id}`)

export const createAerialVehicle = (data: any) =>
  post<AerialVehicle>('/aerial/vehicles', data)

export const updateAerialVehicle = (id: string, data: any) =>
  patch<AerialVehicle>(`/aerial/vehicles/${id}`, data)

// ── Driver API ─────────────────────────────────────────────────────────────

export const getAerialDrivers = (params?: any) =>
  get<PaginatedData<AerialDriver>>('/aerial/drivers', { params })

export const getAerialDriver = (id: string) =>
  get<AerialDriver>(`/aerial/drivers/${id}`)

export const createAerialDriver = (data: any) =>
  post<AerialDriver>('/aerial/drivers', data)

export const updateAerialDriver = (id: string, data: any) =>
  patch<AerialDriver>(`/aerial/drivers/${id}`, data)

// ── Ledger API ─────────────────────────────────────────────────────────────

export const getAerialLedgers = (params?: any) =>
  get<PaginatedData<AerialLedger>>('/aerial/ledgers', { params })

export const getAerialLedger = (id: string) =>
  get<AerialLedger>(`/aerial/ledgers/${id}`)

export const createAerialLedger = (data: any) =>
  post<AerialLedger>('/aerial/ledgers', data)

export const updateAerialLedger = (id: string, data: any) =>
  patch<AerialLedger>(`/aerial/ledgers/${id}`, data)

export const voidAerialLedger = (id: string, reason: string) =>
  post<AerialLedger>(`/aerial/ledgers/${id}/void`, { reason })

export const approveAerialLedger = (id: string, remark?: string) =>
  post<AerialLedger>(`/aerial/ledgers/${id}/approve`, { remark })

export const rejectAerialLedger = (id: string, remark?: string) =>
  post<AerialLedger>(`/aerial/ledgers/${id}/reject`, { remark })

// ── Driver Expense API ─────────────────────────────────────────────────────

export const getAerialDriverExpenses = (params?: any) =>
  get<PaginatedData<AerialDriverExpense>>('/aerial/driver-expenses', { params })

export const createAerialDriverExpense = (data: any) =>
  post<AerialDriverExpense>('/aerial/driver-expenses', data)

export const reviewAerialDriverExpense = (id: string, status: string, remark?: string) =>
  post<AerialDriverExpense>(`/aerial/driver-expenses/${id}/review`, { status, remark })

export const reimburseAerialDriverExpense = (id: string, remark?: string) =>
  post<AerialDriverExpense>(`/aerial/driver-expenses/${id}/reimburse`, { remark })

// ── Driver Wage API ────────────────────────────────────────────────────────

export const getAerialDriverWages = (params?: any) =>
  get<PaginatedData<AerialDriverWage>>('/aerial/driver-wages', { params })

export const createAerialDriverWage = (data: any) =>
  post<AerialDriverWage>('/aerial/driver-wages', data)

export const payAerialDriverWage = (id: string, remark?: string) =>
  post<AerialDriverWage>(`/aerial/driver-wages/${id}/pay`, { remark })

// ── Vehicle Cost API ───────────────────────────────────────────────────────

export const getAerialVehicleCosts = (params?: any) =>
  get<PaginatedData<AerialVehicleCost>>('/aerial/vehicle-costs', { params })

export const createAerialVehicleCost = (data: any) =>
  post<AerialVehicleCost>('/aerial/vehicle-costs', data)

export const reviewAerialVehicleCost = (id: string, status: string, remark?: string) =>
  post<AerialVehicleCost>(`/aerial/vehicle-costs/${id}/review`, { status, remark })

// ── Safety Check API ───────────────────────────────────────────────────────

export const getAerialSafetyChecks = (params?: any) =>
  get<AerialSafetyCheck[]>('/aerial/safety-checks', { params })

export const createAerialSafetyCheck = (data: any) =>
  post<AerialSafetyCheck>('/aerial/safety-checks', data)

// ── Attachment API ─────────────────────────────────────────────────────────

export const getAerialAttachments = (params?: any) =>
  get<AerialAttachment[]>('/aerial/attachments', { params })

export const createAerialAttachment = (data: any) =>
  post<AerialAttachment>('/aerial/attachments', data)

export const deleteAerialAttachment = (id: string) =>
  del(`/aerial/attachments/${id}`)

// ── Audit Log API ──────────────────────────────────────────────────────────

export const getAerialAuditLogs = (params?: any) =>
  get<PaginatedData<any>>('/aerial/audit-logs', { params })

// ── Dashboard API ──────────────────────────────────────────────────────────

export const getAerialDashboardOverview = () =>
  get<any>('/aerial/dashboard/overview')

export const getAerialDashboardToday = () =>
  get<AerialLedger[]>('/aerial/dashboard/today')

export const getAerialDashboardReminders = () =>
  get<any[]>('/aerial/dashboard/reminders')

// ── Report API ─────────────────────────────────────────────────────────────

export const getAerialReportDaily = (date: string) =>
  get<any>('/aerial/reports/daily', { params: { date } })

export const getAerialReportMonthly = (month: string) =>
  get<any>('/aerial/reports/monthly', { params: { month } })

export const getAerialReportReceivables = (params?: any) =>
  get<any>('/aerial/reports/receivables', { params })

export const getAerialReportReimbursements = (params?: any) =>
  get<any>('/aerial/reports/reimbursements', { params })

export const getAerialReportCosts = (month?: string) =>
  get<any[]>('/aerial/reports/costs', { params: { month } })

export const getAerialReportDriverSummary = (month: string) =>
  get<any[]>('/aerial/reports/driver-summary', { params: { month } })

// ── Export API ───────────────────────────────────────────────────────────────

export async function exportAerialLedgers(startDate: string, endDate: string) {
  const response = await apiClient.get('/aerial/reports/export/ledgers', {
    params: { start_date: startDate, end_date: endDate },
    responseType: 'blob',
  })
  const url = window.URL.createObjectURL(new Blob([response.data]))
  const link = document.createElement('a')
  link.href = url
  link.download = `出车台账_${startDate}_${endDate}.xlsx`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

export async function exportAerialWages(month: string) {
  const response = await apiClient.get('/aerial/reports/export/wages', {
    params: { month },
    responseType: 'blob',
  })
  const url = window.URL.createObjectURL(new Blob([response.data]))
  const link = document.createElement('a')
  link.href = url
  link.download = `驾驶员工资_${month}.xlsx`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

// ── Agent 草稿 API ─────────────────────────────────────────────────────────

export interface AerialAgentDraft {
  id: string
  platform: string
  conversation_id?: string
  sender_id?: string
  sender_name?: string
  raw_message: string
  intent: string
  confidence: number
  risk_level: string
  extracted?: Record<string, any>
  suggested_action?: string
  status: string
  confirmed_by?: string
  confirmed_at?: string
  reject_reason?: string
  created_ledger_id?: string
  created_expense_id?: string
  created_cost_id?: string
  created_at: string
}

export const ingestAerialAgentMessage = (data: {
  platform: string
  conversation_id?: string
  message_id?: string
  sender_id?: string
  sender_name?: string
  message_type?: string
  content: string
  attachments?: any[]
  sent_at?: string
}) => post<any>('/aerial/agent/messages/ingest', data)

export const getAerialAgentDrafts = (params?: any) =>
  get<PaginatedData<AerialAgentDraft>>('/aerial/agent/drafts', { params })

export const getAerialAgentDraft = (id: string) =>
  get<AerialAgentDraft>(`/aerial/agent/drafts/${id}`)

export const confirmAerialAgentDraft = (id: string, adjustments?: Record<string, any>) =>
  post<any>(`/aerial/agent/drafts/${id}/confirm`, { adjustments })

export const rejectAerialAgentDraft = (id: string, reason?: string) =>
  post<any>(`/aerial/agent/drafts/${id}/reject`, { reason })
