import type { ApiEnvelope, ApiFieldError, ApiMeta } from '@/types/api'

type UnknownRecord = Record<string, unknown>

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === 'object' && value !== null
}

function asMessage(value: unknown): string | undefined {
  return typeof value === 'string' && value.trim() ? value.trim() : undefined
}

function inferHttpStatus(code: number | undefined): number | undefined {
  if (code === undefined) return undefined
  if (code >= 400 && code <= 599) return code
  const prefix = Math.floor(code / 100)
  return prefix >= 400 && prefix <= 599 ? prefix : undefined
}

function readHeader(headers: unknown, name: string): string | undefined {
  if (!isRecord(headers)) return undefined
  const getter = headers.get
  if (typeof getter === 'function') {
    const value = getter.call(headers, name)
    return asMessage(value)
  }
  return asMessage(headers[name]) || asMessage(headers[name.toLowerCase()])
}

export class ApiRequestError extends Error {
  readonly status?: number
  readonly code?: number
  readonly requestId?: string
  readonly details?: unknown
  readonly fieldErrors: ApiFieldError[]

  constructor(message: string, options: {
    status?: number
    code?: number
    requestId?: string
    details?: unknown
    fieldErrors?: ApiFieldError[]
  } = {}) {
    super(message)
    this.name = 'ApiRequestError'
    this.status = options.status
    this.code = options.code
    this.requestId = options.requestId
    this.details = options.details
    this.fieldErrors = options.fieldErrors || []
  }
}

export function isApiEnvelope(value: unknown): value is ApiEnvelope<unknown> {
  return isRecord(value)
    && typeof value.code === 'number'
    && typeof value.message === 'string'
    && Object.prototype.hasOwnProperty.call(value, 'data')
}

function normalizeFieldErrors(body: unknown, envelope: ApiEnvelope<unknown> | undefined): ApiFieldError[] {
  const data = envelope?.data
  const candidates = [
    isRecord(data) ? data.fields : undefined,
    isRecord(body) ? body.detail : undefined,
  ]
  const fields = candidates.find(Array.isArray)
  if (!Array.isArray(fields)) return []
  return fields.flatMap((item): ApiFieldError[] => {
    if (!isRecord(item) || typeof item.msg !== 'string') return []
    const loc = Array.isArray(item.loc) ? item.loc.filter((part): part is string | number => (
      typeof part === 'string' || typeof part === 'number'
    )) : []
    return [{ loc, msg: item.msg, type: asMessage(item.type) }]
  })
}

export function toApiRequestError(error: unknown): ApiRequestError {
  if (error instanceof ApiRequestError) return error

  const source = isRecord(error) ? error : {}
  const response = isRecord(source.response) ? source.response : undefined
  const body = response?.data
  const envelope = isApiEnvelope(body) ? body : undefined
  const bodyRecord = isRecord(body) ? body : undefined
  const code = typeof envelope?.code === 'number'
    ? envelope.code
    : (typeof bodyRecord?.code === 'number' ? bodyRecord.code : undefined)
  const responseStatus = typeof response?.status === 'number' ? response.status : undefined
  const status = responseStatus && responseStatus >= 400
    ? responseStatus
    : inferHttpStatus(code) || responseStatus
  const meta = isRecord(envelope?.meta) ? envelope?.meta as ApiMeta : undefined
  const requestId = readHeader(response?.headers, 'x-request-id') || asMessage(meta?.request_id)
  const fieldErrors = normalizeFieldErrors(body, envelope)
  const detail = bodyRecord?.detail
  const message = asMessage(envelope?.message)
    || asMessage(bodyRecord?.message)
    || (typeof detail === 'string' ? detail : undefined)
    || asMessage(source.message)
    || '请求失败'

  return new ApiRequestError(message, {
    status,
    code,
    requestId,
    details: envelope?.data ?? detail,
    fieldErrors,
  })
}

export function formatApiError(error: unknown, fallback = '操作失败'): string {
  const normalized = toApiRequestError(error)
  if (normalized.fieldErrors.length) {
    return normalized.fieldErrors.map(field => field.msg).join('；')
  }
  if (normalized.status === 401) return normalized.message || '登录已过期，请重新登录'
  if (normalized.status === 403 && normalized.code === 40300) return '请先修改初始密码'
  if (normalized.status === 403) return normalized.message || '没有权限执行此操作'
  if (normalized.status === 409) return normalized.message || '数据已发生变化，请刷新后重试'
  if (normalized.status === 422) return normalized.message || '请求参数错误'
  if (normalized.status !== undefined && normalized.status >= 500) {
    return '服务器暂时不可用，请稍后重试'
  }
  if (normalized.status === undefined && normalized.message === 'Network Error') {
    return '网络连接失败，请检查网络后重试'
  }
  return normalized.message || fallback
}
