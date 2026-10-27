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
export const createCompanyAccount = (data: Partial<CompanyAccount>) => post<CompanyAccount>('/company-accounts/', data)
export const updateCompanyAccount = (id: string, data: Partial<CompanyAccount>) => put<CompanyAccount>(`/company-accounts/${id}`, data)
export const deleteCompanyAccount = (id: string) => del<{ deleted: boolean }>(`/company-accounts/${id}`)
export const assignPaymentAccount = (kind: PaymentAccountKind, id: string, payment_account_id: string) =>
  put<{ updated: boolean }>(`/company-accounts/assignments/${kind}/${id}`, { payment_account_id })
