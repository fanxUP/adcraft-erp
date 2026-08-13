export interface QuoteGroupColorRegistry {
  colorFor(groupName: string): number
  rename(oldName: string, newName: string): void
  reset(): void
}

/**
 * 为分项分配稳定的调色板序号。
 * 颜色跟随分项身份，不随展示位置重新计算。
 */
export function createQuoteGroupColorRegistry(paletteSize = 10): QuoteGroupColorRegistry {
  const size = Math.max(1, Math.floor(paletteSize))
  const colors = new Map<string, number>()
  let nextColorIndex = 1

  const colorFor = (groupName: string): number => {
    const existing = colors.get(groupName)
    if (existing !== undefined) return existing

    const assigned = nextColorIndex
    colors.set(groupName, assigned)
    nextColorIndex = (nextColorIndex % size) + 1
    return assigned
  }

  const rename = (oldName: string, newName: string): void => {
    if (!oldName || !newName || oldName === newName) return
    const assigned = colors.get(oldName)
    if (assigned === undefined) return
    colors.delete(oldName)
    colors.set(newName, assigned)
  }

  const reset = (): void => {
    colors.clear()
    nextColorIndex = 1
  }

  return { colorFor, rename, reset }
}
