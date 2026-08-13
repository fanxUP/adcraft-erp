export type TagType = '' | 'success' | 'warning' | 'danger' | 'info'
export type BusinessCardType = 'order' | 'quote' | 'task'

const statusTypes: Record<BusinessCardType, Record<string, TagType>> = {
  order: {
    pending_confirm: 'warning',
    confirmed: '',
    designing: '',
    in_production: '',
    in_installation: '',
    completed: 'success',
    cancelled: 'danger',
  },
  quote: {
    draft: 'info',
    confirmed: 'success',
    converted: 'success',
    cancelled: 'danger',
  },
  task: {
    pending: 'warning',
    in_progress: '',
    pending_acceptance: 'warning',
    completed: 'success',
    failed: 'danger',
    rework: 'warning',
  },
}

const statusLabels: Record<BusinessCardType, Record<string, string>> = {
  order: {
    pending_confirm: '待确认',
    confirmed: '已确认',
    designing: '设计中',
    in_production: '生产中',
    in_installation: '安装中',
    completed: '已完成',
    cancelled: '已取消',
  },
  quote: {
    draft: '草稿',
    confirmed: '已确认',
    converted: '已转订单',
    cancelled: '已作废',
  },
  task: {
    pending: '待处理',
    in_progress: '进行中',
    pending_acceptance: '待验收',
    completed: '已完成',
    failed: '失败',
    rework: '返工',
  },
}

export function getStatusTagType(
  status: string,
  cardType?: string,
): TagType {
  if (!cardType || !(cardType in statusTypes)) return 'info'
  return statusTypes[cardType as BusinessCardType][status] || 'info'
}

export function getStatusLabel(status: string, cardType?: string): string {
  if (!cardType || !(cardType in statusLabels)) return status
  return statusLabels[cardType as BusinessCardType][status] || status
}

export function formatAmount(amount: number): string {
  return amount.toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

export function formatFileSize(size?: number): string {
  if (!size) return ''
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}

export function shouldShowMessageTime(
  current: { created_at: string },
  previous?: { created_at: string },
): boolean {
  if (!previous) return true
  const currentTime = new Date(current.created_at).getTime()
  const previousTime = new Date(previous.created_at).getTime()
  return currentTime - previousTime > 5 * 60 * 1000
}
