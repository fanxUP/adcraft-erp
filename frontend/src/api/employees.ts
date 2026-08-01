import { get, post, put, del, apiClient } from './index'
import type { PaginatedData, SuccessResponse } from '@/types/api'
import type { AttachmentResponse } from '@/types/api'

export interface EmployeeResponse {
  id: string; employee_no: string; name: string; phone?: string | null; gender?: string | null; ethnicity?: string | null
  birth_date?: string | null; department?: string | null; position?: string | null
  employment_type?: string | null; hire_date?: string | null; resignation_date?: string | null
  employment_status: string; id_card?: string | null; education?: string | null
  license_no?: string | null; license_type?: string | null; license_expire_date?: string | null
  id_card_front_url?: string | null; id_card_back_url?: string | null
  emergency_contact?: string | null; emergency_phone?: string | null; skills?: string[]
  bank_name?: string | null; bank_account?: string | null
  address?: string | null; user_id?: string | null; remark?: string | null
  is_active: boolean; created_at?: string | null
}

export interface EmployeeCreateInput { name: string; phone?: string | null; gender?: string | null; ethnicity?: string | null; birth_date?: string | null; department?: string | null; position?: string | null; employment_type?: string | null; hire_date?: string | null; resignation_date?: string | null; employment_status?: string; id_card?: string | null; education?: string | null; license_no?: string | null; license_type?: string | null; license_expire_date?: string | null; id_card_front_url?: string | null; id_card_back_url?: string | null; emergency_contact?: string | null; emergency_phone?: string | null; skills?: string[]; bank_name?: string | null; bank_account?: string | null; address?: string | null; user_id?: string | null; remark?: string | null; is_active?: boolean }

export interface EmployeeUpdateInput { name?: string | null; phone?: string | null; gender?: string | null; ethnicity?: string | null; birth_date?: string | null; department?: string | null; position?: string | null; employment_type?: string | null; hire_date?: string | null; resignation_date?: string | null; employment_status?: string | null; id_card?: string | null; education?: string | null; license_no?: string | null; license_type?: string | null; license_expire_date?: string | null; id_card_front_url?: string | null; id_card_back_url?: string | null; emergency_contact?: string | null; emergency_phone?: string | null; skills?: string[]; bank_name?: string | null; bank_account?: string | null; address?: string | null; user_id?: string | null; remark?: string | null; is_active?: boolean | null }

export function getEmployees(params: { page?: number; page_size?: number; keyword?: string; department?: string; employment_status?: string }) { return get<PaginatedData<EmployeeResponse>>('/employees/', { params }) }
export function createEmployee(data: EmployeeCreateInput) { return post<EmployeeResponse>('/employees/', data) }
export function getEmployee(id: string) { return get<EmployeeResponse>('/employees/' + id) }
export function updateEmployee(id: string, data: EmployeeUpdateInput) { return put<EmployeeResponse>('/employees/' + id, data) }
export function deleteEmployee(id: string) { return del<SuccessResponse>('/employees/' + id) }

export async function uploadEmployeeImage(file: File) {
  const form = new FormData()
  form.append('file', file)
  const res = await apiClient.post('/employees/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data.data as { file_url: string; file_name: string; file_size: number }
}

export function getEmployeeAttachments(id: string) { return get<AttachmentResponse[]>('/employees/' + id + '/attachments') }

export async function uploadEmployeeAttachment(id: string, file: File, category?: string) {
  const form = new FormData()
  form.append('file', file)
  const params: Record<string, string> = {}
  if (category) params.category = category
  const res = await apiClient.post('/employees/' + id + '/attachments', form, {
    params,
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data.data as AttachmentResponse
}

export function deleteEmployeeAttachment(attachmentId: string) { return del<SuccessResponse>('/employees/attachments/' + attachmentId) }
