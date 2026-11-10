import { get, post, put, del } from './index'

export type CompanyAccountType = 'bank' | 'wechat' | 'alipay' | 'cash' | 'other'
export interface CompanyAccount {
  id: string
  name: string
  account_type: CompanyAccountType
  holder_name?: string | null
  bank_name?: string | null
  account_number?: string | null
  masked_number?: string | null
  label: string
  is_active: boolean
  is_default: boolean
  is_referenced?: boolean
  remark?: string | null
}
export type PaymentAccountKind = 'expense' | 'project_cost' | 'payable_payment' | 'outsource_payment'
export const accountTypeLabels: Record<CompanyAccountType, string> = {
  bank: '银行账户', wechat: '微信', alipay: '支付宝', cash: '现金', other: '其他',
}
export const getCompanyAccounts = () => get<CompanyAccount[]>('/company-accounts/')
export const getCompanyAccountOptions = () => get<CompanyAccount[]>('/company-accounts/options', { params: { include_inactive: true } })
export interface BankLedgerRow {
  id: string
  entry_type: 'opening_balance' | 'source_payment' | 'source_receipt' | 'manual'
  source_label: string
  source_kind?: string
  source_id?: string | null
  document_id?: string | null
  document_type?: string | null
  entry_date: string
  summary: string
  counterparty_account: string | null
  counterparty_name: string | null
  counterparty_supplier_id?: string | null
  category: string | null
  income_amount: number
  expense_amount: number
  balance: number | null
  project_name: string | null
  department: string | null
  order_id?: string | null
}
export interface BankLedgerSupplierOption {
  id: string
  name: string
  vendor_no: string
}
export interface BankLedgerOrderOption {
  id: string
  doc_no: string
  project_name: string
  department: string | null
}
export interface BankLedgerResult {
  items: BankLedgerRow[]
  total: number
  page: number
  page_size: number
  opening_balance: { entry_date: string; amount: number } | null
  summary: {
    opening_balance: number | null
    income_amount: number
    expense_amount: number
    balance: number | null
    transaction_count: number
  }
}
export interface BankLedgerEntryCreate {
  request_id: string
  entry_date: string
  direction: 'income' | 'expense'
  amount: number
  summary: string
  counterparty_account?: string
  counterparty_name?: string
  counterparty_supplier_id?: string
  category?: string
  project_name?: string
  department?: string
  order_id?: string
}
type BankBusinessEntry = Pick<BankLedgerEntryCreate, 'request_id' | 'entry_date' | 'amount' | 'summary'> & { order_id: string }
export type BankLedgerPurpose = 'manual' | 'project_cost' | 'receipt'
export const getBankLedgerSupplierOptions = (keyword?: string) =>
  get<BankLedgerSupplierOption[]>('/company-accounts/ledger-options/suppliers', { params: keyword ? { keyword } : undefined })
export const getBankLedgerOrderOptions = (keyword: string, purpose: BankLedgerPurpose) =>
  get<BankLedgerOrderOption[]>('/company-accounts/ledger-options/orders', { params: { keyword, purpose } })
export const getBankLedger = (accountId: string, params?: { page?: number; page_size?: number }) =>
  get<BankLedgerResult>('/company-accounts/' + accountId + '/ledger', { params })
export const setBankLedgerOpeningBalance = (
  accountId: string,
  data: { entry_date: string; amount: number },
) => put<{ entry_date: string; amount: number }>('/company-accounts/' + accountId + '/opening-balance', data)
export const createBankLedgerEntry = (accountId: string, data: BankLedgerEntryCreate) =>
  post<{ id: string; account_id: string; entry_type: string; direction: string; entry_date: string; amount: number; summary: string }>(
    '/company-accounts/' + accountId + '/ledger-entries',
    data,
  )
export const createBankProjectCost = (accountId: string, data: BankBusinessEntry & {
  category: string; supplier_id?: string; counterparty_name?: string
}) => post<{ id: string; cost_no: string }>(`/company-accounts/${accountId}/project-cost-payments`, data)
export const createBankCustomerReceipt = (accountId: string, data: BankBusinessEntry) =>
  post<{ id: string; payment_no: string }>(`/company-accounts/${accountId}/customer-receipts`, data)
export const createCompanyAccount = (data: Partial<CompanyAccount>) => post<CompanyAccount>('/company-accounts/', data)
export const updateCompanyAccount = (id: string, data: Partial<CompanyAccount>) => put<CompanyAccount>(`/company-accounts/${id}`, data)
export const deleteCompanyAccount = (id: string) => del<{ deleted: boolean }>(`/company-accounts/${id}`)
export const assignPaymentAccount = (kind: PaymentAccountKind, id: string, payment_account_id: string) =>
  put<{ updated: boolean }>(`/company-accounts/assignments/${kind}/${id}`, { payment_account_id })
