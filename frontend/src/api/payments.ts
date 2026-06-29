import api from './index'

export function getPayments(params?: any) { return api.get('/payments/', { params }) }
export function getPayment(id: string) { return api.get(`/payments/${id}`) }
export function createPayment(data: any) { return api.post('/payments/', data) }
export function voidPayment(id: string, data: { void_reason: string }) { return api.post(`/payments/${id}/void`, data) }
export function uploadReceipt(paymentId: string, file: File) {
  const form = new FormData()
  form.append('file', file)
  return api.post(`/payments/${paymentId}/upload-receipt`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function getStatements(params?: any) { return api.get('/statements/', { params }) }
export function getStatement(id: string) { return api.get(`/statements/${id}`) }
export function createStatement(data: any) { return api.post('/statements/', data) }
export function confirmStatement(id: string) { return api.post(`/statements/${id}/confirm`) }

export function getExpenses(params?: any) { return api.get('/expenses/', { params }) }
export function getExpense(id: string) { return api.get(`/expenses/${id}`) }
export function createExpense(data: any) { return api.post('/expenses/', data) }
export function updateExpense(id: string, data: any) { return api.put(`/expenses/${id}`, data) }
export function deleteExpense(id: string) { return api.delete(`/expenses/${id}`) }

export function getDashboard() { return api.get('/reports/dashboard') }
export function getDailyReport(date?: string) { return api.get('/reports/daily', { params: { date } }) }
export function getMonthlyReport(year?: number, month?: number) { return api.get('/reports/monthly', { params: { year, month } }) }
export function getCustomerDebt() { return api.get('/reports/customer-debt') }
