import { apiClient, get, post, put, del } from './index'
import { PaginatedData, PaymentResponse, StatementResponse, StatementDetailResponse, ExpenseResponse, ExpenseDeleteConfirmedResponse, SuccessResponse, UploadResponse, DashboardData, DailyReportData, MonthlyReportData, CustomerDebtItem, ProjectCostResponse, ProjectCostImportResponse, ProjectCostSummaryResponse, ProjectCostItemSummaryResponse, AttachmentResponse, DebtResponse, QuoteCostResponse, TaskCompletionDetailsResponse, TaskCompletionKind, TaskCompletionPeriod, TaskCompletionSummary, TaskCompletionType, PayableResponse } from '@/types/api'

export function getPayments(params?: { page?: number; page_size?: number; order_id?: string; contract_id?: string; customer_id?: string; status?: string }) { return get<PaginatedData<PaymentResponse>>('/payments/', { params }) }
export function getPayment(id: string) { return get<PaymentResponse>(`/payments/${id}`) }
export function createPayment(data: Omit<Partial<PaymentResponse>, 'id' | 'payment_no' | 'created_at' | 'created_by'>) { return post<PaymentResponse>('/payments/', data) }
export function voidPayment(id: string, data: { void_reason: string }) { return post<SuccessResponse>(`/payments/${id}/void`, data) }
export function uploadReceipt(paymentId: string, file: File) {
  const form = new FormData()
  form.append('file', file)
  return post<UploadResponse>(`/payments/${paymentId}/upload-receipt`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function getStatements(params?: { page?: number; page_size?: number; customer_id?: string; status?: string }) { return get<PaginatedData<StatementResponse>>('/statements/', { params }) }
export function getStatement(id: string) { return get<StatementDetailResponse>(`/statements/${id}`) }
export function createStatement(data: Omit<Partial<StatementResponse>, 'id' | 'statement_no' | 'created_at'>) { return post<StatementResponse>('/statements/', data) }
export function confirmStatement(id: string) { return post<StatementResponse>(`/statements/${id}/confirm`) }

export function getExpenses(params?: { page?: number; page_size?: number; category?: string; start_date?: string; end_date?: string }) { return get<PaginatedData<ExpenseResponse>>('/expenses/', { params }) }
export function getExpense(id: string) { return get<ExpenseResponse>(`/expenses/${id}`) }
export type ExpenseWritePayload = Partial<Omit<ExpenseResponse, 'id' | 'expense_no' | 'created_by' | 'created_at'>> & {
  /** 登记时支付金额；总金额由它与 payable_amount 相加得到。 */
  paid_amount?: number
}

export function createExpense(data: ExpenseWritePayload) { return post<ExpenseResponse>('/expenses/', data) }
export function updateExpense(id: string, data: ExpenseWritePayload) { return put<ExpenseResponse>(`/expenses/${id}`, data) }
export function deleteExpense(id: string) { return del<SuccessResponse>(`/expenses/${id}`) }
export function deleteExpenseConfirmed(
  id: string,
  data: { expected_payment_count: number; expected_paid_amount: number },
) {
  return post<ExpenseDeleteConfirmedResponse>(`/expenses/${id}/delete-confirmed`, data)
}

export function getExpenseAttachments(expenseId: string) {
  return get<AttachmentResponse[]>(`/expenses/${expenseId}/attachments`)
}

export function uploadExpenseAttachment(expenseId: string, file: File) {
  const form = new FormData()
  form.append('file', file)
  return post<AttachmentResponse>(`/expenses/${expenseId}/attachments`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export async function downloadExpenseAttachment(
  expenseId: string,
  attachmentId: string,
  download = false,
): Promise<Blob> {
  const response = await apiClient.get(`/expenses/${expenseId}/attachments/${attachmentId}/file`, {
    params: { download },
    responseType: 'blob',
  })
  return response.data as Blob
}

export function deleteExpenseAttachment(expenseId: string, attachmentId: string) {
  return del<SuccessResponse>(`/expenses/${expenseId}/attachments/${attachmentId}`)
}

// ── Payables ──

export function getPayables(params?: {
  page?: number
  page_size?: number
  keyword?: string
  status?: string
  source_type?: string
  supplier_id?: string
}) {
  return get<PaginatedData<PayableResponse>>('/payables/', { params })
}

export function getPayable(sourceType: string, sourceId: string) {
  return get<PayableResponse>(`/payables/${sourceType}/${sourceId}`)
}

export function createPayablePayment(
  sourceType: string,
  sourceId: string,
  data: {
    amount: number
    payment_method: string
    paid_at?: string
    remark?: string
    receipt_url?: string
  },
) {
  return post<PayableResponse>(`/payables/${sourceType}/${sourceId}/payments`, data)
}

export function voidPayablePayment(
  sourceType: string,
  sourceId: string,
  paymentId: string,
  data: { void_reason: string },
) {
  return post<PayableResponse>(
    `/payables/${sourceType}/${sourceId}/payments/${paymentId}/void`,
    data,
  )
}

export function getDashboard() { return get<DashboardData>('/reports/dashboard') }
export function getDailyReport(date?: string) { return get<DailyReportData>('/reports/daily', { params: { date } }) }
export function getMonthlyReport(year?: number, month?: number) { return get<MonthlyReportData>('/reports/monthly', { params: { year, month } }) }
export function getCustomerDebt() { return get<CustomerDebtItem[]>('/reports/customer-debt') }
export function getTaskCompletionSummary(period: TaskCompletionPeriod) {
  return get<TaskCompletionSummary>('/reports/task-completion/summary', { params: { period } })
}
export function getTaskCompletionDetails(params: {
  period: TaskCompletionPeriod
  kind: TaskCompletionKind
  employee_id?: string
  task_type?: TaskCompletionType
  page?: number
  page_size?: number
}) {
  return get<TaskCompletionDetailsResponse>('/reports/task-completion/details', { params })
}

// ── Project Costs ──

export function getProjectCosts(params?: { page?: number; page_size?: number; order_id?: string; order_item_id?: string; quote_id?: string; category?: string; date_from?: string; date_to?: string }) {
  return get<PaginatedData<ProjectCostResponse>>('/project-costs/', { params })
}
export function createProjectCost(data: Omit<Partial<ProjectCostResponse>, 'id' | 'cost_no' | 'customer_id' | 'customer_name' | 'project_name' | 'created_by' | 'created_at'> & { quote_id?: string; order_item_ids?: string[] }) {
  return post<ProjectCostResponse>('/project-costs/', data)
}
export function updateProjectCost(id: string, data: Partial<Omit<ProjectCostResponse, 'id' | 'cost_no' | 'customer_id' | 'customer_name' | 'project_name' | 'created_by' | 'created_at'>>) {
  return put<ProjectCostResponse>(`/project-costs/${id}`, data)
}
export function deleteProjectCost(id: string) {
  return del<SuccessResponse>(`/project-costs/${id}`)
}

export function batchDeleteProjectCosts(ids: string[]) {
  return del<SuccessResponse>(`/project-costs/batch?cost_ids=${ids.join(',')}`)
}
export function getProjectCostSummary(orderIds: string[]) {
  return get<ProjectCostSummaryResponse>('/project-costs/summary', { params: { order_ids: orderIds.join(',') } })
}
export function getOrderProjectCostItemSummary(orderId: string) {
  return get<ProjectCostItemSummaryResponse>(`/project-costs/orders/${orderId}/item-summary`)
}
export function importProjectCosts(file: File, orderId?: string, quoteId?: string, sourceType: string = 'order') {
  const form = new FormData()
  form.append('file', file)
  const params: Record<string, string> = { source_type: sourceType }
  if (orderId) params.order_id = orderId
  if (quoteId) params.quote_id = quoteId
  return post<ProjectCostImportResponse>('/project-costs/import', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    params,
  })
}

export function getProjectCostAttachments(costId: string) {
  return get<AttachmentResponse[]>(`/project-costs/${costId}/attachments`)
}

export function uploadProjectCostAttachment(costId: string, file: File) {
  const form = new FormData()
  form.append('file', file)
  // Let the browser/Axios add the multipart boundary automatically.
  return post<AttachmentResponse>(`/project-costs/${costId}/upload`, form)
}

export function deleteProjectCostAttachment(attachmentId: string) {
  return del<SuccessResponse>(`/project-costs/attachments/${attachmentId}`)
}

// ── Cost Debts ──

export function getQuotesForCost(params?: { page?: number; page_size?: number; keyword?: string }) {
  return get<PaginatedData<QuoteCostResponse>>('/project-costs/quotes', { params })
}

export function getCostDebts(params?: { page?: number; page_size?: number; keyword?: string; is_settled?: boolean }) {
  return get<PaginatedData<DebtResponse>>('/project-costs/debts/list', { params })
}

export function settleCostDebt(costId: string, data: { settle_amount: number; payment_method: string; remark?: string }) {
  return post<ProjectCostResponse>(`/project-costs/${costId}/settle-debt`, data)
}
