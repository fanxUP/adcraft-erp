import { get, post, patch } from './index'
import type { PaginatedData } from '@/types/api'

export interface VehicleDispatchResponse {
  id: string
  dispatch_no: string
  request_id: string | null
  request_no: string | null
  vehicle_id: string
  vehicle_name: string
  plate_number: string
  driver_id: string | null
  driver_name: string | null
  companions: string | null
  related_customer_id: string | null
  related_order_id: string | null
  related_install_task_id: string | null
  start_location: string | null
  destination: string | null
  planned_start_time: string | null
  planned_return_time: string | null
  actual_start_time: string | null
  actual_return_time: string | null
  status: string
  remark: string | null
  created_by: string | null
  created_at: string
  updated_at: string
}

export interface VehicleDispatchCreateData {
  request_id?: string
  vehicle_id: string
  driver_id?: string
  companions?: string
  related_customer_id?: string
  related_order_id?: string
  related_install_task_id?: string
  start_location?: string
  destination?: string
  planned_start_time?: string
  planned_return_time?: string
  cargo_description?: string
  remark?: string
}

export interface VehicleDispatchUpdateData {
  vehicle_id?: string
  driver_id?: string
  companions?: string
  related_customer_id?: string
  related_order_id?: string
  related_install_task_id?: string
  start_location?: string
  destination?: string
  planned_start_time?: string
  planned_return_time?: string
  cargo_description?: string
  remark?: string
}

export async function getVehicleDispatches(params?: {
  page?: number
  page_size?: number
  keyword?: string
  status?: string
  vehicle_id?: string
  driver_id?: string
}): Promise<PaginatedData<VehicleDispatchResponse>> {
  return get<PaginatedData<VehicleDispatchResponse>>('/vehicle-dispatches/', { params })
}

export async function getVehicleDispatch(id: string): Promise<VehicleDispatchResponse> {
  return get<VehicleDispatchResponse>(`/vehicle-dispatches/${id}`)
}

export async function createVehicleDispatch(data: VehicleDispatchCreateData): Promise<VehicleDispatchResponse> {
  return post<VehicleDispatchResponse>('/vehicle-dispatches/', data)
}

export async function updateVehicleDispatch(id: string, data: VehicleDispatchUpdateData): Promise<VehicleDispatchResponse> {
  return patch<VehicleDispatchResponse>(`/vehicle-dispatches/${id}`, data)
}

export async function cancelVehicleDispatch(id: string): Promise<VehicleDispatchResponse> {
  return post<VehicleDispatchResponse>(`/vehicle-dispatches/${id}/cancel`)
}

export async function getAvailableVehicles() {
  return get<{ id: string; vehicle_name: string; plate_number: string }[]>('/vehicles/available')
}

export async function getAvailableDrivers() {
  return get<{ id: string; driver_name: string; phone: string }[]>('/vehicle-drivers/available')
}
