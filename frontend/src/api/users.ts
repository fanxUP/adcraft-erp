import apiClient from './index'

export function getUsers(params: { page?: number; page_size?: number; keyword?: string }) {
  return apiClient.get('/users/', { params })
}

export function createUser(data: any) {
  return apiClient.post('/users/', data)
}

export function getUser(id: string) {
  return apiClient.get(`/users/${id}`)
}

export function updateUser(id: string, data: any) {
  return apiClient.put(`/users/${id}`, data)
}

export function deleteUser(id: string) {
  return apiClient.delete(`/users/${id}`)
}
