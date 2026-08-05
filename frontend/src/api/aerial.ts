import { get, post, patch, del, apiClient } from './index'
import type { PaginatedData } from '@/types/api'

// ── Types ──────────────────────────────────────────────────────────────────

export type AerialQueryParams = Record<string, string | number | boolean | undefined>
export type JsonValue = string | number | boolean | null | JsonObject | JsonValue[]
export interface JsonObject {
  [key: string]: JsonValue
}

export interface AerialVehicle {
  id: string
  plate_number: string
  vehicle_name: string
  brand_model?: string
  max_working_height?: string
  platform_capacity?: string
  purchase_date?: string
  status: string
  default_personnel_id?: string
  default_personnel_name?: string
  insurance_expire_date?: string
  inspection_expire_date?: string
  maintenance_due_date?: string
  remark?: string
  created_at?: string
  updated_at?: string
}

export type AerialVehicleCreate = Pick<AerialVehicle, 'plate_number' | 'vehicle_name'> &
  Partial<Omit<AerialVehicle, 'id' | 'plate_number' | 'vehicle_name' | 'created_at' | 'updated_at'>>
export type AerialVehicleUpdate = Partial<Omit<AerialVehicle, 'id' | 'created_at' | 'updated_at'>>

export interface AerialPersonnel {
  id: string
  name: string
  phone?: string
  gender?: string
  ethnicity?: string
  license_no?: string
  license_type?: string
  license_expire_date?: string
  is_external: boolean
  personnel_type?: string
  status: string
  remark?: string
  id_card_no?: string
  id_card_front_url?: string
  id_card_back_url?: string
  bank_card_no?: string
  bank_name?: string
  bank_account_name?: string
  created_at?: string
  updated_at?: string
}

export type AerialPersonnelCreate = Pick<AerialPersonnel, 'name'> &
  Partial<Omit<AerialPersonnel, 'id' | 'name' | 'created_at' | 'updated_at'>>
export type AerialPersonnelUpdate = Partial<Omit<AerialPersonnel, 'id' | 'created_at' | 'updated_at'>>

export interface AerialLedger {
  id: string
  ledger_no: string
  work_date: string
  aerial_vehicle_id: string
  plate_number?: string
  personnel_id: string
  name?: string
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
  personnel_wage_amount: number
  reimbursement_amount: number
  vehicle_direct_cost: number
  gross_profit: number
  estimated_profit: number
  abnormal_flag: boolean
  abnormal_description?: string
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
}

export type AerialLedgerCreate = Pick<
  AerialLedger,
  'work_date' | 'aerial_vehicle_id' | 'personnel_id' | 'work_location'
> &
  Partial<Omit<AerialLedger, 'id' | 'ledger_no' | 'created_at'>>
export type AerialLedgerUpdate = Partial<Omit<AerialLedger, 'id' | 'ledger_no' | 'created_at'>>

export interface AerialPersonnelExpense {
  id: string
  ledger_id: string
  expense_date: string
  personnel_id: string
  name?: string
  expense_type: string
  amount: number
  payment_method?: string
  paid_by_personnel: boolean
  receipt_url?: string
  description?: string
  review_status: string
  reimbursement_status: string
  reimbursed_at?: string
  created_at?: string
}

export type AerialPersonnelExpenseCreate = Pick<
  AerialPersonnelExpense,
  'ledger_id' | 'expense_date' | 'personnel_id' | 'expense_type' | 'amount'
> &
  Partial<Omit<AerialPersonnelExpense, 'id' | 'created_at'>>

export interface AerialPersonnelWage {
  id: string
  ledger_id?: string
  wage_month?: string
  personnel_id: string
  name?: string
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

export type AerialPersonnelWageCreate = Pick<AerialPersonnelWage, 'personnel_id'> &
  Partial<Omit<AerialPersonnelWage, 'id' | 'created_at'>>

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
  payer_name?: string
  payment_method?: string
  is_personnel_advance: boolean
  need_reimbursement: boolean
  receipt_url?: string
  allocation_type: string
  allocation_month?: string
  review_status: string
  remark?: string
  created_at?: string
}

export type AerialVehicleCostCreate = Pick<
  AerialVehicleCost,
  'aerial_vehicle_id' | 'cost_date' | 'cost_type' | 'amount'
> &
  Partial<Omit<AerialVehicleCost, 'id' | 'created_at'>>

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

export type AerialSafetyCheckCreate = Pick<AerialSafetyCheck, 'ledger_id' | 'check_type'> &
  Partial<Omit<AerialSafetyCheck, 'id' | 'checked_at'>>

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

export type AerialAttachmentCreate = Pick<AerialAttachment, 'ledger_id' | 'file_url'> &
  Partial<Omit<AerialAttachment, 'id' | 'uploaded_at'>>

export interface AerialSummary {
  work_days?: number
  trip_count: number
  receivable: number
  received: number
  unpaid: number
  wages: number
  reimbursements: number
  vehicle_costs: number
  gross_profit: number
  avg_trip_revenue?: number
  avg_trip_cost?: number
  avg_trip_profit?: number
}

export interface AerialDashboardOverview {
  today: AerialSummary
  monthly: AerialSummary
}

export interface AerialReminder {
  type: 'insurance' | 'inspection' | 'maintenance'
  vehicle: string
  plate: string
  expire_date?: string
  due_date?: string
  days_left: number
  urgent: boolean
}

export interface AerialReceivablesReport {
  items: AerialLedger[]
  total: number
  total_unpaid: number
}

export interface AerialReimbursementsReport {
  pending_reimbursement: AerialPersonnelExpense[]
  pending_reimbursement_total: number
}

export interface AerialCostReportItem {
  cost_type: string
  total_amount: number
  count: number
}

export interface AerialPersonnelSummaryItem {
  personnel_id: string
  name: string
  trip_count: number
  total_wage: number
  total_expense: number
  total_reimbursement: number
}

// ── Vehicle API ────────────────────────────────────────────────────────────

export const getAerialVehicles = (params?: AerialQueryParams) =>
  get<PaginatedData<AerialVehicle>>('/aerial/vehicles', { params })

export const getAerialVehicle = (id: string) =>
  get<AerialVehicle>(`/aerial/vehicles/${id}`)

export const createAerialVehicle = (data: AerialVehicleCreate) =>
  post<AerialVehicle>('/aerial/vehicles', data)

export const updateAerialVehicle = (id: string, data: AerialVehicleUpdate) =>
  patch<AerialVehicle>(`/aerial/vehicles/${id}`, data)

export const deleteAerialVehicle = (id: string) =>
  del(`/aerial/vehicles/${id}`)

// ── Personnel API ─────────────────────────────────────────────────────────────

export const getAerialPersonnel = (params?: AerialQueryParams) =>
  get<PaginatedData<AerialPersonnel>>('/aerial/personnel', { params })

export const getAerialPersonnelItem = (id: string) =>
  get<AerialPersonnel>(`/aerial/personnel/${id}`)

export const createAerialPersonnel = (data: AerialPersonnelCreate) =>
  post<AerialPersonnel>('/aerial/personnel', data)

export const updateAerialPersonnel = (id: string, data: AerialPersonnelUpdate) =>
  patch<AerialPersonnel>(`/aerial/personnel/${id}`, data)

export const deleteAerialPersonnel = (id: string) =>
  del(`/aerial/personnel/${id}`)

// ── Ledger API ─────────────────────────────────────────────────────────────

export interface AerialLedgerSummary {
  trip_count: number
  quantity: number
  receivable_amount: number
  received_amount: number
  unpaid_amount: number
}

export type AerialLedgerListResult = PaginatedData<AerialLedger> & { summary?: AerialLedgerSummary }

export const getAerialLedgers = (params?: AerialQueryParams) =>
  get<AerialLedgerListResult>('/aerial/ledgers', { params })

export const getAerialLedger = (id: string) =>
  get<AerialLedger>(`/aerial/ledgers/${id}`)

export const getAerialLedgerLocations = () =>
  get<string[]>('/aerial/ledgers/locations')

export const createAerialLedger = (data: AerialLedgerCreate) =>
  post<AerialLedger>('/aerial/ledgers', data)

export const updateAerialLedger = (id: string, data: AerialLedgerUpdate) =>
  patch<AerialLedger>(`/aerial/ledgers/${id}`, data)

export const settleAerialLedger = (id: string, data: { amount: number; payment_method?: string; payment_time?: string; payee_id?: string; remark?: string }) =>
  post<AerialLedger>(`/aerial/ledgers/${id}/settle`, data)

export interface AerialSettlement {
  id: string
  ledger_id: string
  amount: number
  payment_method?: string
  payment_time?: string
  payee_id?: string
  payee_name?: string
  remark?: string
  created_by?: string
  created_at?: string
}

export const getAerialLedgerSettlements = (id: string) =>
  get<AerialSettlement[]>(`/aerial/ledgers/${id}/settlements`)

export const deleteAerialLedgerSettlement = (ledgerId: string, settlementId: string) =>
  del(`/aerial/ledgers/${ledgerId}/settlements/${settlementId}`)

export const deleteAerialLedger = (id: string) =>
  del(`/aerial/ledgers/${id}`)

// ── Attendance API ───────────────────────────────────────────────────────────

export interface AerialAttendanceRecord {
  id: string
  att_date: string
  target_type: string // vehicle / personnel
  vehicle_id?: string
  personnel_id?: string
  status: string // present / half_day / overtime / absent / maintenance
  check_in_time?: string | null
  check_out_time?: string | null
  overtime_hours?: number | null
  remark?: string
  source?: string
  created_at?: string
  updated_at?: string
}

export type AerialAttendanceCreate = Pick<AerialAttendanceRecord, 'att_date' | 'target_type'> &
  Partial<Omit<AerialAttendanceRecord, 'id' | 'created_at' | 'updated_at'>>
export type AerialAttendanceUpdate = Partial<Omit<AerialAttendanceRecord, 'id' | 'created_at' | 'updated_at'>>

export const getAerialAttendance = (params?: AerialQueryParams) =>
  get<PaginatedData<AerialAttendanceRecord>>('/aerial/attendance', { params })

export const createAerialAttendance = (data: AerialAttendanceCreate) =>
  post<AerialAttendanceRecord>('/aerial/attendance', data)

export const updateAerialAttendance = (id: string, data: AerialAttendanceUpdate) =>
  patch<AerialAttendanceRecord>(`/aerial/attendance/${id}`, data)

export const deleteAerialAttendance = (id: string) =>
  del(`/aerial/attendance/${id}`)

// ── Personnel Attachment API ─────────────────────────────────────────────────

export interface AerialPersonnelAttachment {
  id: string
  personnel_id: string
  attachment_type: string // id_card / license / qualification / bank_card / insurance / other
  file_url: string
  file_name?: string
  uploaded_by?: string
  uploaded_at?: string
  remark?: string
}

export const uploadAerialPersonnelImage = async (file: File) => {
  const form = new FormData()
  form.append('file', file)
  return post<{ file_url: string; file_name: string; file_size: number }>('/aerial/personnel/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export const getAerialPersonnelAttachments = (personnelId: string) =>
  get<AerialPersonnelAttachment[]>(`/aerial/personnel/${personnelId}/attachments`)

export const createAerialPersonnelAttachment = async (personnelId: string, file: File, attachmentType: string) => {
  const form = new FormData()
  form.append('file', file)
  form.append('attachment_type', attachmentType)
  return post<AerialPersonnelAttachment>(`/aerial/personnel/${personnelId}/attachments`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export const deleteAerialPersonnelAttachment = (id: string) =>
  del(`/aerial/personnel/attachments/${id}`)

// ── Vehicle Attachment API ──────────────────────────────────────────────────

export interface AerialVehicleAttachment {
  id: string
  vehicle_id: string
  attachment_type: string // license / registration / insurance / inspection / maintenance / other
  file_url: string
  file_name?: string
  uploaded_by?: string
  uploaded_at?: string
  remark?: string
}

export const getAerialVehicleAttachments = (vehicleId: string) =>
  get<AerialVehicleAttachment[]>(`/aerial/vehicles/${vehicleId}/attachments`)

export const createAerialVehicleAttachment = async (vehicleId: string, file: File, attachmentType: string) => {
  const form = new FormData()
  form.append('file', file)
  form.append('attachment_type', attachmentType)
  return post<AerialVehicleAttachment>(`/aerial/vehicles/${vehicleId}/attachments`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export const deleteAerialVehicleAttachment = (id: string) =>
  del(`/aerial/vehicles/attachments/${id}`)

// ── Expiry Reminder API ──────────────────────────────────────────────────────

export interface AerialExpiringVehicle {
  vehicle_id: string
  plate_number: string
  vehicle_name: string
  insurance_expire_date?: string | null
  insurance_days_left?: number | null
  insurance_urgency?: string | null
  inspection_expire_date?: string | null
  inspection_days_left?: number | null
  inspection_urgency?: string | null
}

export const getAerialExpiringVehicles = (days = 30) =>
  get<AerialExpiringVehicle[]>('/aerial/vehicles/expiring', { params: { days } })

export const checkAerialExpiryNotifications = (days = 30) =>
  post<{ created: number; total: number }>('/aerial/vehicles/expiry-notifications/check', undefined, { params: { days } })

// ── Personnel Expense API ─────────────────────────────────────────────────────

export const getAerialPersonnelExpenses = (params?: AerialQueryParams) =>
  get<PaginatedData<AerialPersonnelExpense>>('/aerial/personnel-expenses', { params })

export const createAerialPersonnelExpense = (data: AerialPersonnelExpenseCreate) =>
  post<AerialPersonnelExpense>('/aerial/personnel-expenses', data)

export const reimburseAerialPersonnelExpense = (id: string, remark?: string) =>
  post<AerialPersonnelExpense>(`/aerial/personnel-expenses/${id}/reimburse`, { remark })

// ── Personnel Wage API ────────────────────────────────────────────────────────

export const getAerialPersonnelWages = (params?: AerialQueryParams) =>
  get<PaginatedData<AerialPersonnelWage>>('/aerial/personnel-wages', { params })

export const createAerialPersonnelWage = (data: AerialPersonnelWageCreate) =>
  post<AerialPersonnelWage>('/aerial/personnel-wages', data)

export const payAerialPersonnelWage = (id: string, remark?: string) =>
  post<AerialPersonnelWage>(`/aerial/personnel-wages/${id}/pay`, { remark })

// ── Vehicle Cost API ───────────────────────────────────────────────────────

export const getAerialVehicleCosts = (params?: AerialQueryParams) =>
  get<PaginatedData<AerialVehicleCost>>('/aerial/vehicle-costs', { params })

export const createAerialVehicleCost = (data: AerialVehicleCostCreate) =>
  post<AerialVehicleCost>('/aerial/vehicle-costs', data)

// ── Safety Check API ───────────────────────────────────────────────────────

export const getAerialSafetyChecks = (params?: AerialQueryParams) =>
  get<AerialSafetyCheck[]>('/aerial/safety-checks', { params })

export const createAerialSafetyCheck = (data: AerialSafetyCheckCreate) =>
  post<AerialSafetyCheck>('/aerial/safety-checks', data)

// ── Attachment API ─────────────────────────────────────────────────────────

export const getAerialAttachments = (params?: AerialQueryParams) =>
  get<AerialAttachment[]>('/aerial/attachments', { params })

export const createAerialAttachment = (data: AerialAttachmentCreate) =>
  post<AerialAttachment>('/aerial/attachments', data)

export const deleteAerialAttachment = (id: string) =>
  del(`/aerial/attachments/${id}`)

// ── Dashboard API ──────────────────────────────────────────────────────────

export const getAerialDashboardOverview = () =>
  get<AerialDashboardOverview>('/aerial/dashboard/overview')

export const getAerialDashboardToday = () =>
  get<AerialLedger[]>('/aerial/dashboard/today')

export const getAerialDashboardReminders = () =>
  get<AerialReminder[]>('/aerial/dashboard/reminders')

// ── Report API ─────────────────────────────────────────────────────────────

export const getAerialReportDaily = (date: string) =>
  get<AerialSummary & { ledgers: AerialLedger[] }>('/aerial/reports/daily', { params: { date } })

export const getAerialReportMonthly = (month: string) =>
  get<AerialSummary>('/aerial/reports/monthly', { params: { month } })

export const getAerialReportReceivables = (params?: AerialQueryParams) =>
  get<AerialReceivablesReport>('/aerial/reports/receivables', { params })

export const getAerialReportReimbursements = (params?: AerialQueryParams) =>
  get<AerialReimbursementsReport>('/aerial/reports/reimbursements', { params })

export const getAerialReportCosts = (month?: string) =>
  get<AerialCostReportItem[]>('/aerial/reports/costs', { params: { month } })

export const getAerialReportPersonnelSummary = (month: string) =>
  get<AerialPersonnelSummaryItem[]>('/aerial/reports/personnel-summary', { params: { month } })

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
  link.download = `人员工资_${month}.xlsx`
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
  extracted?: JsonObject
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

export interface AerialAgentIngestResult {
  draft_id?: string
  intent: string
  confidence: number
  risk_level: string
  suggested_action?: string
  query_result?: JsonObject
  extracted?: JsonObject
  requires_confirmation?: boolean
  message?: string
}

export interface AerialAgentActionResult {
  success: boolean
  error?: string
  ids?: JsonObject
}

export const ingestAerialAgentMessage = (data: {
  platform: string
  conversation_id?: string
  message_id?: string
  sender_id?: string
  sender_name?: string
  message_type?: string
  content: string
  attachments?: JsonObject[]
  sent_at?: string
}) => post<AerialAgentIngestResult>('/aerial/agent/messages/ingest', data)

export const getAerialAgentDrafts = (params?: AerialQueryParams) =>
  get<PaginatedData<AerialAgentDraft>>('/aerial/agent/drafts', { params })

export const getAerialAgentDraft = (id: string) =>
  get<AerialAgentDraft>(`/aerial/agent/drafts/${id}`)

export const confirmAerialAgentDraft = (id: string, adjustments?: JsonObject) =>
  post<AerialAgentActionResult>(`/aerial/agent/drafts/${id}/confirm`, { adjustments })

export const rejectAerialAgentDraft = (id: string, reason?: string) =>
  post<AerialAgentActionResult>(`/aerial/agent/drafts/${id}/reject`, { reason })
