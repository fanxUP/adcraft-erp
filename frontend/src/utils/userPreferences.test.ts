import { describe, expect, it } from 'vitest'
import {
  DEFAULT_USER_PREFERENCES,
  normalizeUserPreferences,
  userPreferencesStorageKey,
} from '@/config/userPreferences'

describe('per-user preference contract', () => {
  it('uses safe defaults for missing or invalid server values', () => {
    expect(normalizeUserPreferences(null)).toEqual(DEFAULT_USER_PREFERENCES)
    expect(normalizeUserPreferences({
      theme: 'url(javascript:alert(1))' as never,
      font_size: 99 as never,
      font_weight: 999 as never,
    })).toEqual(DEFAULT_USER_PREFERENCES)
  })

  it('preserves valid values and fills omitted values independently', () => {
    expect(normalizeUserPreferences({ theme: 'dark-blue' })).toEqual({
      theme: 'dark-blue',
      font_size: 14,
      font_weight: 400,
    })
    expect(normalizeUserPreferences({ font_size: 20, font_weight: 700 })).toEqual({
      theme: 'light-blue',
      font_size: 20,
      font_weight: 700,
    })
  })

  it('namespaces browser cache by authenticated user id', () => {
    expect(userPreferencesStorageKey('user-a')).toBe('adcraft-ui-preferences:user-a')
    expect(userPreferencesStorageKey('user-b')).not.toBe(userPreferencesStorageKey('user-a'))
  })
})
