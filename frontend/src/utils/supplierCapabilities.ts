import type { VendorResponse } from '@/types/api'

export const supplierTypeOptions = [
  { value: 'outsource', label: '外协服务' }, { value: 'material', label: '材料供应' },
  { value: 'equipment', label: '设备供应' }, { value: 'transport', label: '运输服务' },
  { value: 'service', label: '其他服务' }, { value: 'other', label: '其他供应商' },
]
export const serviceTypeOptions = [
  { value: 'production', label: '制作' }, { value: 'installation', label: '安装' },
  { value: 'design', label: '设计' }, { value: 'transport', label: '运输' },
]

export function supplierRoles(row: Pick<VendorResponse, 'supplier_types' | 'supplier_type'>): string[] {
  return row.supplier_types ?? [row.supplier_type || 'outsource']
}
export function supplierServices(row: Pick<VendorResponse, 'service_types' | 'service_type'>): string[] {
  return row.service_types ?? (row.service_type ? [row.service_type] : serviceTypeOptions.map(option => option.value))
}
export function canUndertakeOutsource(row: VendorResponse, taskType: string): boolean {
  return row.is_active && supplierRoles(row).includes('outsource') && supplierServices(row).includes(taskType)
}
export function choiceLabels(values: string[], options: { value: string; label: string }[]): string {
  return values.map(value => options.find(option => option.value === value)?.label || value).join('、') || '-'
}
