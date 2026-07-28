import { get, post, put, del } from './index'
import type { PaginatedData, UserResponse, SuccessResponse } from '@/types/api'

export interface UserCreateInput {
  username: string
  password: string
  real_name?: string | null
  phone?: string | null
  email?: string | null
  role_ids?: string[]
}

export interface UserUpdateInput {
  real_name?: string | null
  phone?: string | null
  email?: string | null
  is_active?: boolean
  role_ids?: string[]
}

export function getUsers(params: { page?: number; page_size?: number; keyword?: string }) {
  return get<PaginatedData<UserResponse>>('/users/', { params })
}

export function createUser(data: UserCreateInput) {
  return post<UserResponse>('/users/', data)
}

export function getUser(id: string) {
  return get<UserResponse>(`/users/${id}`)
}

export function updateUser(id: string, data: UserUpdateInput) {
  return put<UserResponse>(`/users/${id}`, data)
}

export function deleteUser(id: string) {
  return del<SuccessResponse>(`/users/${id}`)
}

export function resetPassword(id: string, new_password: string) {
  return post<SuccessResponse>(`/users/${id}/reset-password`, { new_password })
}
