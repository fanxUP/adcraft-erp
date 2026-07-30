import { get, post, put, del } from "./index"
import type { SuccessResponse } from "@/types/api"

export interface DepartmentItem {
  id: string; name: string; code: string; parent_id?: string | null
  sort_order: number; description?: string | null; is_active: boolean
  created_at?: string | null; updated_at?: string | null
}

export function getDepartments(params?: { keyword?: string; include_inactive?: boolean }) {
  return get<DepartmentItem[]>("/departments/", { params })
}
export function createDepartment(data: Partial<DepartmentItem>) {
  return post<DepartmentItem>("/departments/", data)
}
export function getDepartment(id: string) {
  return get<DepartmentItem>("/departments/" + id)
}
export function updateDepartment(id: string, data: Partial<DepartmentItem>) {
  return put<DepartmentItem>("/departments/" + id, data)
}
export function deleteDepartment(id: string) {
  return del<SuccessResponse>("/departments/" + id)
}
