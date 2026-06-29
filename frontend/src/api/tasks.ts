import { get, post, put, del } from './index'
import { PaginatedData, DesignTaskResponse, ProductionTaskResponse, InstallationTaskResponse, AttachmentResponse, SuccessResponse } from '@/types/api'

export function getDesignTasks(params?: { page?: number; page_size?: number; status?: string; assigned_to?: string; order_id?: string }) { return get<PaginatedData<DesignTaskResponse>>('/design-tasks/', { params }) }
export function getDesignTask(id: string) { return get<DesignTaskResponse>(`/design-tasks/${id}`) }
export function createDesignTask(data: Omit<Partial<DesignTaskResponse>, 'id' | 'design_no' | 'created_at' | 'updated_at' | 'attachments'>) { return post<DesignTaskResponse>('/design-tasks/', data) }
export function updateDesignTask(id: string, data: Partial<Omit<DesignTaskResponse, 'id' | 'design_no' | 'created_at' | 'updated_at' | 'attachments'>>) { return put<DesignTaskResponse>(`/design-tasks/${id}`, data) }
export function changeDesignTaskStatus(id: string, data: { to_status: string; reason?: string }) { return post<DesignTaskResponse>(`/design-tasks/${id}/change-status`, data) }

export function getProductionTasks(params?: { page?: number; page_size?: number; status?: string; assigned_to?: string; order_id?: string }) { return get<PaginatedData<ProductionTaskResponse>>('/production-tasks/', { params }) }
export function getProductionTask(id: string) { return get<ProductionTaskResponse>(`/production-tasks/${id}`) }
export function createProductionTask(data: Omit<Partial<ProductionTaskResponse>, 'id' | 'production_no' | 'created_at' | 'updated_at' | 'attachments'>) { return post<ProductionTaskResponse>('/production-tasks/', data) }
export function updateProductionTask(id: string, data: Partial<Omit<ProductionTaskResponse, 'id' | 'production_no' | 'created_at' | 'updated_at' | 'attachments'>>) { return put<ProductionTaskResponse>(`/production-tasks/${id}`, data) }
export function changeProductionTaskStatus(id: string, data: { to_status: string; reason?: string }) { return post<ProductionTaskResponse>(`/production-tasks/${id}/change-status`, data) }

export function getInstallationTasks(params?: { page?: number; page_size?: number; status?: string; assigned_to?: string; order_id?: string }) { return get<PaginatedData<InstallationTaskResponse>>('/installation-tasks/', { params }) }
export function getInstallationTask(id: string) { return get<InstallationTaskResponse>(`/installation-tasks/${id}`) }
export function createInstallationTask(data: Omit<Partial<InstallationTaskResponse>, 'id' | 'installation_no' | 'created_at' | 'updated_at' | 'attachments'>) { return post<InstallationTaskResponse>('/installation-tasks/', data) }
export function updateInstallationTask(id: string, data: Partial<Omit<InstallationTaskResponse, 'id' | 'installation_no' | 'created_at' | 'updated_at' | 'attachments'>>) { return put<InstallationTaskResponse>(`/installation-tasks/${id}`, data) }
export function changeInstallationTaskStatus(id: string, data: { to_status: string; reason?: string }) { return post<InstallationTaskResponse>(`/installation-tasks/${id}/change-status`, data) }

export function uploadAttachment(relatedType: string, relatedId: string, file: File, category?: string) {
  const form = new FormData()
  form.append('file', file)
  return post<AttachmentResponse>('/attachments/upload', form, {
    params: { related_type: relatedType, related_id: relatedId, category },
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
export function deleteAttachment(id: string) { return del<SuccessResponse>(`/attachments/${id}`) }
