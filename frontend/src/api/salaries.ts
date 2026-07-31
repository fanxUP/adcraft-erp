import { get, post, put, del } from "./index"
import type { PaginatedData, SuccessResponse } from "@/types/api"

export interface SalaryRecordItem {
  id: string; employee_id: string; employee_no?: string | null; employee_name?: string | null
  month: string; base_salary: number; overtime_pay?: number | null; bonus?: number | null
  commission?: number | null; subsidy?: number | null; deduction?: number | null
  net_salary: number; payment_status: string; paid_at?: string | null
  remark?: string | null; created_at?: string | null; updated_at?: string | null
}

export interface SalaryGenerateResult {
  month: string
  created: number
  skipped_no_rule: number
  skipped_exists: number
  errors: string[]
}

export function getSalaries(params: { page?: number; page_size?: number; employee_id?: string; month?: string; payment_status?: string }) {
  return get<PaginatedData<SalaryRecordItem>>("/salaries/", { params })
}
export function createSalary(data: Partial<SalaryRecordItem>) {
  return post<SalaryRecordItem>("/salaries/", data)
}
export function getSalary(id: string) {
  return get<SalaryRecordItem>("/salaries/" + id)
}
export function updateSalary(id: string, data: Partial<SalaryRecordItem>) {
  return put<SalaryRecordItem>("/salaries/" + id, data)
}
export function deleteSalary(id: string) {
  return del<SuccessResponse>("/salaries/" + id)
}
export function generateSalaries(month: string, employee_ids?: string[]) {
  return post<SalaryGenerateResult>("/salaries/generate", { month, employee_ids })
}
