import { describe, expect, it } from 'vitest'

import { createQuoteGroupColorRegistry } from './quoteGroupColors'
import { applyQuoteDisplayOrder, buildQuoteDisplayRows, reorderQuoteDisplayRows } from './quoteItemOrdering'

describe('quoteGroupColors', () => {
  it('keeps each group color attached to the group after reordering', () => {
    const colors = createQuoteGroupColorRegistry(5)
    const items = [
      { id: 'a', group_name: '分项A' },
      { id: 'b', group_name: '分项B' },
    ]
    const rows = buildQuoteDisplayRows(items, item => item.id, () => 0, colors.colorFor)

    expect(rows.filter(row => row.type === 'group-header').map(row => [row.groupName, row.colorIndex]))
      .toEqual([['分项A', 1], ['分项B', 2]])

    const movedItems = applyQuoteDisplayOrder(reorderQuoteDisplayRows(rows, 'gh-b', 'gh-a'))
    const rebuiltRows = buildQuoteDisplayRows(movedItems, item => item.id, () => 0, colors.colorFor)
    expect(rebuiltRows.filter(row => row.type === 'group-header').map(row => [row.groupName, row.colorIndex]))
      .toEqual([['分项B', 2], ['分项A', 1]])
  })

  it('keeps the original group color after renaming', () => {
    const colors = createQuoteGroupColorRegistry(5)

    expect(colors.colorFor('分项A')).toBe(1)
    colors.rename('分项A', '门头部分')

    expect(colors.colorFor('门头部分')).toBe(1)
  })

  it('starts a fresh palette when another quote is loaded', () => {
    const colors = createQuoteGroupColorRegistry(5)
    colors.colorFor('分项A')
    colors.colorFor('分项B')

    colors.reset()

    expect(colors.colorFor('新报价分项')).toBe(1)
  })
})
