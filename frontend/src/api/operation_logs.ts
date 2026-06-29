import { get } from './index'
import { PaginatedData, OperationLogResponse } from '@/types/api'

export function getOperationLogs(params: {
  page?: number
  page_size?: number
  user_id?: string
  object_type?: string
  action?: string
  date_from?: string
  date_to?: string
}) {
  return get<PaginatedData<OperationLogResponse>>('/logs/', { params })
}

export function getOperationLog(id: string) {
  return get<OperationLogResponse>(`/logs/${id}`)
}
