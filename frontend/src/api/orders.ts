import { get, post, put, del, patch, apiClient } from './index'
import {
  PaginatedData,
  OrderItemEditabilityResponse,
  OrderItemMutationFields,
  OrderItemMutationImpactResponse,
  OrderEditImpactResponse,
  OrderEditRequest,
  OrderItemChangeBatch,
  OrderItemChangeBatchListResponse,
  OrderItemReconciliationResponse,
  OrderListResponse,
  OrderDetailResponse,
  OrderTaskAssigneesResponse,
  TaskAssigneeOption,
  OrderTaskAttachmentResponse,
  OrderTaskAttachmentsResponse,
} from '@/types/api'
import { dedupeProjectQueueOrders, PROJECT_QUEUE_STATUSES } from '@/utils/project-queue'

export function getOrders(params: { page?: number; page_size?: number; status?: string; customer_id?: string; keyword?: string }) {
  return get<PaginatedData<OrderListResponse>>('/orders/', { params })
}

/**
 * Load the order-level project queue from the same status contract used by
 * the workbench and the independent project board.
 */
export async function getProjectQueueOrders(pageSize = 200): Promise<OrderListResponse[]> {
  const responses = await Promise.all(
    PROJECT_QUEUE_STATUSES.map(status => getOrders({ page: 1, page_size: pageSize, status })),
  )
  return dedupeProjectQueueOrders(responses.flatMap(response => response.items || []))
}

export function getOrder(id: string) {
  return get<OrderDetailResponse>(`/orders/${id}`)
}

export function getOrderAttachments(
  orderId: string,
  params?: { stage?: 'design' | 'production' | 'installation'; task_id?: string },
) {
  return get<OrderTaskAttachmentsResponse>(`/orders/${orderId}/attachments`, { params })
}

export function uploadOrderAttachment(
  orderId: string,
  stage: 'design' | 'production' | 'installation',
  file: File,
  taskId?: string,
) {
  const formData = new FormData()
  formData.append('stage', stage)
  if (taskId) formData.append('task_id', taskId)
  formData.append('file', file)
  return post<OrderTaskAttachmentResponse>(`/orders/${orderId}/attachments`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export async function downloadOrderAttachment(
  orderId: string,
  attachmentId: string,
  options?: {
    download?: boolean
    stage?: 'design' | 'production' | 'installation'
    task_id?: string
  },
): Promise<Blob> {
  const response = await apiClient.get(`/orders/${orderId}/attachments/${attachmentId}/file`, {
    params: options,
    responseType: 'blob',
  })
  return response.data as Blob
}

export function deleteOrderAttachment(
  orderId: string,
  attachmentId: string,
  params?: { stage?: 'design' | 'production' | 'installation'; task_id?: string },
) {
  return del(`/orders/${orderId}/attachments/${attachmentId}`, { params })
}

// Compatibility adapters. New pages use the order-stage methods above.
export function getOrderTaskAttachments(id: string) {
  return get<OrderTaskAttachmentsResponse>(`/orders/${id}/task-attachments`)
}

export function uploadOrderTaskAttachment(
  orderId: string,
  taskType: 'design' | 'production' | 'installation',
  taskId: string,
  file: File,
) {
  const formData = new FormData()
  formData.append('task_type', taskType)
  formData.append('task_id', taskId)
  formData.append('file', file)
  return post<OrderTaskAttachmentResponse>(`/orders/${orderId}/task-attachments`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export async function downloadOrderTaskAttachment(
  orderId: string,
  attachmentId: string,
  download = false,
): Promise<Blob> {
  const response = await apiClient.get(`/orders/${orderId}/task-attachments/${attachmentId}/file`, {
    params: { download },
    responseType: 'blob',
  })
  return response.data as Blob
}

export function deleteOrderTaskAttachment(orderId: string, attachmentId: string) {
  return del(`/orders/${orderId}/task-attachments/${attachmentId}`)
}

export function getOrderTaskAssigneeOptions() {
  return get<TaskAssigneeOption[]>('/orders/task-assignee-options')
}

export function getOrderTaskAssignees(id: string) {
  return get<OrderTaskAssigneesResponse>(`/orders/${id}/task-assignees`)
}

export function updateOrderTaskAssignees(id: string, employeeIds: string[]) {
  return put<OrderTaskAssigneesResponse>(`/orders/${id}/task-assignees`, {
    employee_ids: employeeIds,
  })
}

export function getOrderItemEditability(id: string) {
  return get<OrderItemEditabilityResponse>(`/orders/${id}/items/editability`)
}

export function previewOrderItemMutation(id: string, data: {
  operation: 'add' | 'update' | 'delete'
  item_id?: string
  item?: OrderItemMutationFields
  reason: string
  expected_updated_at: string
}) {
  return post<OrderItemMutationImpactResponse>(`/orders/${id}/items/preview`, data)
}

export function getOrderItemChangeBatches(id: string, params?: {
  limit?: number
  change_batch_id?: string
}) {
  return get<OrderItemChangeBatchListResponse>(`/orders/${id}/items/change-batches`, { params })
}

export function getOrderItemChangeBatch(id: string, changeBatchId: string) {
  return get<OrderItemChangeBatch>(`/orders/${id}/items/change-batches/${changeBatchId}`)
}

export function reconcileOrderItemChange(id: string, changeBatchId?: string) {
  return get<OrderItemReconciliationResponse>(`/orders/${id}/items/reconciliation`, {
    params: changeBatchId ? { change_batch_id: changeBatchId } : undefined,
  })
}

export function addOrderItem(id: string, data: OrderItemMutationFields & {
  reason: string
  expected_updated_at: string
  preview_id?: string
  plan_hash?: string
  preview_expires_at?: string
  confirm_high_risk?: boolean
}) {
  return post<OrderDetailResponse>(`/orders/${id}/items`, data)
}

export function updateOrderItem(id: string, itemId: string, data: OrderItemMutationFields & {
  reason: string
  expected_updated_at: string
  preview_id?: string
  plan_hash?: string
  preview_expires_at?: string
  confirm_high_risk?: boolean
}) {
  return patch<OrderDetailResponse>(`/orders/${id}/items/${itemId}`, data)
}

export function deleteOrderItem(id: string, itemId: string, data: {
  reason: string
  expected_updated_at: string
  preview_id?: string
  plan_hash?: string
  preview_expires_at?: string
  confirm_high_risk?: boolean
}) {
  return del<OrderDetailResponse>(`/orders/${id}/items/${itemId}`, { data })
}

export function previewOrderEdit(id: string, data: OrderEditRequest) {
  return post<OrderEditImpactResponse>(`/orders/${id}/items/batch-preview`, data)
}

export function saveOrderEdit(id: string, data: OrderEditRequest) {
  return post<OrderDetailResponse>(`/orders/${id}/items/batch`, data)
}

export function changeOrderStatus(id: string, data: { to_status: string; reason?: string }) {
  return post<OrderDetailResponse>(`/orders/${id}/change-status`, data)
}

export function reopenCompletedOrder(id: string, reason: string) {
  return post<OrderDetailResponse>(`/orders/${id}/reopen-completed`, { to_status: 'in_installation', reason })
}

export function setOrderCost(id: string, cost_amount: number) {
  return post<OrderDetailResponse>(`/orders/${id}/set-cost`, { cost_amount })
}

export function autoCalculateCost(id: string) {
  return post<OrderDetailResponse>(`/orders/${id}/auto-cost`)
}

export function deleteOrder(id: string) {
  return del(`/orders/${id}`)
}

export function getDeletedOrders(params: { page?: number; page_size?: number; keyword?: string }) {
  return get<PaginatedData<OrderListResponse>>('/orders/recycle/list', { params })
}

export function restoreOrder(id: string) {
  return post<OrderDetailResponse>(`/orders/${id}/restore`)
}

export function updateOrderContact(id: string, data: { contact_person?: string | null; contact_phone?: string | null }) {
  return put<OrderDetailResponse>(`/orders/${id}/contact`, data)
}
