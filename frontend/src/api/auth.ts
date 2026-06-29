import { post, get } from './index'
import { LoginResponse, UserProfile, SuccessResponse } from '@/types/api'

export function login(data: { username: string; password: string }) {
  return post<LoginResponse>('/auth/login', data)
}

export function getProfile() {
  return get<UserProfile>('/auth/me')
}

export function changePassword(data: { old_password: string; new_password: string }) {
  return post<SuccessResponse>('/auth/change-password', data)
}
