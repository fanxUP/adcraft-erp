import { get, post, put, del } from './index'
import type { PaginatedData, SuccessResponse } from '@/types/api'

export interface SalaryRuleItem {
  id: string
  employee_id: string
  employee_no?: string | null
  employee_name?: string | null
  effective_date: string
  base_salary: number
  overtime_rate?: number | null
  commission_rate?: number | null
  subsidy_standard?: number | null
  social_insurance?: number | null
  housing_fund?: number | null
  deduction_standard?: number | null
  remark?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export function getSalaryRules(params: {
  page?: number
  page_size?: number
  employee_id?: string
}) {
  return get<PaginatedData<SalaryRuleItem>>('/salary-rules/', { params })
}

export function getEmployeeSalaryRule(employeeId: string) {
  return get<SalaryRuleItem>('/salary-rules/employee/' + employeeId)
}

export function createSalaryRule(data: Partial<SalaryRuleItem>) {
  return post<SalaryRuleItem>('/salary-rules/', data)
}

export function updateSalaryRule(id: string, data: Partial<SalaryRuleItem>) {
  return put<SalaryRuleItem>('/salary-rules/' + id, data)
}

export function deleteSalaryRule(id: string) {
  return del<SuccessResponse>('/salary-rules/' + id)
}
