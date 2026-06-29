import apiClient from './index'

export function getProducts(params: { page?: number; page_size?: number; keyword?: string; category_id?: string }) {
  return apiClient.get('/products/', { params })
}

export function getProduct(id: string) {
  return apiClient.get(`/products/${id}`)
}

export function createProduct(data: any) {
  return apiClient.post('/products/', data)
}

export function updateProduct(id: string, data: any) {
  return apiClient.put(`/products/${id}`, data)
}

export function deleteProduct(id: string) {
  return apiClient.delete(`/products/${id}`)
}

// Categories
export function getCategories() {
  return apiClient.get('/product-categories/')
}

export function createCategory(data: any) {
  return apiClient.post('/product-categories/', data)
}

export function deleteCategory(id: string) {
  return apiClient.delete(`/product-categories/${id}`)
}

// Materials
export function getMaterials(params: { page?: number; page_size?: number; keyword?: string }) {
  return apiClient.get('/materials/', { params })
}

export function getMaterial(id: string) {
  return apiClient.get(`/materials/${id}`)
}

export function createMaterial(data: any) {
  return apiClient.post('/materials/', data)
}

export function updateMaterial(id: string, data: any) {
  return apiClient.put(`/materials/${id}`, data)
}

export function deleteMaterial(id: string) {
  return apiClient.delete(`/materials/${id}`)
}

// Processes
export function getProcesses(params: { page?: number; page_size?: number; keyword?: string }) {
  return apiClient.get('/processes/', { params })
}

export function getProcess(id: string) {
  return apiClient.get(`/processes/${id}`)
}

export function createProcess(data: any) {
  return apiClient.post('/processes/', data)
}

export function updateProcess(id: string, data: any) {
  return apiClient.put(`/processes/${id}`, data)
}

export function deleteProcess(id: string) {
  return apiClient.delete(`/processes/${id}`)
}
