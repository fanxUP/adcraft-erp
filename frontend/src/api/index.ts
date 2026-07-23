import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'

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
    if (data.code !== 0) {
      ElMessage.error(data.message || '请求失败')
      return Promise.reject(new Error(data.message))
    }
    return data.data
  },
  (error) => {
    if (error.response?.status === 401) {
      ElMessage.error('登录已过期，请重新登录')
      useAuthStore().logout()
      router.push('/login')
    } else if (error.response?.status === 422 && Array.isArray(error.response?.data?.detail)) {
      const messages = error.response.data.detail.map((d: { msg: string }) => d.msg).join('; ')
      ElMessage.error(messages || '请求参数错误')
    } else {
      ElMessage.error(error.response?.data?.message || '网络错误')
    }
    return Promise.reject(error)
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
export { apiClient }
