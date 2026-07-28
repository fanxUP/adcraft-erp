import { describe, expect, it } from 'vitest'
import { resolvePageContext } from './pageContext'

describe('resolvePageContext', () => {
  it('adds route business id to order detail context', () => {
    expect(resolvePageContext('OrderDetail', { id: 'order-1' })).toEqual({
      page: 'order_detail',
      business_type: 'order',
      business_id: 'order-1',
    })
  })

  it('returns an empty context for unknown routes', () => {
    expect(resolvePageContext('Unknown', {})).toEqual({})
  })
})
