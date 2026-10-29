export function passwordError(value: string): string | null {
  if (value.length < 6) return '新密码至少 6 位'
  if (new TextEncoder().encode(value).length > 72) return '新密码不能超过 72 个 UTF-8 字节（汉字通常占 3 字节）'
  return null
}
