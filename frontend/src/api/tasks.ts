import { get, post, put, del } from './index'
import { PaginatedData, DesignTaskResponse, ProductionTaskResponse, InstallationTaskResponse, AttachmentResponse, SuccessResponse } from '@/types/api'

type ReadonlyTaskFields =
  | 'id'
  | 'created_at'
  | 'updated_at'
  | 'attachments'
  | 'assigned_to'

type TaskUpdateInput<T, NumberField extends string> = Partial<
  Omit<T, ReadonlyTaskFields | NumberField>
> & {
  assigned_to?: string | null
}

export type DesignTaskUpdateInput = TaskUpdateInput<
  DesignTaskResponse,
  'design_no'
>
export type ProductionTaskUpdateInput = TaskUpdateInput<
  ProductionTaskResponse,
  'production_no'
>
export type InstallationTaskUpdateInput = TaskUpdateInput<
  InstallationTaskResponse,
  'installation_no' | 'scheduled_at'
> & {
  scheduled_at?: string | null
}

export function getDesignTasks(params?: { page?: number; page_size?: number; status?: string; assigned_to?: string; order_id?: string; outsourced?: boolean }) { return get<PaginatedData<DesignTaskResponse>>('/design-tasks/', { params }) }
export function getDesignTask(id: string) { return get<DesignTaskResponse>(`/design-tasks/${id}`) }
export function createDesignTask(data: Omit<Partial<DesignTaskResponse>, 'id' | 'design_no' | 'created_at' | 'updated_at' | 'attachments'>) { return post<DesignTaskResponse>('/design-tasks/', data) }
export function updateDesignTask(id: string, data: DesignTaskUpdateInput) { return put<DesignTaskResponse>(`/design-tasks/${id}`, data) }
export function changeDesignTaskStatus(id: string, data: { to_status: string; reason?: string }) { return post<DesignTaskResponse>(`/design-tasks/${id}/change-status`, data) }

export function getProductionTasks(params?: { page?: number; page_size?: number; status?: string; assigned_to?: string; order_id?: string; outsourced?: boolean }) { return get<PaginatedData<ProductionTaskResponse>>('/production-tasks/', { params }) }
export function getProductionTask(id: string) { return get<ProductionTaskResponse>(`/production-tasks/${id}`) }
export function createProductionTask(data: Omit<Partial<ProductionTaskResponse>, 'id' | 'production_no' | 'created_at' | 'updated_at' | 'attachments'>) { return post<ProductionTaskResponse>('/production-tasks/', data) }
export function updateProductionTask(id: string, data: ProductionTaskUpdateInput) { return put<ProductionTaskResponse>(`/production-tasks/${id}`, data) }
export function changeProductionTaskStatus(id: string, data: { to_status: string; reason?: string }) { return post<ProductionTaskResponse>(`/production-tasks/${id}/change-status`, data) }

export function getInstallationTasks(params?: { page?: number; page_size?: number; status?: string; assigned_to?: string; order_id?: string; outsourced?: boolean }) { return get<PaginatedData<InstallationTaskResponse>>('/installation-tasks/', { params }) }
export function getInstallationTask(id: string) { return get<InstallationTaskResponse>(`/installation-tasks/${id}`) }
export function createInstallationTask(data: Omit<Partial<InstallationTaskResponse>, 'id' | 'installation_no' | 'created_at' | 'updated_at' | 'attachments'>) { return post<InstallationTaskResponse>('/installation-tasks/', data) }
export function updateInstallationTask(id: string, data: InstallationTaskUpdateInput) { return put<InstallationTaskResponse>(`/installation-tasks/${id}`, data) }
export function changeInstallationTaskStatus(id: string, data: { to_status: string; reason?: string }) { return post<InstallationTaskResponse>(`/installation-tasks/${id}/change-status`, data) }

export function uploadAttachment(relatedType: string, relatedId: string, file: File, category?: string) {
  const form = new FormData()
  form.append('file', file)
  return post<AttachmentResponse>('/attachments/upload', form, {
    params: { related_type: relatedType, related_id: relatedId, category },
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
export function deleteDesignTask(id: string) { return del<SuccessResponse>(`/design-tasks/${id}`) }
export function deleteProductionTask(id: string) { return del<SuccessResponse>(`/production-tasks/${id}`) }
export function deleteInstallationTask(id: string) { return del<SuccessResponse>(`/installation-tasks/${id}`) }
export function deleteAttachment(id: string) { return del<SuccessResponse>(`/attachments/${id}`) }
