import { get, patch } from './index'

export interface FinanceCategoryOption {
  id: string
  name: string
  code: string
  sort_order: number
}

export function getFinanceCategories() {
  return get<FinanceCategoryOption[]>('/finance-categories/')
}

export function renameFinanceCategory(id: string, name: string) {
  return patch<{
    id: string
    name: string
    previous_name: string
    updated_bank_ledger_entries: number
    updated_project_costs: number
  }>(`/finance-categories/${id}`, { name })
}
