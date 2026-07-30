import { get, post, put, del } from "./index"
import type { PaginatedData, SuccessResponse } from "@/types/api"

export interface AttendanceRuleItem {
  id: string; name: string; department?: string | null; check_in_time: string; check_out_time: string
  work_days?: string[]; late_threshold: number; early_leave_threshold: number; overtime_rate?: number | null
  is_active: boolean; created_at?: string | null; updated_at?: string | null
}
export interface AttendanceRecordItem {
  id: string; employee_id: string; date: string; check_in_time?: string | null; check_out_time?: string | null
  check_in_status: string; check_out_status: string; overtime_hours?: number | null; source: string; remark?: string | null; created_at?: string | null; updated_at?: string | null
}
export interface EmployeeOption { id: string; employee_no: string; name: string; department?: string | null }

export function getAttendanceRules() { return get<AttendanceRuleItem[]>("/attendance/rules") }
export function createAttendanceRule(data: Partial<AttendanceRuleItem>) { return post<AttendanceRuleItem>("/attendance/rules", data) }
export function updateAttendanceRule(id: string, data: Partial<AttendanceRuleItem>) { return put<AttendanceRuleItem>("/attendance/rules/" + id, data) }
export function deleteAttendanceRule(id: string) { return del<SuccessResponse>("/attendance/rules/" + id) }
export function getAttendanceRecords(params: { page?: number; page_size?: number; employee_id?: string; date_from?: string; date_to?: string }) { return get<PaginatedData<AttendanceRecordItem>>("/attendance/records", { params }) }
export function createAttendanceRecord(data: { employee_id: string; date: string; check_in_time?: string | null; check_out_time?: string | null; check_in_status?: string; check_out_status?: string; remark?: string | null }) { return post<AttendanceRecordItem>("/attendance/records", data) }
export function updateAttendanceRecord(id: string, data: Record<string, unknown>) { return put<AttendanceRecordItem>("/attendance/records/" + id, data) }
export function deleteAttendanceRecord(id: string) { return del<SuccessResponse>("/attendance/records/" + id) }
export function getAttendanceEmployees() { return get<EmployeeOption[]>("/attendance/employees") }