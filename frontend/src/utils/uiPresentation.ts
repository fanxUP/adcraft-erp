import type { StatusView as ApiStatusView } from '@/types/api'

export type UiTone = 'brand' | 'success' | 'warning' | 'danger' | 'info' | 'neutral'

export interface UiStatusPresentation {
  code: string
  label: string
  tone: UiTone
  terminal: boolean
}

type StatusDefaults = Omit<UiStatusPresentation, 'code'>

/**
 * 这里只保存展示层默认值，不参与权限、阶段推进或任务完成判断。
 * 后端返回 label/tone/terminal 后，页面应优先传入服务端结果。
 */
const STATUS_DEFAULTS: Readonly<Record<string, StatusDefaults>> = {
  pending: { label: '待处理', tone: 'warning', terminal: false },
  pending_confirm: { label: '待确认', tone: 'warning', terminal: false },
  pending_sign: { label: '待签约', tone: 'warning', terminal: false },
  confirmed: { label: '已确认', tone: 'info', terminal: false },
  designing: { label: '设计中', tone: 'info', terminal: false },
  in_design: { label: '设计中', tone: 'info', terminal: false },
  in_production: { label: '制作中', tone: 'info', terminal: false },
  production: { label: '制作中', tone: 'info', terminal: false },
  in_installation: { label: '安装中', tone: 'info', terminal: false },
  installation: { label: '安装中', tone: 'info', terminal: false },
  blocked: { label: '已阻塞', tone: 'danger', terminal: false },
  active: { label: '生效中', tone: 'info', terminal: false },
  terminated: { label: '已终止', tone: 'danger', terminal: true },
  converted: { label: '已转订单', tone: 'info', terminal: true },
  voided: { label: '已作废', tone: 'danger', terminal: true },
  debt: { label: '待结清', tone: 'warning', terminal: false },
  settled: { label: '已结清', tone: 'success', terminal: true },
  unpaid: { label: '待付款', tone: 'warning', terminal: false },
  partial: { label: '部分付款', tone: 'warning', terminal: false },
  paid: { label: '已付款', tone: 'success', terminal: true },
  completed: { label: '已完成', tone: 'success', terminal: true },
  complete: { label: '已完成', tone: 'success', terminal: true },
  cancelled: { label: '已取消', tone: 'neutral', terminal: true },
  canceled: { label: '已取消', tone: 'neutral', terminal: true },
}

export function normalizeProgress(value: number | null | undefined): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) return 0
  return Math.min(100, Math.max(0, Math.round(value)))
}

export function resolveStatusPresentation(
  status?: string | ApiStatusView | null,
  label?: string | null,
  tone?: UiTone,
  terminal?: boolean,
): UiStatusPresentation {
  const serverView = status && typeof status === 'object' ? status : undefined
  const rawCode = typeof status === 'string' ? status : serverView?.code
  const code = rawCode?.trim() || 'unknown'
  const defaults = STATUS_DEFAULTS[code]
  return {
    code,
    label: label?.trim() || serverView?.label?.trim() || defaults?.label || code,
    tone: tone || serverView?.tone || defaults?.tone || 'neutral',
    terminal: terminal ?? serverView?.terminal ?? defaults?.terminal ?? false,
  }
}

export function progressTone(tone: UiTone | undefined, progress: number): UiTone {
  if (tone) return tone
  return normalizeProgress(progress) >= 100 ? 'success' : 'brand'
}
