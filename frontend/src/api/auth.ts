import { post, get, patch } from './index'
import type { LoginResponse, UserPreferences, UserProfile, SuccessResponse } from '@/types/api'

export function login(data: { username: string; password: string }) {
  return post<LoginResponse>('/auth/login', data)
}

export function getProfile() {
  return get<UserProfile>('/auth/me')
}

export function changePassword(data: { old_password: string; new_password: string }) {
  return post<SuccessResponse>('/auth/change-password', data)
}

export function updateUserPreferences(data: Partial<UserPreferences>) {
  return patch<UserPreferences>('/auth/preferences', data)
}
