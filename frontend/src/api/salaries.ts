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

export interface SalaryReportRow {
  employee_no: string | null; department: string | null; employee_name: string | null
  attend_days: number; missed_days: number; attendance_bonus: number; performance: number; absent_days: number
  base_salary: number; overtime_hours: number; overtime_pay: number; total_salary: number
  performance_wage: number; meal_subsidy: number; attendance_phone_subsidy: number
  gross: number; social_deduction: number; net_salary: number; social_insurance: number; actual_gross: number
  remark: string | null; prev_month_net: number | null
}
export interface SalaryReportResult { month: string; title: string; rows: SalaryReportRow[] }

export function getSalaryReport(month: string) {
  return get<SalaryReportResult>("/salaries/report", { params: { month } })
}

/* ── 工资网格（考勤式）：指标列 + 可编辑公式 + 单元格 ─────────────────── */

export interface SalaryItem {
  id: string
  key: string
  label: string
  formula: string
  sort_order: number
  is_active: boolean
  is_builtin: boolean
  is_manual: boolean
  group1: string | null
  group2: string | null
}

export interface SalaryGridRow {
  employee_id: string
  employee_no: string | null
  employee_name: string
  department: string | null
  values: Record<string, number | null>
  payment_status: string | null
  remark: string | null
  paid_at: string | null
}

export interface SalaryGridResult {
  month: string
  items: SalaryItem[]
  rows: SalaryGridRow[]
}

export interface SalaryComputeResult {
  month: string
  computed: number
  errors: string[]
}

export interface SalarySaveResult {
  month: string
  saved: number
  errors: string[]
}

export function getSalaryItems() {
  return get<SalaryItem[]>("/salaries/items")
}
export function createSalaryItem(data: { key: string; label: string; formula: string; sort_order: number; is_manual?: boolean; group1?: string | null; group2?: string | null }) {
  return post<SalaryItem>("/salaries/items", data)
}
export function updateSalaryItem(id: string, data: { label?: string; formula?: string; sort_order?: number; is_active?: boolean; is_manual?: boolean; group1?: string | null; group2?: string | null }) {
  return put<SalaryItem>("/salaries/items/" + id, data)
}
export function deleteSalaryItem(id: string) {
  return del<unknown>("/salaries/items/" + id)
}

/* ── 工资参数（每月手工填一个值，公式可引用） ─────────────────────────────── */

export interface SalaryParam {
  id: string
  key: string
  label: string
  sort_order: number
  value: number | null
}

export interface SalaryParamsResult {
  month: string
  params: SalaryParam[]
}

export interface SalaryParamSaveResult {
  month: string
  saved: number
  errors: string[]
}

export function getSalaryParams(month: string) {
  return get<SalaryParamsResult>("/salaries/params", { params: { month } })
}
export function createSalaryParam(data: { key: string; label: string; sort_order: number }) {
  return post<{ id: string; key: string; label: string; sort_order: number }>("/salaries/params", data)
}
export function updateSalaryParam(id: string, data: { label?: string; sort_order?: number }) {
  return put<{ id: string; key: string; label: string; sort_order: number }>("/salaries/params/" + id, data)
}
export function deleteSalaryParam(id: string) {
  return del<unknown>("/salaries/params/" + id)
}
export function saveSalaryParamValues(month: string, values: { key: string; value: number | null }[]) {
  return post<SalaryParamSaveResult>("/salaries/params/save", { month, values })
}
export function getSalaryGrid(month: string) {
  return get<SalaryGridResult>("/salaries/grid", { params: { month } })
}
export function computeSalaryGrid(month: string, employee_ids?: string[]) {
  return post<SalaryComputeResult>("/salaries/grid/compute", { month, employee_ids })
}
export function saveSalaryGrid(
  month: string,
  cells?: { employee_id: string; item_key: string; value: number | null }[],
  payments?: { employee_id: string; payment_status: string }[],
  remarks?: { employee_id: string; remark: string | null }[],
) {
  return post<SalarySaveResult>("/salaries/grid/save", { month, cells, payments, remarks })
}
