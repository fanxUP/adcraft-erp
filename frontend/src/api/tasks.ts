import api from './index'

export function getDesignTasks(params?: any) { return api.get('/design-tasks/', { params }) }
export function getDesignTask(id: string) { return api.get(`/design-tasks/${id}`) }
export function createDesignTask(data: any) { return api.post('/design-tasks/', data) }
export function updateDesignTask(id: string, data: any) { return api.put(`/design-tasks/${id}`, data) }
export function changeDesignTaskStatus(id: string, data: { to_status: string; reason?: string }) { return api.post(`/design-tasks/${id}/change-status`, data) }

export function getProductionTasks(params?: any) { return api.get('/production-tasks/', { params }) }
export function getProductionTask(id: string) { return api.get(`/production-tasks/${id}`) }
export function createProductionTask(data: any) { return api.post('/production-tasks/', data) }
export function updateProductionTask(id: string, data: any) { return api.put(`/production-tasks/${id}`, data) }
export function changeProductionTaskStatus(id: string, data: { to_status: string; reason?: string }) { return api.post(`/production-tasks/${id}/change-status`, data) }

export function getInstallationTasks(params?: any) { return api.get('/installation-tasks/', { params }) }
export function getInstallationTask(id: string) { return api.get(`/installation-tasks/${id}`) }
export function createInstallationTask(data: any) { return api.post('/installation-tasks/', data) }
export function updateInstallationTask(id: string, data: any) { return api.put(`/installation-tasks/${id}`, data) }
export function changeInstallationTaskStatus(id: string, data: { to_status: string; reason?: string }) { return api.post(`/installation-tasks/${id}/change-status`, data) }

export function uploadAttachment(relatedType: string, relatedId: string, file: File, category?: string) {
  const form = new FormData()
  form.append('file', file)
  return api.post('/attachments/upload', form, {
    params: { related_type: relatedType, related_id: relatedId, category },
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
export function deleteAttachment(id: string) { return api.delete(`/attachments/${id}`) }
