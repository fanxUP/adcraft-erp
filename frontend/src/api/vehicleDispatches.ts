import { get, post, patch } from './index'

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

export interface PaginatedResponse<T> {
  code: number
  message: string
  data: {
    items: T[]
    total: number
    page: number
    page_size: number
  }
}

export interface SuccessResponse<T> {
  code: number
  message: string
  data: T
}

export async function getVehicleDispatches(params?: {
  page?: number
  page_size?: number
  keyword?: string
  status?: string
  vehicle_id?: string
  driver_id?: string
}): Promise<PaginatedResponse<VehicleDispatchResponse>> {
  return get('/vehicle-dispatches/', { params }) as Promise<PaginatedResponse<VehicleDispatchResponse>>
}

export async function getVehicleDispatch(id: string): Promise<SuccessResponse<VehicleDispatchResponse>> {
  return get(`/vehicle-dispatches/${id}`) as Promise<SuccessResponse<VehicleDispatchResponse>>
}

export async function createVehicleDispatch(data: VehicleDispatchCreateData): Promise<SuccessResponse<VehicleDispatchResponse>> {
  return post('/vehicle-dispatches/', data) as Promise<SuccessResponse<VehicleDispatchResponse>>
}

export async function updateVehicleDispatch(id: string, data: VehicleDispatchUpdateData): Promise<SuccessResponse<VehicleDispatchResponse>> {
  return patch(`/vehicle-dispatches/${id}`, data) as Promise<SuccessResponse<VehicleDispatchResponse>>
}

export async function cancelVehicleDispatch(id: string): Promise<SuccessResponse<VehicleDispatchResponse>> {
  return post(`/vehicle-dispatches/${id}/cancel`) as Promise<SuccessResponse<VehicleDispatchResponse>>
}

export async function getAvailableVehicles() {
  return get('/vehicles/available')
}

export async function getAvailableDrivers() {
  return get('/vehicle-drivers/available')
}
