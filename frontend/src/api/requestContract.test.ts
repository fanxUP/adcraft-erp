import { describe, expect, it } from 'vitest'
import {
  ApiRequestError,
  formatApiError,
  isApiEnvelope,
  toApiRequestError,
} from './requestContract'

describe('api contract helpers', () => {
  it('recognizes the shared response envelope without rejecting legacy payloads', () => {
    expect(isApiEnvelope({ code: 0, message: 'success', data: { id: '1' } })).toBe(true)
    expect(isApiEnvelope({ items: [] })).toBe(false)
  })

  it('preserves status, business code and request id for conflict errors', () => {
    const error = toApiRequestError({
      response: {
        status: 409,
        headers: { 'x-request-id': 'req-409' },
        data: {
          code: 40901,
          message: '订单已被其他人修改，请刷新订单后重试',
          data: null,
          meta: { request_id: 'req-409' },
        },
      },
    })

    expect(error).toBeInstanceOf(ApiRequestError)
    expect(error.status).toBe(409)
    expect(error.code).toBe(40901)
    expect(error.requestId).toBe('req-409')
    expect(formatApiError(error)).toContain('刷新')

    const legacyError = toApiRequestError({
      response: {
        status: 200,
        data: {
          code: 40901,
          message: '旧接口也应识别为并发冲突',
          data: null,
        },
      },
    })
    expect(legacyError.status).toBe(409)
  })

  it('maps validation fields and network failures to stable user feedback', () => {
    const validation = toApiRequestError({
      response: {
        status: 422,
        data: {
          code: 42200,
          message: '请求参数错误',
          data: {
            fields: [{ loc: ['body', 'order_item_ids'], msg: '至少选择一条明细' }],
          },
        },
      },
    })
    expect(formatApiError(validation)).toContain('至少选择一条明细')

    const network = toApiRequestError({ request: {}, message: 'Network Error' })
    expect(formatApiError(network)).toBe('网络连接失败，请检查网络后重试')
  })

  it('covers the shared transport error matrix', () => {
    const makeResponseError = (status: number, code: number, message = `错误 ${status}`) => (
      toApiRequestError({
        response: {
          status,
          data: { code, message, data: null },
        },
      })
    )

    expect(formatApiError(makeResponseError(400, 40001))).toBe('错误 400')
    expect(formatApiError(makeResponseError(401, 40100))).toBe('错误 401')
    expect(formatApiError(makeResponseError(403, 40301))).toBe('错误 403')
    expect(formatApiError(makeResponseError(403, 40300))).toBe('请先修改初始密码')
    expect(formatApiError(makeResponseError(409, 40901))).toBe('错误 409')
    expect(formatApiError(makeResponseError(422, 42200))).toBe('错误 422')
    expect(formatApiError(makeResponseError(500, 50000))).toBe('服务器暂时不可用，请稍后重试')
    expect(formatApiError(makeResponseError(503, 50300))).toBe('服务器暂时不可用，请稍后重试')
  })
})
