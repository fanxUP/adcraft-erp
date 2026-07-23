import { get, post, patch } from './index'

export interface VehicleUseRequestResponse {
  id: string
  request_no: string | null
  requester_id: string | null
  requester_name: string | null
  reason: string
  related_customer_id: string | null
  customer_name: string | null
  related_order_id: string | null
  related_install_task_id: string | null
  start_time: string | null
  expected_return_time: string | null
  destination: string | null
  need_driver: boolean
  need_cargo: boolean
  cargo_description: string | null
  estimated_distance_km: number | null
  status: string
  approver_id: string | null
  approver_name: string | null
  approved_at: string | null
  reject_reason: string | null
  remark: string | null
  created_at: string | null
  updated_at: string | null
}

export interface VehicleUseRequestCreateData {
  reason: string
  related_customer_id?: string | null
  related_order_id?: string | null
  related_install_task_id?: string | null
  start_time?: string | null
  expected_return_time?: string | null
  destination?: string | null
  need_driver?: boolean
  need_cargo?: boolean
  cargo_description?: string | null
  estimated_distance_km?: number | null
  remark?: string | null
}

export interface VehicleUseRequestUpdateData {
  reason?: string
  related_customer_id?: string | null
  related_order_id?: string | null
  related_install_task_id?: string | null
  start_time?: string | null
  expected_return_time?: string | null
  destination?: string | null
  need_driver?: boolean
  need_cargo?: boolean
  cargo_description?: string | null
  estimated_distance_km?: number | null
  remark?: string | null
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

export async function getVehicleUseRequests(params?: {
  page?: number
  page_size?: number
  keyword?: string
  status?: string
  requester_id?: string
}): Promise<PaginatedResponse<VehicleUseRequestResponse>> {
  return get('/vehicle-use-requests', { params }) as Promise<PaginatedResponse<VehicleUseRequestResponse>>
}

export async function getVehicleUseRequest(id: string): Promise<SuccessResponse<VehicleUseRequestResponse>> {
  return get(`/vehicle-use-requests/${id}`) as Promise<SuccessResponse<VehicleUseRequestResponse>>
}

export async function createVehicleUseRequest(data: VehicleUseRequestCreateData): Promise<SuccessResponse<VehicleUseRequestResponse>> {
  return post('/vehicle-use-requests', data) as Promise<SuccessResponse<VehicleUseRequestResponse>>
}

export async function updateVehicleUseRequest(id: string, data: VehicleUseRequestUpdateData): Promise<SuccessResponse<VehicleUseRequestResponse>> {
  return patch(`/vehicle-use-requests/${id}`, data) as Promise<SuccessResponse<VehicleUseRequestResponse>>
}

export async function submitVehicleUseRequest(id: string): Promise<SuccessResponse<VehicleUseRequestResponse>> {
  return post(`/vehicle-use-requests/${id}/submit`) as Promise<SuccessResponse<VehicleUseRequestResponse>>
}

export async function approveVehicleUseRequest(id: string): Promise<SuccessResponse<VehicleUseRequestResponse>> {
  return post(`/vehicle-use-requests/${id}/approve`) as Promise<SuccessResponse<VehicleUseRequestResponse>>
}

export async function rejectVehicleUseRequest(id: string, rejectReason: string): Promise<SuccessResponse<VehicleUseRequestResponse>> {
  return post(`/vehicle-use-requests/${id}/reject`, { reject_reason: rejectReason }) as Promise<SuccessResponse<VehicleUseRequestResponse>>
}

export async function cancelVehicleUseRequest(id: string): Promise<SuccessResponse<VehicleUseRequestResponse>> {
  return post(`/vehicle-use-requests/${id}/cancel`) as Promise<SuccessResponse<VehicleUseRequestResponse>>
}
