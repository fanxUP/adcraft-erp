import { describe, expect, it } from 'vitest'
import { attachmentUploadHistory } from './attachmentUploadHistory'

describe('同名资料上传历史', () => {
  const record = (id: string, created_at: string | null, extra = {}) => ({ id, filename: '稿件.pdf', stage: 'design', order_item_id: 'item1', created_at, ...extra })
  it('同明细同阶段同文件名按时间比较，旧文件保留且不修改输入', () => {
    const records = [record('a', '2026-10-27T00:00:00'), record('b', '2026-10-27T09:00:00+08:00')]
    const history = attachmentUploadHistory(records)
    expect(history.get('a')).toMatchObject({ count: 2, latestId: 'b' })
    expect(history.get('a')?.records.map(row => row.id)).toEqual(['b', 'a'])
    expect(records.map(row => row.id)).toEqual(['a', 'b'])
  })
  it('同名不同明细、阶段、大小写以及无明细的历史文件均不合并', () => {
    const records = [record('a', null), record('b', null, { order_item_id: 'item2' }), record('c', null, { stage: 'production' }),
      record('d', null, { filename: '稿件.PDF' }), record('e', null, { order_item_id: null }), record('f', null, { order_item_id: null })]
    expect([...attachmentUploadHistory(records).values()].map(value => value.count)).toEqual([1, 1, 1, 1, 1, 1])
  })
  it.each([null, '', 'bad-time', '2026-10-27T00:00:00Z'])('时间缺失、无效或相同时不指定唯一最近：%s', value => {
    expect(attachmentUploadHistory([record('a', '2026-10-27T00:00:00Z'), record('b', value)]).get('a')?.latestId).toBeNull()
  })
})
