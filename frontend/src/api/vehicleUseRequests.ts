import { get, post, patch } from './index'
import type { PaginatedData } from '@/types/api'

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

export async function getVehicleUseRequests(params?: {
  page?: number
  page_size?: number
  keyword?: string
  status?: string
  requester_id?: string
}): Promise<PaginatedData<VehicleUseRequestResponse>> {
  return get<PaginatedData<VehicleUseRequestResponse>>('/vehicle-use-requests', { params })
}

export async function getVehicleUseRequest(id: string): Promise<VehicleUseRequestResponse> {
  return get<VehicleUseRequestResponse>(`/vehicle-use-requests/${id}`)
}

export async function createVehicleUseRequest(data: VehicleUseRequestCreateData): Promise<VehicleUseRequestResponse> {
  return post<VehicleUseRequestResponse>('/vehicle-use-requests', data)
}

export async function updateVehicleUseRequest(id: string, data: VehicleUseRequestUpdateData): Promise<VehicleUseRequestResponse> {
  return patch<VehicleUseRequestResponse>(`/vehicle-use-requests/${id}`, data)
}

export async function submitVehicleUseRequest(id: string): Promise<VehicleUseRequestResponse> {
  return post<VehicleUseRequestResponse>(`/vehicle-use-requests/${id}/submit`)
}

export async function approveVehicleUseRequest(id: string): Promise<VehicleUseRequestResponse> {
  return post<VehicleUseRequestResponse>(`/vehicle-use-requests/${id}/approve`)
}

export async function rejectVehicleUseRequest(id: string, rejectReason: string): Promise<VehicleUseRequestResponse> {
  return post<VehicleUseRequestResponse>(`/vehicle-use-requests/${id}/reject`, { reject_reason: rejectReason })
}

export async function cancelVehicleUseRequest(id: string): Promise<VehicleUseRequestResponse> {
  return post<VehicleUseRequestResponse>(`/vehicle-use-requests/${id}/cancel`)
}
