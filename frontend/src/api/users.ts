import { get, post, put, del } from './index'
import { PaginatedData, UserResponse, SuccessResponse } from '@/types/api'

export function getUsers(params: { page?: number; page_size?: number; keyword?: string }) {
  return get<PaginatedData<UserResponse>>('/users/', { params })
}

export function createUser(data: Omit<Partial<UserResponse>, 'id' | 'created_at'>) {
  return post<UserResponse>('/users/', data)
}

export function getUser(id: string) {
  return get<UserResponse>(`/users/${id}`)
}

export function updateUser(id: string, data: Partial<Omit<UserResponse, 'id' | 'created_at'>>) {
  return put<UserResponse>(`/users/${id}`, data)
}

export function deleteUser(id: string) {
  return del<SuccessResponse>(`/users/${id}`)
}
