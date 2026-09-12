export type ThemeName = 'light-blue' | 'light-white' | 'dark-blue'

export interface ThemeInfo {
  name: ThemeName
  label: string
  desc: string
  colors: [string, string, string]
}

export const THEME_LIST: ThemeInfo[] = [
  { name: 'light-blue', label: '冰川蓝', desc: '浅色商务，蓝色主调', colors: ['#2563eb', '#f5f7fa', '#ffffff'] },
  { name: 'light-white', label: '晨曦白', desc: '纯白简洁，清爽明亮', colors: ['#2563eb', '#f5f5f5', '#ffffff'] },
  { name: 'dark-blue', label: '暗夜蓝', desc: '深色护眼，科技蓝调', colors: ['#3b82f6', '#0f172a', '#1e293b'] },
]

export const FONT_SIZE_OPTIONS = [12, 13, 14, 15, 16, 18, 20] as const
export type FontSize = typeof FONT_SIZE_OPTIONS[number]

export const FONT_WEIGHT_OPTIONS = [
  { value: 300, label: '细体' },
  { value: 400, label: '正常' },
  { value: 500, label: '中等' },
  { value: 700, label: '粗体' },
] as const
export type FontWeight = typeof FONT_WEIGHT_OPTIONS[number]['value']

export interface UserPreferences {
  theme: ThemeName
  font_size: FontSize
  font_weight: FontWeight
}

export const DEFAULT_USER_PREFERENCES: UserPreferences = {
  theme: 'light-blue',
  font_size: 14,
  font_weight: 400,
}

const LEGACY_STORAGE_KEYS = ['adcraft-theme', 'adcraft-font-size', 'adcraft-font-weight'] as const

function isThemeName(value: unknown): value is ThemeName {
  return typeof value === 'string' && THEME_LIST.some(theme => theme.name === value)
}

function isFontSize(value: unknown): value is FontSize {
  return typeof value === 'number' && FONT_SIZE_OPTIONS.includes(value as FontSize)
}

function isFontWeight(value: unknown): value is FontWeight {
  return typeof value === 'number'
    && FONT_WEIGHT_OPTIONS.some(option => option.value === value)
}

export function normalizeUserPreferences(value: Partial<UserPreferences> | null | undefined): UserPreferences {
  return {
    theme: isThemeName(value?.theme) ? value.theme : DEFAULT_USER_PREFERENCES.theme,
    font_size: isFontSize(value?.font_size) ? value.font_size : DEFAULT_USER_PREFERENCES.font_size,
    font_weight: isFontWeight(value?.font_weight) ? value.font_weight : DEFAULT_USER_PREFERENCES.font_weight,
  }
}

export function userPreferencesStorageKey(userId: string): string {
  return `adcraft-ui-preferences:${encodeURIComponent(userId)}`
}

export function readCachedUserPreferences(userId: string): UserPreferences | null {
  if (typeof localStorage === 'undefined') return null
  try {
    const raw = localStorage.getItem(userPreferencesStorageKey(userId))
    if (!raw) return null
    return normalizeUserPreferences(JSON.parse(raw) as Partial<UserPreferences>)
  } catch {
    return null
  }
}

export function cacheUserPreferences(userId: string, value: Partial<UserPreferences>): UserPreferences {
  const normalized = normalizeUserPreferences(value)
  if (typeof localStorage !== 'undefined') {
    try {
      localStorage.setItem(userPreferencesStorageKey(userId), JSON.stringify(normalized))
    } catch {
      // A full/private browser storage must not prevent the server save.
    }
  }
  return normalized
}

export function clearLegacyUserPreferenceStorage(): void {
  if (typeof localStorage === 'undefined') return
  for (const key of LEGACY_STORAGE_KEYS) {
    localStorage.removeItem(key)
  }
}
