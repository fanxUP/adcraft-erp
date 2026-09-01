export interface QuoteGroupColorRegistry {
  colorFor(groupId: string): number
  rename(oldId: string, newId: string): void
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

  const colorFor = (groupId: string): number => {
    const existing = colors.get(groupId)
    if (existing !== undefined) return existing

    const assigned = nextColorIndex
    colors.set(groupId, assigned)
    nextColorIndex = (nextColorIndex % size) + 1
    return assigned
  }

  const rename = (oldId: string, newId: string): void => {
    if (!oldId || !newId || oldId === newId) return
    const assigned = colors.get(oldId)
    if (assigned === undefined) return
    colors.delete(oldId)
    colors.set(newId, assigned)
  }

  const reset = (): void => {
    colors.clear()
    nextColorIndex = 1
  }

  return { colorFor, rename, reset }
}
