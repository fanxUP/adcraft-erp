export const REQUIRED_VIEWPORTS = [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'tablet', width: 1024, height: 768 },
  { name: 'mobile', width: 390, height: 844 },
] as const

export const MIN_TOUCH_TARGET_PX = 40

export function hasMinimumTouchTarget(width: number, height: number, minimum = MIN_TOUCH_TARGET_PX): boolean {
  return width >= minimum && height >= minimum
}

function channel(value: number): number {
  const normalized = value / 255
  return normalized <= 0.03928
    ? normalized / 12.92
    : ((normalized + 0.055) / 1.055) ** 2.4
}

/** WCAG relative luminance contrast ratio for six-digit hex colors. */
export function contrastRatio(foreground: string, background: string): number {
  const parse = (value: string): [number, number, number] => {
    const hex = value.replace('#', '')
    if (!/^[0-9a-fA-F]{6}$/.test(hex)) return [0, 0, 0]
    return [
      Number.parseInt(hex.slice(0, 2), 16),
      Number.parseInt(hex.slice(2, 4), 16),
      Number.parseInt(hex.slice(4, 6), 16),
    ]
  }
  const luminance = (value: string) => {
    const [red, green, blue] = parse(value)
    return 0.2126 * channel(red) + 0.7152 * channel(green) + 0.0722 * channel(blue)
  }
  const foregroundLuminance = luminance(foreground)
  const backgroundLuminance = luminance(background)
  const lighter = Math.max(foregroundLuminance, backgroundLuminance)
  const darker = Math.min(foregroundLuminance, backgroundLuminance)
  return (lighter + 0.05) / (darker + 0.05)
}

export function includesAny(source: string, fragments: readonly string[]): boolean {
  return fragments.some(fragment => source.includes(fragment))
}
