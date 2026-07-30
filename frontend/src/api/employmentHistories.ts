import { get, post, put, del } from "./index"
import type { PaginatedData, SuccessResponse } from "@/types/api"

export interface EmploymentHistoryItem {
  id: string; employee_id: string; employee_no?: string | null; employee_name?: string | null
  change_date: string; change_type: string
  previous_department?: string | null; new_department?: string | null
  previous_position?: string | null; new_position?: string | null
  reason?: string | null; remark?: string | null; created_at?: string | null
}

export function getEmploymentHistories(params: { page?: number; page_size?: number; employee_id?: string; change_type?: string }) {
  return get<PaginatedData<EmploymentHistoryItem>>("/employment-histories/", { params })
}
export function createEmploymentHistory(data: Partial<EmploymentHistoryItem>) {
  return post<EmploymentHistoryItem>("/employment-histories/", data)
}
export function getEmploymentHistory(id: string) {
  return get<EmploymentHistoryItem>("/employment-histories/" + id)
}
export function updateEmploymentHistory(id: string, data: Partial<EmploymentHistoryItem>) {
  return put<EmploymentHistoryItem>("/employment-histories/" + id, data)
}
export function deleteEmploymentHistory(id: string) {
  return del<SuccessResponse>("/employment-histories/" + id)
}
