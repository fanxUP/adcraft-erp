import { get, post, del, apiClient } from './index'
import { CreateBackupResponse, BackupListResponse, SuccessResponse, ImportBackupResponse } from '@/types/api'

export function createBackup() { return post<CreateBackupResponse>('/admin/backup/create') }

export function listBackups() { return get<BackupListResponse>('/admin/backup/list') }

export function restoreBackup(filename: string) { return post<SuccessResponse>('/admin/backup/restore', { filename }, { timeout: 300000 }) }

export function deleteBackup(filename: string) { return del<SuccessResponse>(`/admin/backup/${filename}`) }

/** Download a backup file to the browser. Triggers a file save dialog. */
export async function exportBackup(filename: string) {
  const resp = await apiClient.get(`/admin/backup/export/${encodeURIComponent(filename)}`, {
    responseType: 'blob',
  })
  // Create a temporary link to trigger download
  const url = URL.createObjectURL(resp.data)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

/** Upload a .tar.gz backup file to the server. */
export function importBackup(file: File) {
  const form = new FormData()
  form.append('file', file)
  return post<ImportBackupResponse>('/admin/backup/import', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300000,
  })
}
