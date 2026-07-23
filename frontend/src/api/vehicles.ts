import { get, post, patch } from './index'
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
