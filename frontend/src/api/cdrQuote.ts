/** CDR 智能报价 API 封装 */
import api from './index'

export interface PricingTraceStep {
  rule_code: string
  description: string
  input_value?: Record<string, any>
  output_value?: Record<string, any>
}

export interface PricingResult {
  billable_quantity: string
  unit_price: string
  subtotal_amount: string
  material_cost: string
  process_cost: string
  startup_fee: string
  total_cost: string
  discount_amount: string
  tax_amount: string
  total_amount: string
  minimum_charge_applied: boolean
  requires_approval: boolean
  warnings: string[]
  pricing_trace: PricingTraceStep[]
}

/** 报价试算 */
export async function calculatePricing(data: {
  product_id: string
  material_id?: string
  quantity?: number
  width_mm?: number
  height_mm?: number
  length_m?: number
  process_ids?: string[]
  customer_id?: string
  tax_rate?: number
}): Promise<PricingResult> {
  return api.post('/cdr/pricing/calculate', data)
}

/** 创建报价版本 */
export async function createQuoteVersion(quoteId: string, data: {
  notes?: string
  lines: any[]
}): Promise<any> {
  return api.post(`/cdr/quotes/${quoteId}/versions`, data)
}

/** 获取最新版本 */
export async function getLatestVersion(quoteId: string): Promise<any> {
  return api.get(`/cdr/quotes/${quoteId}/versions/latest`)
}

/** 获取版本历史 */
export async function listVersions(quoteId: string): Promise<any[]> {
  return api.get(`/cdr/quotes/${quoteId}/versions`)
}

/** 请求审批 */
export async function requestApproval(quoteId: string, data: {
  approval_type: string
  reason?: string
}): Promise<any> {
  return api.post(`/cdr/quotes/${quoteId}/approvals`, data)
}

/** 批准 */
export async function approveQuote(approvalId: string, comment?: string): Promise<any> {
  return api.post(`/cdr/approvals/${approvalId}/approve`, { comment })
}

/** 驳回 */
export async function rejectQuote(approvalId: string, comment?: string): Promise<any> {
  return api.post(`/cdr/approvals/${approvalId}/reject`, { comment })
}

/** 获取规则集列表 */
export async function listRuleSets(): Promise<any[]> {
  return api.get('/cdr/rule-sets')
}

/** 创建规则集 */
export async function createRuleSet(data: any): Promise<any> {
  return api.post('/cdr/rule-sets', data)
}

/** 获取客户协议价 */
export async function listCustomerAgreements(customerId?: string): Promise<any[]> {
  const params = customerId ? { customer_id: customerId } : {}
  return api.get('/cdr/customer-agreements', { params })
}

/** 创建客户协议价 */
export async function createCustomerAgreement(data: any): Promise<any> {
  return api.post('/cdr/customer-agreements', data)
}

/** 查询审计日志 */
export async function listAuditLogs(quoteId: string): Promise<any[]> {
  return api.get(`/cdr/quotes/${quoteId}/audit-logs`)
}

/** 转订单 */
export async function convertToOrder(quoteId: string): Promise<any> {
  return api.post(`/cdr/quotes/${quoteId}/convert-to-order`)
}

/** 获取报价详情 */
export async function getCDRQuote(quoteId: string): Promise<any> {
  return api.get(`/cdr/quotes/${quoteId}`)
}

/** 报价列表 */
export async function listCDRQuotes(params?: Record<string, any>): Promise<any> {
  return api.get('/cdr/quotes', { params })
}
