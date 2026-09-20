import { get, post, put, del } from './index'
import { PaginatedData, DesignTaskResponse, ProductionTaskResponse, InstallationTaskResponse, TaskQueueItem, AttachmentResponse, SuccessResponse, TaskType, TaskOrderItemOption, TaskAssigneeOption, CompletedProjectCard, CompletedProjectDetail, TaskCompletionType } from '@/types/api'

type ReadonlyTaskFields =
  | 'id'
  | 'created_at'
  | 'updated_at'
  | 'attachments'
  | 'assigned_to'
  | 'item_names'

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

export interface TaskStatusChangeInput {
  to_status: string
  reason?: string
  order_item_ids: string[]
}

/** Complete exactly one order item and optionally attach its completion materials. */
export function completeTaskItem(
  taskType: TaskType,
  taskId: string,
  orderItemId: string,
  files: File[] = [],
  skipMaterials = false,
  reason = '',
) {
  const form = new FormData()
  form.append('task_type', taskType)
  form.append('task_id', taskId)
  form.append('order_item_id', orderItemId)
  form.append('skip_materials', String(skipMaterials))
  if (reason.trim()) form.append('reason', reason.trim())
  files.forEach(file => form.append('files', file))

  return post<DesignTaskResponse | ProductionTaskResponse | InstallationTaskResponse>(
    '/task-queue/complete-item',
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
}

export interface TaskItemRollbackInput {
  order_item_ids: string[]
  reason?: string
}

export interface TaskItemAssigneeUpdateInput {
  order_item_ids: string[]
  assignee_user_id?: string | null
}

export function getDesignTasks(params?: { page?: number; page_size?: number; status?: string; assigned_to?: string; order_id?: string; order_item_id?: string; outsourced?: boolean }) { return get<PaginatedData<DesignTaskResponse>>('/design-tasks/', { params }) }
export function getDesignTask(id: string) { return get<DesignTaskResponse>(`/design-tasks/${id}`) }
export function createDesignTask(data: Omit<Partial<DesignTaskResponse>, 'id' | 'design_no' | 'created_at' | 'updated_at' | 'attachments'>) { return post<DesignTaskResponse>('/design-tasks/', data) }
export function updateDesignTask(id: string, data: DesignTaskUpdateInput) { return put<DesignTaskResponse>(`/design-tasks/${id}`, data) }
export function linkHistoricalDesignTaskItems(id: string, data: { order_item_ids: string[] }) { return post<DesignTaskResponse>(`/design-tasks/${id}/historical-order-item-links`, data) }
export function assignDesignTask(id: string, assignedTo: string | null) { return put<DesignTaskResponse>(`/design-tasks/${id}/assignee`, { assigned_to: assignedTo }) }
export function reassignDesignTaskItems(id: string, data: TaskItemAssigneeUpdateInput) { return put<DesignTaskResponse>(`/design-tasks/${id}/order-item-assignees`, data) }
export function changeDesignTaskStatus(id: string, data: TaskStatusChangeInput) { return post<DesignTaskResponse>(`/design-tasks/${id}/change-status`, data) }

export function getProductionTasks(params?: { page?: number; page_size?: number; status?: string; assigned_to?: string; order_id?: string; order_item_id?: string; outsourced?: boolean }) { return get<PaginatedData<ProductionTaskResponse>>('/production-tasks/', { params }) }
export function getProductionTask(id: string) { return get<ProductionTaskResponse>(`/production-tasks/${id}`) }
export function createProductionTask(data: Omit<Partial<ProductionTaskResponse>, 'id' | 'production_no' | 'created_at' | 'updated_at' | 'attachments'>) { return post<ProductionTaskResponse>('/production-tasks/', data) }
export function updateProductionTask(id: string, data: ProductionTaskUpdateInput) { return put<ProductionTaskResponse>(`/production-tasks/${id}`, data) }
export function linkHistoricalProductionTaskItems(id: string, data: { order_item_ids: string[] }) { return post<ProductionTaskResponse>(`/production-tasks/${id}/historical-order-item-links`, data) }
export function assignProductionTask(id: string, assignedTo: string | null) { return put<ProductionTaskResponse>(`/production-tasks/${id}/assignee`, { assigned_to: assignedTo }) }
export function reassignProductionTaskItems(id: string, data: TaskItemAssigneeUpdateInput) { return put<ProductionTaskResponse>(`/production-tasks/${id}/order-item-assignees`, data) }
export function changeProductionTaskStatus(id: string, data: TaskStatusChangeInput) { return post<ProductionTaskResponse>(`/production-tasks/${id}/change-status`, data) }
export function rollbackProductionTaskItems(id: string, data: TaskItemRollbackInput) { return post<ProductionTaskResponse>(`/production-tasks/${id}/rollback-items`, data) }

export function getInstallationTasks(params?: { page?: number; page_size?: number; status?: string; assigned_to?: string; order_id?: string; order_item_id?: string; outsourced?: boolean }) { return get<PaginatedData<InstallationTaskResponse>>('/installation-tasks/', { params }) }
export function getInstallationTask(id: string) { return get<InstallationTaskResponse>(`/installation-tasks/${id}`) }
export function createInstallationTask(data: Omit<Partial<InstallationTaskResponse>, 'id' | 'installation_no' | 'created_at' | 'updated_at' | 'attachments'>) { return post<InstallationTaskResponse>('/installation-tasks/', data) }
export function updateInstallationTask(id: string, data: InstallationTaskUpdateInput) { return put<InstallationTaskResponse>(`/installation-tasks/${id}`, data) }
export function linkHistoricalInstallationTaskItems(id: string, data: { order_item_ids: string[] }) { return post<InstallationTaskResponse>(`/installation-tasks/${id}/historical-order-item-links`, data) }
export function assignInstallationTask(id: string, assignedTo: string | null) { return put<InstallationTaskResponse>(`/installation-tasks/${id}/assignee`, { assigned_to: assignedTo }) }
export function reassignInstallationTaskItems(id: string, data: TaskItemAssigneeUpdateInput) { return put<InstallationTaskResponse>(`/installation-tasks/${id}/order-item-assignees`, data) }
export function changeInstallationTaskStatus(id: string, data: TaskStatusChangeInput) { return post<InstallationTaskResponse>(`/installation-tasks/${id}/change-status`, data) }
export function rollbackInstallationTaskItems(id: string, data: TaskItemRollbackInput) { return post<InstallationTaskResponse>(`/installation-tasks/${id}/rollback-items`, data) }

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

export function getTaskQueue(params?: {
  page?: number
  page_size?: number
  stage?: 'design' | 'production' | 'installation'
  status?: string
  order_id?: string
  order_item_id?: string
  overdue?: boolean
}) {
  return get<PaginatedData<TaskQueueItem>>('/task-queue/', { params })
}

export function getCompletedProjects(params?: {
  page?: number
  page_size?: number
  stage?: TaskCompletionType
}) {
  return get<PaginatedData<CompletedProjectCard>>('/task-queue/completed-projects', { params })
}

export function getCompletedProject(projectId: string) {
  return get<CompletedProjectDetail>(`/task-queue/completed-projects/${projectId}`)
}

export function getTaskOrderItemOptions(taskType: TaskType, taskId: string) {
  return get<TaskOrderItemOption[]>('/task-queue/order-item-options', {
    params: { task_type: taskType, task_id: taskId },
  })
}

export function acknowledgeTaskOrderReview(taskType: TaskType, taskId: string) {
  return post<DesignTaskResponse | ProductionTaskResponse | InstallationTaskResponse>(
    '/task-queue/acknowledge-order-review',
    undefined,
    { params: { task_type: taskType, task_id: taskId } },
  )
}

export function getTaskAssigneeOptions(taskType: TaskType) {
  return get<TaskAssigneeOption[]>('/task-queue/assignee-options', {
    params: { task_type: taskType },
  })
}
