import { get, post, put, del } from './index'
import type { SuccessResponse } from '@/types/api'

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
  module: string
  resource: string
  action: string
  kind: 'module' | 'action' | 'field' | string
  sensitivity: 'normal' | 'price' | 'financial' | 'external' | 'security' | string
  status: 'active' | 'deprecated' | string
  sort_order: number
  requires: string[]
}

export interface PermissionPackItem {
  code: string
  name: string
  description: string
  permissions: string[]
}

export interface RolePermissionIssue {
  kind: string
  code: string
  message: string
  permissions: string[]
}

export interface RolePermissionPreview {
  role_id: string
  valid: boolean
  issues: RolePermissionIssue[]
  added_permissions: string[]
  removed_permissions: string[]
  affected_user_count: number
  permissions: PermissionItem[]
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

export function previewRolePermissions(id: string, permissionIds: string[]) {
  return post<RolePermissionPreview>(`/admin/roles/${id}/permissions/preview`, { permission_ids: permissionIds })
}

// ── Permissions ──

export function getPermissions() {
  return get<PermissionItem[]>('/admin/permissions')
}

export function getPermissionPacks() {
  return get<PermissionPackItem[]>('/admin/permission-packs')
}

// ── System Settings ──

export interface SystemSettings {
  APP_NAME: string
  COMPANY_NAME: string
  COMPANY_PHONE: string
  JWT_EXPIRE_MINUTES: number
  UPLOAD_STORAGE: string
  LOCAL_UPLOAD_DIR: string
  AI_ENABLED: boolean
  AI_PROVIDER: string
  AI_MODEL: string
  AI_API_KEY: string
  AI_API_BASE_URL: string
  BRANDING?: BrandingMetadata
}

export interface BrandingMetadata {
  app_name: string
  logo_url: string | null
  logo_version: number
  has_custom_logo: boolean
  logo_filename?: string | null
  logo_content_type?: string | null
  logo_size?: number | null
}

export function getSystemSettings() {
  return get<SystemSettings>('/admin/settings')
}

export function forceRelogin() {
  return post<{ message: string }>('/admin/force-relogin')
}

export function updateSystemSettings(data: Record<string, unknown>) {
  return put<{ updated: Record<string, string>; message: string }>('/admin/settings', data)
}

export function uploadSystemLogo(file: File) {
  const form = new FormData()
  form.append('file', file)
  return post<{ branding: BrandingMetadata; message: string }>('/admin/settings/logo', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function restoreDefaultSystemLogo() {
  return del<{ branding: BrandingMetadata; message: string }>('/admin/settings/logo')
}
