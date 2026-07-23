import { get, post, patch, del } from './index'
import { PaginatedData } from '@/types/api'

export interface VehicleResponse {
  id: string
  vehicle_code: string
  plate_number: string
  vehicle_name: string
  vehicle_type: string
  brand_model?: string
  color?: string
  purchase_date?: string
  status: string
  department?: string
  default_driver_id?: string
  default_driver_name?: string
  load_capacity?: string
  seats?: number
  vehicle_photo_url?: string
  license_photo_url?: string
  remark?: string
  created_at?: string
  updated_at?: string
}

export interface VehicleCreateData {
  vehicle_code: string
  plate_number: string
  vehicle_name: string
  vehicle_type: string
  brand_model?: string
  color?: string
  purchase_date?: string
  department?: string
  default_driver_id?: string
  load_capacity?: string
  seats?: number
  vehicle_photo_url?: string
  license_photo_url?: string
  remark?: string
}

export interface VehicleUpdateData {
  vehicle_code?: string
  plate_number?: string
  vehicle_name?: string
  vehicle_type?: string
  brand_model?: string
  color?: string
  purchase_date?: string
  department?: string
  default_driver_id?: string
  load_capacity?: string
  seats?: number
  vehicle_photo_url?: string
  license_photo_url?: string
  remark?: string
}

export interface VehicleDriverResponse {
  id: string
  employee_id?: string
  employee_name?: string
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

// ── 车辆 ──────────────────────────────────────────────────────────────────

export function getVehicles(params: {
  page?: number
  page_size?: number
  keyword?: string
  vehicle_type?: string
  status?: string
  driver_id?: string
}) {
  return get<PaginatedData<VehicleResponse>>('/vehicles/', { params })
}

export function getVehicle(id: string) {
  return get<VehicleResponse>(`/vehicles/${id}`)
}

export function createVehicle(data: VehicleCreateData) {
  return post<VehicleResponse>('/vehicles/', data)
}

export function updateVehicle(id: string, data: VehicleUpdateData) {
  return patch<VehicleResponse>(`/vehicles/${id}`, data)
}

export function disableVehicle(id: string) {
  return post<VehicleResponse>(`/vehicles/${id}/disable`)
}

export function enableVehicle(id: string) {
  return post<VehicleResponse>(`/vehicles/${id}/enable`)
}

export function scrapVehicle(id: string) {
  return post<VehicleResponse>(`/vehicles/${id}/scrap`)
}

// ── 司机 ──────────────────────────────────────────────────────────────────

export function getDrivers(params: {
  page?: number
  page_size?: number
  keyword?: string
  status?: string
}) {
  return get<PaginatedData<VehicleDriverResponse>>('/vehicle-drivers/', { params })
}

export function getDriver(id: string) {
  return get<VehicleDriverResponse>(`/vehicle-drivers/${id}`)
}

export function createDriver(data: Partial<VehicleDriverResponse>) {
  return post<VehicleDriverResponse>('/vehicle-drivers/', data)
}

export function updateDriver(id: string, data: Partial<VehicleDriverResponse>) {
  return patch<VehicleDriverResponse>(`/vehicle-drivers/${id}`, data)
}

export function disableDriver(id: string) {
  return post<VehicleDriverResponse>(`/vehicle-drivers/${id}/disable`)
}

export function enableDriver(id: string) {
  return post<VehicleDriverResponse>(`/vehicle-drivers/${id}/enable`)
}

// ── 油费记录 ──────────────────────────────────────────────────────────────────

export interface FuelRecordResponse {
  id: string
  vehicle_id: string
  vehicle_name?: string
  plate_number?: string
  driver_id?: string
  driver_name?: string
  dispatch_id?: string
  dispatch_no?: string
  fuel_time?: string
  amount: number
  liters?: number
  unit_price?: number
  gas_station?: string
  mileage?: number
  payment_method?: string
  payer_id?: string
  payer_name?: string
  is_driver_advance: boolean
  receipt_url?: string
  status: string
  remark?: string
  created_at?: string
  updated_at?: string
}

export function getFuelRecords(params: {
  page?: number
  page_size?: number
  vehicle_id?: string
  driver_id?: string
  status?: string
}) {
  return get<PaginatedData<FuelRecordResponse>>('/vehicle-fuel-records/', { params })
}

export function createFuelRecord(data: Partial<FuelRecordResponse>) {
  return post<FuelRecordResponse>('/vehicle-fuel-records/', data)
}

export function updateFuelRecord(id: string, data: Partial<FuelRecordResponse>) {
  return patch<FuelRecordResponse>(`/vehicle-fuel-records/${id}`, data)
}

export function reviewFuelRecord(id: string, data: { status: string; remark?: string }) {
  return post<FuelRecordResponse>(`/vehicle-fuel-records/${id}/review`, data)
}

// ── 维修保养记录 ──────────────────────────────────────────────────────────────

export interface MaintenanceRecordResponse {
  id: string
  vehicle_id: string
  vehicle_name?: string
  plate_number?: string
  maintenance_type: string
  maintenance_date?: string
  maintenance_item?: string
  repair_shop?: string
  amount: number
  mileage?: number
  next_maintenance_mileage?: number
  next_maintenance_date?: string
  handler_id?: string
  handler_name?: string
  invoice_url?: string
  before_photo_url?: string
  after_photo_url?: string
  status: string
  remark?: string
  created_at?: string
  updated_at?: string
}

export function getMaintenanceRecords(params: {
  page?: number
  page_size?: number
  vehicle_id?: string
  maintenance_type?: string
  status?: string
}) {
  return get<PaginatedData<MaintenanceRecordResponse>>('/vehicle-maintenance-records/', { params })
}

export function createMaintenanceRecord(data: Partial<MaintenanceRecordResponse>) {
  return post<MaintenanceRecordResponse>('/vehicle-maintenance-records/', data)
}

export function updateMaintenanceRecord(id: string, data: Partial<MaintenanceRecordResponse>) {
  return patch<MaintenanceRecordResponse>(`/vehicle-maintenance-records/${id}`, data)
}

export function reviewMaintenanceRecord(id: string, data: { status: string; remark?: string }) {
  return post<MaintenanceRecordResponse>(`/vehicle-maintenance-records/${id}/review`, data)
}

// ── 通用费用 ──────────────────────────────────────────────────────────────────

export interface CostAllocationResponse {
  id: string
  source_type: string
  source_id?: string
  vehicle_id: string
  vehicle_name?: string
  plate_number?: string
  dispatch_id?: string
  related_order_id?: string
  related_install_task_id?: string
  cost_type: string
  amount: number
  allocation_method: string
  allocation_date?: string
  remark?: string
  created_at?: string
  updated_at?: string
}

export function getCostAllocations(params: {
  page?: number
  page_size?: number
  vehicle_id?: string
  cost_type?: string
  source_type?: string
}) {
  return get<PaginatedData<CostAllocationResponse>>('/vehicle-cost-records/', { params })
}

export function createCostAllocation(data: Partial<CostAllocationResponse>) {
  return post<CostAllocationResponse>('/vehicle-cost-records/', data)
}

// ── 保险/年检/证件 ──────────────────────────────────────────────────────

export interface CertificateResponse {
  id: string
  vehicle_id?: string
  vehicle_name?: string
  plate_number?: string
  driver_id?: string
  driver_name?: string
  certificate_type: string
  certificate_no?: string
  start_date?: string
  expire_date?: string
  amount: number
  file_url?: string
  reminder_days: number
  status: string
  remark?: string
  urgency?: string
  days_left?: number
  created_at?: string
  updated_at?: string
}

export function getCertificates(params: {
  page?: number
  page_size?: number
  vehicle_id?: string
  certificate_type?: string
  status?: string
}) {
  return get<PaginatedData<CertificateResponse>>('/vehicle-certificates/', { params })
}

export function getExpiringCertificates(params?: {
  days?: number
  vehicle_id?: string
}) {
  return get<CertificateResponse[]>('/vehicle-certificates/expiring', { params })
}

export function createCertificate(data: Partial<CertificateResponse>) {
  return post<CertificateResponse>('/vehicle-certificates/', data)
}

export function updateCertificate(id: string, data: Partial<CertificateResponse>) {
  return patch<CertificateResponse>(`/vehicle-certificates/${id}`, data)
}

export function deleteCertificate(id: string) {
  return del(`/vehicle-certificates/${id}`)
}

// ── 违章/事故/异常 ──────────────────────────────────────────────────────────

export interface IncidentResponse {
  id: string
  vehicle_id?: string
  vehicle_name?: string
  plate_number?: string
  driver_id?: string
  driver_name?: string
  dispatch_id?: string
  dispatch_no?: string
  related_order_id?: string
  related_install_task_id?: string
  incident_type: string
  incident_time?: string
  location?: string
  description?: string
  fine_amount: number
  points_deducted: number
  repair_amount: number
  responsible_user_id?: string
  responsible_user_name?: string
  status: string
  resolution?: string
  evidence_url?: string
  remark?: string
  created_at?: string
  updated_at?: string
}

export function getIncidents(params: {
  page?: number
  page_size?: number
  vehicle_id?: string
  incident_type?: string
  status?: string
  driver_id?: string
}) {
  return get<PaginatedData<IncidentResponse>>('/vehicle-incidents/', { params })
}

export function createIncident(data: Partial<IncidentResponse>) {
  return post<IncidentResponse>('/vehicle-incidents/', data)
}

export function updateIncident(id: string, data: Partial<IncidentResponse>) {
  return patch<IncidentResponse>(`/vehicle-incidents/${id}`, data)
}

export function resolveIncident(id: string, data: { resolution: string; status?: string }) {
  return post<IncidentResponse>(`/vehicle-incidents/${id}/resolve`, data)
}

export function deleteIncident(id: string) {
  return del(`/vehicle-incidents/${id}`)
}

// ── 车辆报表 ─────────────────────────────────────────────────────────────────

export interface VehicleReportOverview {
  total_vehicles: number
  available_vehicles: number
  month_dispatches: number
  month_mileage: number
  month_fuel_cost: number
  month_maintenance_cost: number
  month_insurance_cost: number
  month_incident_cost: number
  month_allocation_cost: number
  month_total_cost: number
  avg_cost_per_dispatch: number
  avg_cost_per_km: number
  year: number
  month: number
}

export interface VehicleCostItem {
  vehicle_id: string
  vehicle_name?: string
  plate_number?: string
  fuel_cost: number
  maintenance_cost: number
  insurance_cost: number
  incident_cost: number
  allocation_cost: number
  total_cost: number
  total_mileage: number
  dispatch_count: number
  avg_cost_per_km: number
  avg_cost_per_dispatch: number
}

export interface DriverStatItem {
  driver_id?: string
  driver_name?: string
  phone?: string
  dispatch_count: number
  total_mileage: number
}

export interface MileageStatItem {
  month: number
  total_mileage: number
  dispatch_count: number
}

export interface DispatchStats {
  by_status: { status: string; count: number }[]
  by_reason: { reason: string; count: number }[]
}

export interface OrderCostItem {
  order_id: string
  dispatch_count: number
  total_mileage: number
  allocated_cost: number
}

export interface CostTypeItem {
  cost_type: string
  amount: number
}

export function getVehicleReportOverview(params: { year?: number; month?: number } = {}) {
  return get<VehicleReportOverview>('/vehicle-reports/overview', { params })
}

export function getVehicleCosts(params: {
  year?: number; month?: number; start_date?: string; end_date?: string
} = {}) {
  return get<VehicleCostItem[]>('/vehicle-reports/costs', { params })
}

export function getDriverStats(params: {
  year?: number; month?: number; start_date?: string; end_date?: string
} = {}) {
  return get<DriverStatItem[]>('/vehicle-reports/drivers', { params })
}

export function getMileageStats(params: { year?: number; vehicle_id?: string } = {}) {
  return get<MileageStatItem[]>('/vehicle-reports/mileage', { params })
}

export function getDispatchReportStats(params: {
  year?: number; month?: number; start_date?: string; end_date?: string
} = {}) {
  return get<DispatchStats>('/vehicle-reports/dispatches', { params })
}

export function getOrderVehicleCosts(params: {
  year?: number; month?: number; start_date?: string; end_date?: string
} = {}) {
  return get<OrderCostItem[]>('/vehicle-reports/order-costs', { params })
}

export function getCostByType(params: {
  year?: number; month?: number; start_date?: string; end_date?: string
} = {}) {
  return get<CostTypeItem[]>('/vehicle-reports/cost-types', { params })
}

// ── Agent 消息识别草稿 ──────────────────────────────────────────────────────

export interface AgentDraftResponse {
  id: string
  intent: string
  confidence: number
  risk_level: string
  status: string
  platform: string
  conversation_id?: string
  message_id?: string
  sender_name?: string
  sender_id?: string
  original_content: string
  extracted_data?: Record<string, string | number | boolean | null>
  suggested_action?: string
  requires_confirmation: boolean
  requires_finance_review: boolean
  confirmed_by?: string
  confirmed_by_name?: string
  confirmed_at?: string
  reject_reason?: string
  created_draft_id?: string
  created_draft_type?: string
  created_at?: string
  updated_at?: string
}

export function analyzeAgentMessage(data: {
  content: string
  platform?: string
  conversation_id?: string
  message_id?: string
  sender_name?: string
  sender_id?: string
}) {
  return post<AgentDraftResponse>('/vehicle-agent/messages/analyze', data)
}

export function getAgentDrafts(params: {
  page?: number
  page_size?: number
  status?: string
  intent?: string
  platform?: string
}) {
  return get<PaginatedData<AgentDraftResponse>>('/vehicle-agent/drafts', { params })
}

export function getAgentDraft(id: string) {
  return get<AgentDraftResponse>(`/vehicle-agent/drafts/${id}`)
}

export function confirmAgentDraft(id: string) {
  return post<AgentDraftResponse>(`/vehicle-agent/drafts/${id}/confirm`, {})
}

export function rejectAgentDraft(id: string, rejectReason?: string) {
  return post<AgentDraftResponse>(`/vehicle-agent/drafts/${id}/reject`, { reject_reason: rejectReason })
}
