import { get, post, put, del, apiClient } from './index'
import { SuccessResponse } from '@/types/api'

// ── Roles ──

export interface RoleItem {
  id: string
  name: string
  description?: string
  permissions: PermissionItem[]
}

export interface PermissionItem {
  id: string
  code: string
  name: string
  description?: string
}

export function getRoles() {
  return get<RoleItem[]>('/admin/roles')
}

export function createRole(data: { name: string; description?: string }) {
  return post<RoleItem>('/admin/roles', data)
}

export function updateRole(id: string, data: { name?: string; description?: string }) {
  return put<RoleItem>(`/admin/roles/${id}`, data)
}

export function deleteRole(id: string) {
  return del<SuccessResponse>(`/admin/roles/${id}`)
}

export function setRolePermissions(id: string, permissionIds: string[]) {
  return put<RoleItem>(`/admin/roles/${id}/permissions`, { permission_ids: permissionIds })
}

// ── Permissions ──

export function getPermissions() {
  return get<PermissionItem[]>('/admin/permissions')
}

// ── System Settings ──

export interface SystemSettings {
  APP_NAME: string
  JWT_EXPIRE_MINUTES: number
  UPLOAD_STORAGE: string
  LOCAL_UPLOAD_DIR: string
  AI_ENABLED: boolean
  AI_PROVIDER: string
  AI_MODEL: string
  AI_API_KEY: string
  AI_API_BASE_URL: string
}

export function getSystemSettings() {
  return get<SystemSettings>('/admin/settings')
}

export function forceRelogin() {
  return apiClient.post('/users/bump-token-version')
}

export function updateSystemSettings(data: Record<string, unknown>) {
  return put<{ updated: Record<string, string>; message: string }>('/admin/settings', data)
}
