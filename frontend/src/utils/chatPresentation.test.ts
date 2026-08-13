import { describe, expect, it } from 'vitest'
import {
  formatFileSize,
  getStatusLabel,
  shouldShowMessageTime,
} from './chatPresentation'

describe('chat presentation helpers', () => {
  it('uses the canonical order workflow labels', () => {
    expect(getStatusLabel('in_installation', 'order')).toBe('安装中')
  })

  it('formats file sizes', () => {
    expect(formatFileSize(512)).toBe('512 B')
    expect(formatFileSize(2048)).toBe('2.0 KB')
  })

  it('shows a timestamp after a five minute gap', () => {
    const previous = { created_at: '2026-07-28T10:00:00' }
    expect(shouldShowMessageTime(
      { created_at: '2026-07-28T10:06:00' },
      previous,
    )).toBe(true)
  })
})
