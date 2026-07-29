import { get, post, put, del } from './index'
import { PaginatedData, ProductResponse, ProductCategoryResponse, MaterialResponse, ProcessResponse, SuccessResponse, ImportResponse } from '@/types/api'

export function getProducts(params: { page?: number; page_size?: number; keyword?: string; category_id?: string }) {
  return get<PaginatedData<ProductResponse>>('/products/', { params })
}

export function getProduct(id: string) {
  return get<ProductResponse>(`/products/${id}`)
}

export function createProduct(data: Omit<Partial<ProductResponse>, 'id' | 'created_at'>) {
  return post<ProductResponse>('/products/', data)
}

export function updateProduct(id: string, data: Partial<Omit<ProductResponse, 'id' | 'created_at'>>) {
  return put<ProductResponse>(`/products/${id}`, data)
}

export function deleteProduct(id: string) {
  return del<SuccessResponse>(`/products/${id}`)
}

export function importProducts(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return post<ImportResponse>('/products/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// Categories
export function getCategories() {
  return get<ProductCategoryResponse[]>('/product-categories/')
}

export function createCategory(data: Omit<Partial<ProductCategoryResponse>, 'id'>) {
  return post<ProductCategoryResponse>('/product-categories/', data)
}

export function deleteCategory(id: string) {
  return del<SuccessResponse>(`/product-categories/${id}`)
}

// Materials
export function getMaterials(params: { page?: number; page_size?: number; keyword?: string }) {
  return get<PaginatedData<MaterialResponse>>('/materials/', { params })
}

export function getMaterial(id: string) {
  return get<MaterialResponse>(`/materials/${id}`)
}

export function createMaterial(data: Omit<Partial<MaterialResponse>, 'id' | 'created_at'>) {
  return post<MaterialResponse>('/materials/', data)
}

export function updateMaterial(id: string, data: Partial<Omit<MaterialResponse, 'id' | 'created_at'>>) {
  return put<MaterialResponse>(`/materials/${id}`, data)
}

export function deleteMaterial(id: string) {
  return del<SuccessResponse>(`/materials/${id}`)
}

export function importMaterials(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return post<ImportResponse>('/materials/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// Processes
export function getProcesses(params: { page?: number; page_size?: number; keyword?: string }) {
  return get<PaginatedData<ProcessResponse>>('/processes/', { params })
}

export function getProcess(id: string) {
  return get<ProcessResponse>(`/processes/${id}`)
}

export function createProcess(data: Omit<Partial<ProcessResponse>, 'id' | 'created_at'>) {
  return post<ProcessResponse>('/processes/', data)
}

export function updateProcess(id: string, data: Partial<Omit<ProcessResponse, 'id' | 'created_at'>>) {
  return put<ProcessResponse>(`/processes/${id}`, data)
}

export function deleteProcess(id: string) {
  return del<SuccessResponse>(`/processes/${id}`)
}
