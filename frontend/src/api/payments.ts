import { get, post, put, del } from './index'
import { PaginatedData, PaymentResponse, StatementResponse, StatementDetailResponse, ExpenseResponse, SuccessResponse, UploadResponse, DashboardData, DailyReportData, MonthlyReportData, CustomerDebtItem, ProjectCostResponse, ProjectCostImportResponse, ProjectCostSummaryResponse, AttachmentResponse, DebtResponse, QuoteCostResponse } from '@/types/api'

export function getPayments(params?: { page?: number; page_size?: number; order_id?: string; customer_id?: string; status?: string }) { return get<PaginatedData<PaymentResponse>>('/payments/', { params }) }
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

export function getExpenses(params?: { page?: number; page_size?: number; category?: string }) { return get<PaginatedData<ExpenseResponse>>('/expenses/', { params }) }
export function getExpense(id: string) { return get<ExpenseResponse>(`/expenses/${id}`) }
export function createExpense(data: Omit<Partial<ExpenseResponse>, 'id' | 'expense_no' | 'created_by' | 'created_at'>) { return post<ExpenseResponse>('/expenses/', data) }
export function updateExpense(id: string, data: Partial<Omit<ExpenseResponse, 'id' | 'expense_no' | 'created_by' | 'created_at'>>) { return put<ExpenseResponse>(`/expenses/${id}`, data) }
export function deleteExpense(id: string) { return del<SuccessResponse>(`/expenses/${id}`) }

export function getDashboard() { return get<DashboardData>('/reports/dashboard') }
export function getDailyReport(date?: string) { return get<DailyReportData>('/reports/daily', { params: { date } }) }
export function getMonthlyReport(year?: number, month?: number) { return get<MonthlyReportData>('/reports/monthly', { params: { year, month } }) }
export function getCustomerDebt() { return get<CustomerDebtItem[]>('/reports/customer-debt') }

// ── Project Costs ──

export function getProjectCosts(params?: { page?: number; page_size?: number; order_id?: string; category?: string; date_from?: string; date_to?: string }) {
  return get<PaginatedData<ProjectCostResponse>>('/project-costs/', { params })
}
export function createProjectCost(data: Omit<Partial<ProjectCostResponse>, 'id' | 'cost_no' | 'customer_id' | 'customer_name' | 'project_name' | 'created_by' | 'created_at'>) {
  return post<ProjectCostResponse>('/project-costs/', data)
}
export function updateProjectCost(id: string, data: Partial<Omit<ProjectCostResponse, 'id' | 'cost_no' | 'customer_id' | 'customer_name' | 'project_name' | 'created_by' | 'created_at'>>) {
  return put<ProjectCostResponse>(`/project-costs/${id}`, data)
}
export function deleteProjectCost(id: string) {
  return del<SuccessResponse>(`/project-costs/${id}`)
}
export function getProjectCostSummary(orderIds: string[]) {
  return get<ProjectCostSummaryResponse>('/project-costs/summary', { params: { order_ids: orderIds.join(',') } })
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
  return post<AttachmentResponse>(`/project-costs/${costId}/upload`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
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
