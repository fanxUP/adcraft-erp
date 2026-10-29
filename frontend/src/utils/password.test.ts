import { describe, expect, it } from 'vitest'
import { passwordError } from './password'

describe('新密码字节限制', () => {
  it('检查 ASCII、汉字和表情的实际 UTF-8 长度', () => {
    expect(passwordError('a'.repeat(72))).toBeNull()
    expect(passwordError('中'.repeat(24))).toBeNull()
    expect(passwordError('中'.repeat(25))).toContain('72')
    expect(passwordError('😀'.repeat(19))).toContain('72')
    expect(passwordError('short')).toContain('6')
  })
})
