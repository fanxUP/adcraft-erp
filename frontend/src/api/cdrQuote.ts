/** CDR 智能报价 API 封装 */
import api from './index'
import type { PaginatedData, QuoteListResponse } from '@/types/api'

export type CDRQueryParams = Record<string, string | number | boolean | undefined>

export interface PricingTraceStep {
  rule_code: string
  description: string
  input_value?: Record<string, unknown>
  output_value?: Record<string, unknown>
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

export interface PricingRequest {
  product_id: string
  material_id?: string
  quantity?: number
  width_mm?: number
  height_mm?: number
  length_m?: number
  process_ids?: string[]
  customer_id?: string
  tax_rate?: number
}

export interface QuoteLineProcessInput {
  process_id: string
  billing_quantity?: number
  unit?: string
  unit_price?: number
}

export interface QuoteLineInput {
  product_id?: string
  material_id?: string
  item_name: string
  description?: string
  material_process?: string
  width?: number
  width_unit?: string
  height?: number
  height_unit?: string
  width_mm?: number
  height_mm?: number
  length_m?: number
  quantity?: number
  unit?: string
  use_area?: boolean
  pieces?: number
  unit_price?: number
  process_fee?: number
  installation_fee?: number
  design_fee?: number
  transport_fee?: number
  other_fee?: number
  remark?: string
  image_url?: string
  sort_order?: number
  group_name?: string
  manual_adjustment?: number
  manual_reason?: string
  processes?: QuoteLineProcessInput[]
}

export interface QuoteLineProcess {
  id: string
  process_id: string
  billing_quantity: string
  unit_price: string
  amount: string
}

export interface QuoteVersionLine {
  id: string
  line_no: number
  product_id?: string
  material_id?: string
  item_name: string
  description: string
  material_process?: string
  width?: string
  width_unit?: string
  height?: string
  height_unit?: string
  width_mm?: string
  height_mm?: string
  length_m?: string
  quantity: string
  unit?: string
  use_area?: boolean
  pieces?: string
  unit_price: string
  amount: string
  estimated_cost: string
  process_fee: string
  installation_fee: string
  design_fee: string
  transport_fee: string
  other_fee: string
  remark?: string
  image_url?: string
  sort_order: number
  group_name?: string
  source: string
  requires_approval: boolean
  processes: QuoteLineProcess[]
}

export interface QuoteVersion {
  id: string
  quote_id: string
  version_no: number
  status: string
  subtotal_amount: string
  total_amount: string
  estimated_cost: string
  estimated_profit: string
  estimated_margin: string
  notes?: string
  created_by?: string
  created_at?: string
  lines: QuoteVersionLine[]
}

export interface QuoteApproval {
  id: string
  quote_id: string
  quote_version_id?: string
  approval_type: string
  status: string
  reason?: string
  decision_comment?: string
  requested_by?: string
  approver_id?: string
  created_at?: string
  decided_at?: string
}

export interface PriceRuleInput {
  code: string
  name: string
  priority?: number
  conditions_json?: Record<string, unknown>
  actions_json?: Record<string, unknown>
  conflict_policy?: string
}

export interface PriceRuleSetInput {
  code: string
  name: string
  effective_from?: string
  effective_to?: string
  description?: string
  rules?: PriceRuleInput[]
}

export interface PriceRuleSet extends PriceRuleSetInput {
  id: string
  version: number
  status: string
}

export interface CustomerAgreementInput {
  customer_id: string
  product_id?: string
  material_id?: string
  process_id?: string
  pricing_method: string
  price_value: number
  minimum_charge?: number
  discount_rate?: number
  effective_from: string
  effective_to?: string
  remark?: string
}

export interface CustomerAgreement {
  id: string
  customer_id: string
  product_id?: string
  material_id?: string
  process_id?: string
  pricing_method: string
  price_value: string
  minimum_charge: string
  discount_rate: string
  effective_from: string
  effective_to?: string
  remark?: string
}

export interface CDRAuditLog {
  id: string
  actor_id?: string
  action: string
  reason?: string
  created_at?: string
}

export interface CDRQuote extends QuoteListResponse {
  doc_no?: string
  tax_rate?: number
  customer?: { name?: string }
}

export interface CDRQuoteCreate {
  project_name: string
  customer_id?: string
  customer_name?: string
  tax_rate?: number
  status?: string
}

export interface DesignAttachment {
  id: string
  filename: string
  file_size: number
  file_type: string
  created_at?: string
}

export interface ParsedShape {
  type: string
  width_mm: number
  height_mm: number
  area_m2: number
  quantity: number
  label: string
}

export interface SvgParseResult {
  document_width_mm?: number
  document_height_mm?: number
  shapes: ParsedShape[]
  shape_count: number
  total_area_m2?: number
  filename: string
  attachment_id: string
}

export interface CDRSuggestedLine {
  description?: string
  item_name?: string
  width_mm?: number
  height_mm?: number
  quantity?: number
  unit?: string
  material_suggestion?: string
}

export interface AiAssistResult {
  project_name: string
  files: string[]
  ai_suggestions:
    | CDRSuggestedLine[]
    | { items?: CDRSuggestedLine[]; lines?: CDRSuggestedLine[]; raw?: string }
}

/** 报价试算 */
export function calculatePricing(data: PricingRequest) {
  return api.post<PricingResult>('/cdr/pricing/calculate', data)
}

export function createCDRQuote(data: CDRQuoteCreate) {
  return api.post<CDRQuote>('/cdr/quotes', data)
}

/** 创建报价版本 */
export function createQuoteVersion(
  quoteId: string,
  data: { notes?: string; lines: QuoteLineInput[] },
) {
  return api.post<QuoteVersion>(`/cdr/quotes/${quoteId}/versions`, data)
}

export function getLatestVersion(quoteId: string) {
  return api.get<QuoteVersion | null>(`/cdr/quotes/${quoteId}/versions/latest`)
}

export function listVersions(quoteId: string) {
  return api.get<QuoteVersion[]>(`/cdr/quotes/${quoteId}/versions`)
}

export function listApprovals(quoteId: string) {
  return api.get<QuoteApproval[]>(`/cdr/quotes/${quoteId}/approvals`)
}

export function requestApproval(
  quoteId: string,
  data: { approval_type: string; reason?: string },
) {
  return api.post<QuoteApproval>(`/cdr/quotes/${quoteId}/approvals`, data)
}

export function approveQuote(approvalId: string, comment?: string) {
  return api.post<{ status: string }>(`/cdr/approvals/${approvalId}/approve`, { comment })
}

export function rejectQuote(approvalId: string, comment?: string) {
  return api.post<{ status: string }>(`/cdr/approvals/${approvalId}/reject`, { comment })
}

export function listRuleSets() {
  return api.get<PriceRuleSet[]>('/cdr/rule-sets')
}

export function createRuleSet(data: PriceRuleSetInput) {
  return api.post<Pick<PriceRuleSet, 'id' | 'code' | 'name'>>('/cdr/rule-sets', data)
}

export function listCustomerAgreements(customerId?: string) {
  const params = customerId ? { customer_id: customerId } : {}
  return api.get<CustomerAgreement[]>('/cdr/customer-agreements', { params })
}

export function createCustomerAgreement(data: CustomerAgreementInput) {
  return api.post<Pick<CustomerAgreement, 'id' | 'customer_id'>>('/cdr/customer-agreements', data)
}

export function listAuditLogs(quoteId: string) {
  return api.get<CDRAuditLog[]>(`/cdr/quotes/${quoteId}/audit-logs`)
}

export function deleteCDRQuote(quoteId: string) {
  return api.del<{ deleted: boolean }>(`/cdr/quotes/${quoteId}`)
}

export function convertToOrder(quoteId: string) {
  return api.post<{ id: string; doc_no: string }>(`/cdr/quotes/${quoteId}/convert-to-order`)
}

export function getCDRQuote(quoteId: string) {
  return api.get<CDRQuote>(`/cdr/quotes/${quoteId}`)
}

export function listCDRQuotes(params?: CDRQueryParams) {
  return api.get<PaginatedData<CDRQuote>>('/cdr/quotes', { params })
}

export function uploadDesignFile(quoteId: string, file: File) {
  const form = new FormData()
  form.append('file', file)
  return api.post<DesignAttachment>(`/cdr/quotes/${quoteId}/upload`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function listDesignAttachments(quoteId: string) {
  return api.get<DesignAttachment[]>(`/cdr/quotes/${quoteId}/attachments`)
}

export function deleteDesignAttachment(attId: string) {
  return api.del<{ deleted: boolean }>(`/cdr/attachments/${attId}`)
}

export function parseSvgAttachment(attId: string) {
  return api.post<SvgParseResult>(`/cdr/attachments/${attId}/parse-svg`)
}

export function aiAssistFromDescription(quoteId: string, description: string) {
  return api.post<AiAssistResult>(`/cdr/quotes/${quoteId}/ai-assist-description`, { description })
}
