// 附件分类共享字典（高空车人员 + 员工 两模块共用）
export const ATTACHMENT_TYPE_OPTIONS = [
  { label: '身份证', value: 'id_card' },
  { label: '驾驶证', value: 'license' },
  { label: '资格证', value: 'qualification' },
  { label: '银行卡', value: 'bank_card' },
  { label: '保险', value: 'insurance' },
  { label: '其他', value: 'other' },
]

export const ATTACHMENT_TYPE_LABELS: Record<string, string> = Object.fromEntries(
  ATTACHMENT_TYPE_OPTIONS.map((o) => [o.value, o.label]),
)

export const ATTACHMENT_TYPE_TAGS: Record<string, 'primary' | 'success' | 'warning' | 'danger' | 'info'> = {
  id_card: 'primary',
  license: 'success',
  qualification: 'warning',
  bank_card: 'danger',
  insurance: 'info',
  other: 'info',
}

// 高空车档案附件分类（行驶证/登记证/保险单/年检/保养等）
export const VEHICLE_ATTACHMENT_TYPE_OPTIONS = [
  { label: '行驶证', value: 'license' },
  { label: '登记证', value: 'registration' },
  { label: '保险单', value: 'insurance' },
  { label: '年检', value: 'inspection' },
  { label: '保养记录', value: 'maintenance' },
  { label: '其他', value: 'other' },
]

export const VEHICLE_ATTACHMENT_TYPE_LABELS: Record<string, string> = Object.fromEntries(
  VEHICLE_ATTACHMENT_TYPE_OPTIONS.map((o) => [o.value, o.label]),
)

export const VEHICLE_ATTACHMENT_TYPE_TAGS: Record<string, 'primary' | 'success' | 'warning' | 'danger' | 'info'> = {
  license: 'success',
  registration: 'primary',
  insurance: 'info',
  inspection: 'warning',
  maintenance: 'danger',
  other: 'info',
}
