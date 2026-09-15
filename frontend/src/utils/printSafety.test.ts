import { describe, expect, it } from 'vitest'
import { escapePrintText } from './printSafety'

describe('打印动态文本安全处理', () => {
  it('转义 HTML 特殊字符，避免业务字段变成可执行标记', () => {
    expect(escapePrintText(`<img src=x onerror="alert('x')">`)).toBe(
      '&lt;img src=x onerror=&quot;alert(&#39;x&#39;)&quot;&gt;',
    )
  })

  it('保留零值并为缺失值提供可读占位符', () => {
    expect(escapePrintText(0)).toBe('0')
    expect(escapePrintText('')).toBe('-')
    expect(escapePrintText(null, '暂无')).toBe('暂无')
  })
})
