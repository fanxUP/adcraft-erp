import { get, post, del } from './index'
import { CreateBackupResponse, BackupListResponse, SuccessResponse } from '@/types/api'

export function createBackup() { return post<CreateBackupResponse>('/admin/backup/create') }

export function listBackups() { return get<BackupListResponse>('/admin/backup/list') }

export function restoreBackup(filename: string) { return post<SuccessResponse>('/admin/backup/restore', { filename }) }

export function deleteBackup(filename: string) { return del<SuccessResponse>(`/admin/backup/${filename}`) }
