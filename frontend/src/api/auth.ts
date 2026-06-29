import apiClient from './index'

export function login(data: { username: string; password: string }) {
  return apiClient.post('/auth/login', data)
}

export function getProfile() {
  return apiClient.get('/auth/me')
}

export function changePassword(data: { old_password: string; new_password: string }) {
  return apiClient.post('/auth/change-password', data)
}
