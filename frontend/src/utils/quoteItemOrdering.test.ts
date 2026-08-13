import { describe, expect, it } from 'vitest'

import {
  applyQuoteDisplayOrder,
  buildQuoteDisplayRows,
  getQuoteGroupDropSuccessorKey,
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
const totalOf = (items: Item[], groupName: string) => {
  const row = rowsOf(items).find(candidate => (
    candidate.type === 'group-total' && candidate.groupName === groupName
  ))
  return row?.type === 'group-total' ? row.total : undefined
}

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

  it('moves group A as a whole directly before group B', () => {
    const rows = rowsOf([
      item('b1', '分项B'), item('b2', '分项B'),
      item('a1', '分项A'), item('a2', '分项A'),
    ])
    const moved = reorderQuoteDisplayRows(rows, 'gh-a1', 'gh-b1')

    expect(moved.map(row => row.key)).toEqual([
      'gh-a1', 'a1', 'a2', 'gt-a1', 'gh-b1', 'b1', 'b2', 'gt-b1',
    ])
    expect(applyQuoteDisplayOrder(moved).map(value => value.id)).toEqual(['a1', 'a2', 'b1', 'b2'])
  })

  it('moves group A after the complete group B when dropped on a B detail', () => {
    const rows = rowsOf([
      item('a1', '分项A'), item('a2', '分项A'),
      item('b1', '分项B'), item('b2', '分项B'),
      item('c', '分项C'),
    ])
    const moved = reorderQuoteDisplayRows(rows, 'gh-a1', 'b2')

    expect(moved.map(row => row.key)).toEqual([
      'gh-b1', 'b1', 'b2', 'gt-b1',
      'gh-a1', 'a1', 'a2', 'gt-a1',
      'gh-c', 'c', 'gt-c',
    ])
  })

  it('keeps the earlier target group intact when a later group is dropped into it', () => {
    const rows = rowsOf([
      item('b1', '分项B'), item('b2', '分项B'),
      item('a1', '分项A'), item('a2', '分项A'),
      item('c1', '分项C'),
    ])
    const moved = reorderQuoteDisplayRows(rows, 'gh-a1', 'b2')

    expect(moved.map(row => row.key)).toEqual([
      'gh-b1', 'b1', 'b2', 'gt-b1',
      'gh-a1', 'a1', 'a2', 'gt-a1',
      'gh-c1', 'c1', 'gt-c1',
    ])
    expect(applyQuoteDisplayOrder(moved).map(value => [value.id, value.group_name])).toEqual([
      ['b1', '分项B'], ['b2', '分项B'],
      ['a1', '分项A'], ['a2', '分项A'],
      ['c1', '分项C'],
    ])
  })

  it('moves group A as a whole to the bottom', () => {
    const rows = rowsOf([
      item('a1', '分项A'), item('a2', '分项A'),
      item('b1', '分项B'), item('b2', '分项B'),
    ])
    const moved = reorderQuoteDisplayRows(rows, 'gh-a1', null)

    expect(moved.map(row => row.key)).toEqual([
      'gh-b1', 'b1', 'b2', 'gt-b1', 'gh-a1', 'a1', 'a2', 'gt-a1',
    ])
  })

  it('keeps a group intact when dropped into its own block', () => {
    const rows = rowsOf([item('a1', '分项A'), item('a2', '分项A'), item('b', '分项B')])

    expect(reorderQuoteDisplayRows(rows, 'gh-a1', 'a2')).toBe(rows)
  })

  it('converts every group hover target to a complete group boundary', () => {
    const rows = rowsOf([
      item('a1', '分项A'), item('a2', '分项A'),
      item('free'),
      item('b1', '分项B'), item('b2', '分项B'),
      item('c1', '分项C'),
    ])

    expect(getQuoteGroupDropSuccessorKey(rows, 'gh-a1', 'gh-b1')).toBe('gh-b1')
    expect(getQuoteGroupDropSuccessorKey(rows, 'gh-a1', 'b1')).toBe('gh-c1')
    expect(getQuoteGroupDropSuccessorKey(rows, 'gh-a1', 'gt-b1')).toBe('gh-c1')
    expect(getQuoteGroupDropSuccessorKey(rows, 'gh-a1', 'c1')).toBeNull()
    expect(getQuoteGroupDropSuccessorKey(rows, 'gh-a1', 'a2')).toBe('a2')
    expect(getQuoteGroupDropSuccessorKey(rows, 'gh-a1', 'free', true)).toBe('gh-b1')
  })

  it('keeps standalone details between groups instead of forcing them to the bottom', () => {
    const rows = rowsOf([item('a', '分项A'), item('free'), item('b', '分项B')])

    expect(rows.map(row => row.key)).toEqual([
      'gh-a', 'a', 'gt-a', 'free', 'gh-b', 'b', 'gt-b',
    ])
  })

  it('reorders one detail inside its original group', () => {
    const moving = item('a2', '分项A')
    const moved = reorderQuoteDisplayRows(rowsOf([item('a1', '分项A'), moving]), 'a2', 'a1')

    expect(applyQuoteDisplayOrder(moved).map(value => value.id)).toEqual(['a2', 'a1'])
    expect(moving.group_name).toBe('分项A')
  })

  it('moves only one detail to another group at the requested position', () => {
    const moving = item('a2', '分项A', 20)
    const moved = reorderQuoteDisplayRows(
      rowsOf([
        item('a1', '分项A', 10), moving,
        item('b1', '分项B', 30), item('b2', '分项B', 40),
      ]),
      'a2',
      'b2',
    )
    const reorderedItems = applyQuoteDisplayOrder(moved)

    expect(reorderedItems.map(value => value.id)).toEqual(['a1', 'b1', 'a2', 'b2'])
    expect(moving.group_name).toBe('分项B')
    expect(totalOf(reorderedItems, '分项A')).toBe(10)
    expect(totalOf(reorderedItems, '分项B')).toBe(90)
  })

  it('moves a detail below a group header as that group first detail', () => {
    const free = item('free')
    const moved = reorderQuoteDisplayRows(
      rowsOf([item('a', '分项A'), item('b', '分项B'), free]),
      'free',
      'b',
    )

    expect(applyQuoteDisplayOrder(moved).map(value => value.id)).toEqual(['a', 'free', 'b'])
    expect(free.group_name).toBe('分项B')
  })

  it('moves one detail after a group total as a standalone top-level row', () => {
    const moving = item('a2', '分项A')
    const moved = reorderQuoteDisplayRows(
      rowsOf([item('a1', '分项A'), moving, item('b', '分项B')]),
      'a2',
      'gh-b',
    )
    const reorderedItems = applyQuoteDisplayOrder(moved)

    expect(reorderedItems.map(value => value.id)).toEqual(['a1', 'a2', 'b'])
    expect(moving.group_name).toBeUndefined()
    expect(rowsOf(reorderedItems).map(row => row.key)).toEqual([
      'gh-a1', 'a1', 'gt-a1', 'a2', 'gh-b', 'b', 'gt-b',
    ])
  })

  it('removes an empty group when its last detail becomes standalone', () => {
    const only = item('only', '分项A')
    const moved = reorderQuoteDisplayRows(rowsOf([only, item('free')]), 'only', null)
    const reorderedItems = applyQuoteDisplayOrder(moved)

    expect(only.group_name).toBeUndefined()
    expect(rowsOf(reorderedItems).map(row => row.key)).toEqual(['free', 'only'])
  })
})
