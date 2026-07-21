import { get, post, put, del } from './index'
import type {
  PaginatedData,
  ContractListResponse,
  FrameworkContractProjectDetailResponse,
  FrameworkContractAvailableResources,
  SuccessResponse,
} from '@/types/api'

// ── 框架合同列表（委托 contracts API，带 contract_type 过滤） ──

export function getFrameworkContracts(params: {
  page?: number
  page_size?: number
  status?: string
  keyword?: string
  customer_id?: string
}) {
  return get<PaginatedData<ContractListResponse>>('/contracts/', {
    params: { ...params, contract_type: '框架合同' },
  })
}

// 复用 contracts.ts 的 getContract / updateContract / deleteContract / changeContractStatus 等

// ── 框架合同项目 CRUD ──

export function getContractProjects(contractId: string, params?: { page?: number; page_size?: number }) {
  return get<PaginatedData<FrameworkContractProjectDetailResponse>>(
    `/framework-contracts/${contractId}/projects`,
    { params }
  )
}

export function getContractProject(projectId: string) {
  return get<FrameworkContractProjectDetailResponse>(`/framework-contracts/projects/${projectId}`)
}

export function createContractProject(contractId: string, data: Record<string, unknown>) {
  return post<FrameworkContractProjectDetailResponse>(`/framework-contracts/${contractId}/projects`, data)
}

export function updateContractProject(projectId: string, data: Record<string, unknown>) {
  return put<FrameworkContractProjectDetailResponse>(`/framework-contracts/projects/${projectId}`, data)
}

export function deleteContractProject(projectId: string) {
  return del<SuccessResponse>(`/framework-contracts/projects/${projectId}`)
}

// ── 项目附件 ──

export function uploadContractProjectAttachment(projectId: string, file: File) {
  const form = new FormData()
  form.append('file', file)
  return post<FrameworkContractProjectDetailResponse>(
    `/framework-contracts/projects/${projectId}/upload`,
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  )
}

export function deleteContractProjectAttachment(projectId: string) {
  return del<SuccessResponse>(`/framework-contracts/projects/${projectId}/attachment`)
}

export function getContractProjectAttachmentUrl(projectId: string) {
  return `/api/v1/framework-contracts/projects/${projectId}/attachment`
}

// ── 可用资源 ──

export function getAvailableResources(customerId: string, contractId?: string) {
  const params: Record<string, string> = { customer_id: customerId }
  if (contractId) params.contract_id = contractId
  return get<FrameworkContractAvailableResources>('/framework-contracts/available-projects', { params })
}
