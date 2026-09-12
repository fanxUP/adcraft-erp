import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { UserPreferences } from '@/types/api'
import {
  cacheUserPreferences,
  clearLegacyUserPreferenceStorage,
  DEFAULT_USER_PREFERENCES,
  normalizeUserPreferences,
  readCachedUserPreferences,
  type FontSize,
  type FontWeight,
  type ThemeName,
} from '@/config/userPreferences'

export {
  THEME_LIST,
  FONT_SIZE_OPTIONS,
  FONT_WEIGHT_OPTIONS,
  type ThemeName,
} from '@/config/userPreferences'
export type { ThemeInfo } from '@/config/userPreferences'

export const useAppStore = defineStore('app', () => {
  const sidebarCollapsed = ref(false)
  // Start from a safe account-neutral state.  The authenticated profile then
  // replaces it with the server-owned preferences for the current user.
  const theme = ref<ThemeName>(DEFAULT_USER_PREFERENCES.theme)
  const fontSize = ref<FontSize>(DEFAULT_USER_PREFERENCES.font_size)
  const fontWeight = ref<FontWeight>(DEFAULT_USER_PREFERENCES.font_weight)

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function setTheme(name: ThemeName) {
    theme.value = name
    applyThemeDom()
  }

  function setFontSize(px: FontSize) {
    fontSize.value = px
    applyTypographyDom()
  }

  function setFontWeight(weight: FontWeight) {
    fontWeight.value = weight
    applyTypographyDom()
  }

  function applyThemeDom() {
    if (typeof document === 'undefined') return
    document.documentElement.dataset.theme = theme.value
    document.documentElement.classList.toggle('dark', theme.value.startsWith('dark'))
  }

  function applyTypographyDom() {
    if (typeof document === 'undefined') return
    document.documentElement.style.setProperty('--ad-font-size-base', `${fontSize.value}px`)
    document.documentElement.style.setProperty('--ad-font-weight-base', String(fontWeight.value))
  }

  function initTheme() {
    applyThemeDom()
    applyTypographyDom()
  }

  function applyUserPreferences(userId: string, value: Partial<UserPreferences> | null | undefined): UserPreferences {
    const normalized = normalizeUserPreferences(value)
    theme.value = normalized.theme
    fontSize.value = normalized.font_size
    fontWeight.value = normalized.font_weight
    initTheme()
    cacheUserPreferences(userId, normalized)
    clearLegacyUserPreferenceStorage()
    return normalized
  }

  function restoreCachedUserPreferences(userId: string): UserPreferences | null {
    const cached = readCachedUserPreferences(userId)
    if (!cached) return null
    theme.value = cached.theme
    fontSize.value = cached.font_size
    fontWeight.value = cached.font_weight
    initTheme()
    return cached
  }

  function resetToDefaults() {
    theme.value = DEFAULT_USER_PREFERENCES.theme
    fontSize.value = DEFAULT_USER_PREFERENCES.font_size
    fontWeight.value = DEFAULT_USER_PREFERENCES.font_weight
    clearLegacyUserPreferenceStorage()
    initTheme()
  }

  return {
    sidebarCollapsed,
    theme,
    fontSize,
    fontWeight,
    toggleSidebar,
    setTheme,
    setFontSize,
    setFontWeight,
    initTheme,
    applyUserPreferences,
    restoreCachedUserPreferences,
    resetToDefaults,
  }
})
