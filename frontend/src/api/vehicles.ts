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
