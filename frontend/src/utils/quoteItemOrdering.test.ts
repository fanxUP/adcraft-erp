import { describe, expect, it } from 'vitest'

import {
  applyQuoteDisplayOrder,
  buildQuoteDisplayRows,
  isDuplicateQuoteGroupName,
  reorderQuoteDisplayRows,
} from './quoteItemOrdering'

interface Item {
  id: string
  group_name?: string
  amount: number
}

const item = (id: string, group_name?: string, amount = 1): Item => ({ id, group_name, amount })
const rowsOf = (items: Item[]) => buildQuoteDisplayRows(items, value => value.id, value => value.amount)

describe('quoteItemOrdering', () => {
  it('detects a rename that would silently merge two groups', () => {
    const items = [item('a', '分项A'), item('b', '分项B')]

    expect(isDuplicateQuoteGroupName(items, '分项A', '分项B')).toBe(true)
    expect(isDuplicateQuoteGroupName(items, '分项A', '分项C')).toBe(false)
  })

  it('uses stable group row keys after group order changes', () => {
    const a = item('a', '分项A')
    const b = item('b', '分项B')

    expect(rowsOf([a, b]).map(row => row.key)).toEqual(['gh-a', 'a', 'gt-a', 'gh-b', 'b', 'gt-b'])
    expect(rowsOf([b, a]).map(row => row.key)).toEqual(['gh-b', 'b', 'gt-b', 'gh-a', 'a', 'gt-a'])
  })

  it('moves a group header together with all details and its total', () => {
    const source = [item('a1', '分项A'), item('a2', '分项A'), item('b1', '分项B')]
    const moved = reorderQuoteDisplayRows(rowsOf(source), 'gh-a1', null)

    expect(moved.map(row => row.key)).toEqual([
      'gh-b1', 'b1', 'gt-b1', 'gh-a1', 'a1', 'a2', 'gt-a1',
    ])
    expect(applyQuoteDisplayOrder(moved).map(value => value.id)).toEqual(['b1', 'a1', 'a2'])
    expect(source.map(value => value.group_name)).toEqual(['分项A', '分项A', '分项B'])
  })

  it('snaps a group dropped inside another group to that group boundary', () => {
    const rows = rowsOf([
      item('a', '分项A'), item('b1', '分项B'), item('b2', '分项B'), item('c', '分项C'),
    ])
    const moved = reorderQuoteDisplayRows(rows, 'gh-a', 'b2')

    expect(moved.map(row => row.key)).toEqual([
      'gh-b1', 'b1', 'b2', 'gt-b1', 'gh-a', 'a', 'gt-a', 'gh-c', 'c', 'gt-c',
    ])
  })

  it('keeps a group intact when dropped into its own block', () => {
    const rows = rowsOf([item('a1', '分项A'), item('a2', '分项A'), item('b', '分项B')])

    expect(reorderQuoteDisplayRows(rows, 'gh-a1', 'a2')).toBe(rows)
  })

  it('moves a detail into a group and updates its group name', () => {
    const free = item('free')
    const moved = reorderQuoteDisplayRows(rowsOf([item('a', '分项A'), free]), 'free', 'gt-a')

    expect(applyQuoteDisplayOrder(moved).map(value => value.id)).toEqual(['a', 'free'])
    expect(free.group_name).toBe('分项A')
  })

  it('moves a detail out of a group when dropped after its total', () => {
    const moving = item('a2', '分项A')
    const moved = reorderQuoteDisplayRows(
      rowsOf([item('a1', '分项A'), moving, item('b', '分项B')]),
      'a2',
      'gh-b',
    )

    expect(applyQuoteDisplayOrder(moved).map(value => value.id)).toEqual(['a1', 'a2', 'b'])
    expect(moving.group_name).toBeUndefined()
  })
})
