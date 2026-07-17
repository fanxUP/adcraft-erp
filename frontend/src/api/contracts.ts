import { get, post, put, del } from './index'
import type { PaginatedData, ContractListResponse, ContractDetailResponse, ContractAvailableResources, SuccessResponse } from '@/types/api'

export function getContracts(params: {
  page?: number
  page_size?: number
  status?: string
  keyword?: string
  customer_id?: string
}) {
  return get<PaginatedData<ContractListResponse>>('/contracts/', { params })
}

export function getContract(id: string) {
  return get<ContractDetailResponse>(`/contracts/${id}`)
}

export function createContract(data: Record<string, unknown>) {
  return post<ContractDetailResponse>('/contracts/', data)
}

export function updateContract(id: string, data: Record<string, unknown>) {
  return put<ContractDetailResponse>(`/contracts/${id}`, data)
}

export function deleteContract(id: string) {
  return del<SuccessResponse>(`/contracts/${id}`)
}

export function changeContractStatus(id: string, data: { to_status: string; reason?: string }) {
  return post<ContractDetailResponse>(`/contracts/${id}/status`, data)
}

export function uploadContractAttachment(contractId: string, file: File) {
  const form = new FormData()
  form.append('file', file)
  return post<ContractDetailResponse>(`/contracts/${contractId}/upload`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function deleteContractAttachment(contractId: string) {
  return del<SuccessResponse>(`/contracts/${contractId}/attachment`)
}

export function getContractAttachmentUrl(contractId: string) {
  return `/api/v1/contracts/${contractId}/attachment`
}

export function getContractAvailableResources(contractId?: string) {
  const params: Record<string, string> = {}
  if (contractId) params.contract_id = contractId
  return get<ContractAvailableResources>('/contracts/available-resources', { params })
}
