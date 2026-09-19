import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'
import {
  ApiRequestError,
  formatApiError,
  isApiEnvelope,
  toApiRequestError,
} from './requestContract'

const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
})

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => {
    // Pass through non-JSON responses (e.g. blob downloads)
    if (response.data instanceof Blob) {
      return response
    }
    const data = response.data
    // New endpoints use the shared envelope. Legacy JSON payloads still pass
    // through so this migration does not require a destructive URL rewrite.
    if (!isApiEnvelope(data)) {
      return data
    }
    if (data.code !== 0) {
      return Promise.reject(toApiRequestError({ response: { ...response, data } }))
    }
    return data.data
  },
  (error) => {
    const normalized = toApiRequestError(error)
    if (error.response?.status === 401) {
      // 登录接口失败（密码错误等）：显示后端真实原因，不当作“会话过期”处理
      if (error.config?.url?.includes('/auth/login')) {
        ElMessage.error(formatApiError(normalized, '工号或密码错误'))
        return Promise.reject(normalized)
      }
      ElMessage.error('登录已过期，请重新登录')
      useAuthStore().logout()
      router.push('/login')
    } else if (normalized.status === 403 && normalized.code === 40300) {
      // 强制改密场景：不弹窗刷屏，由全局 ForceChangePasswordDialog 统一引导修改密码
      return Promise.reject(normalized)
    } else {
      ElMessage.error(formatApiError(normalized, '网络错误'))
    }
    return Promise.reject(normalized)
  },
)

/**
 * Typed request helpers.
 * The response interceptor unwraps `response.data.data` so the return type
 * is the inner payload, not AxiosResponse.  These wrappers tell TypeScript
 * that, eliminating "Property 'items' does not exist on type 'AxiosResponse'"
 * errors in every view.
 */
import type { AxiosRequestConfig } from 'axios'

export async function get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  return apiClient.get(url, config) as unknown as Promise<T>
}
export async function post<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
  return apiClient.post(url, data, config) as unknown as Promise<T>
}
export async function put<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
  return apiClient.put(url, data, config) as unknown as Promise<T>
}
export async function del<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  return apiClient.delete(url, config) as unknown as Promise<T>
}
export async function patch<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
  return apiClient.patch(url, data, config) as unknown as Promise<T>
}

/**
 * Raw axios client – only needed when the interceptor's unwrapping is
 * undesirable (e.g. blob downloads, progress events).
 */
export { apiClient, ApiRequestError }

// Convenience default export - supports `import api from '@/api'`
const api = { get, post, put, del, patch, apiClient }
export default api
