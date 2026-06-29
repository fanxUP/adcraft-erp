import apiClient from './index'

export function getOperationLogs(params: {
  page?: number
  page_size?: number
  user_id?: string
  object_type?: string
  action?: string
  date_from?: string
  date_to?: string
}) {
  return apiClient.get('/logs/', { params })
}

export function getOperationLog(id: string) {
  return apiClient.get(`/logs/${id}`)
}
