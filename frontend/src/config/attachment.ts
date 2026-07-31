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
