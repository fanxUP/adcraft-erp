import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { login as loginApi, getProfile } from '@/api/auth'
import type { UserResponse } from '@/types/api'
import router from '@/router'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>(localStorage.getItem('token') || '')
  const user = ref<UserResponse | null>(null)

  const isLoggedIn = computed(() => !!token.value)
  const roles = computed<string[]>(() => user.value?.roles || [])

  function hasRole(roleName: string): boolean {
    return roles.value.includes(roleName)
  }

  function hasAnyRole(roleNames: string[]): boolean {
    return roleNames.some(r => roles.value.includes(r))
  }

  /** Whether the user is the admin (has the admin role). */
  const isAdmin = computed(() => hasRole('admin'))

  async function login(username: string, password: string) {
    const data = await loginApi({ username, password })
    token.value = data.token
    localStorage.setItem('token', data.token)
    await fetchProfile()
  }

  async function fetchProfile(quiet = false) {
    try {
      user.value = await getProfile()
    } catch {
      if (!quiet) {
        ElMessage.error('登录已过期，请重新登录')
      }
      logout()
    }
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    router.push('/login')
  }

  return {
    token, user, isLoggedIn, roles, isAdmin,
    hasRole, hasAnyRole,
    login, fetchProfile, logout,
  }
})
