import { get, post, put, del } from "./index"
import type { PaginatedData, SuccessResponse } from "@/types/api"

export interface LeaveRequestItem {
  id: string; employee_id: string; employee_no?: string | null; employee_name?: string | null
  leave_type: string; start_date: string; end_date: string; duration_days: number
  reason: string; status: string; approved_by?: string | null
  approved_at?: string | null; remark?: string | null
  created_at?: string | null; updated_at?: string | null
}

export function getLeaveRequests(params: { page?: number; page_size?: number; employee_id?: string; status?: string; leave_type?: string }) {
  return get<PaginatedData<LeaveRequestItem>>("/leaves/", { params })
}
export function createLeaveRequest(data: Partial<LeaveRequestItem>) {
  return post<LeaveRequestItem>("/leaves/", data)
}
export function getLeaveRequest(id: string) {
  return get<LeaveRequestItem>("/leaves/" + id)
}
export function updateLeaveRequest(id: string, data: Partial<LeaveRequestItem>) {
  return put<LeaveRequestItem>("/leaves/" + id, data)
}
export function approveLeaveRequest(id: string, data: { status: string; remark?: string | null }) {
  return post<LeaveRequestItem>("/leaves/" + id + "/approve", data)
}
export function deleteLeaveRequest(id: string) {
  return del<SuccessResponse>("/leaves/" + id)
}
