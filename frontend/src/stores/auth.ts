import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { login as loginApi, getProfile } from '@/api/auth'
import type { UserProfile } from '@/types/api'
import router from '@/router'
import { useNotificationStore } from '@/stores/notification'
import { useChatStore } from '@/stores/chat'
import { useAppStore } from '@/stores/app'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>(localStorage.getItem('token') || '')
  const user = ref<UserProfile | null>(null)

  const isLoggedIn = computed(() => !!token.value)
  const roles = computed<string[]>(() => user.value?.roles || [])
  const permissions = computed<string[]>(() => user.value?.permissions || [])

  function hasRole(roleName: string): boolean {
    return roles.value.includes(roleName)
  }

  function hasAnyRole(roleNames: string[]): boolean {
    return roleNames.some(r => roles.value.includes(r))
  }

  function hasPermission(permissionCode: string): boolean {
    return permissions.value.includes(permissionCode)
  }

  const isSuperAdmin = computed(() => hasPermission('system:super_admin'))

  /**
   * Capability-first UI helper.  The backend remains authoritative; this
   * helper only keeps buttons, navigation and direct-route guards consistent.
   */
  function can(permissionCode: string): boolean {
    return isSuperAdmin.value || hasPermission(permissionCode)
  }

  function canAny(permissionCodes: string[]): boolean {
    return isSuperAdmin.value || permissionCodes.some(permission => hasPermission(permission))
  }

  function canAll(permissionCodes: string[]): boolean {
    return isSuperAdmin.value || permissionCodes.every(permission => hasPermission(permission))
  }

  // Compatibility name for existing views.  It now reflects the explicit
  // capability instead of the display role name.
  const isAdmin = computed(() => isSuperAdmin.value)

  async function login(username: string, password: string) {
    const data = await loginApi({ username, password })
    token.value = data.token
    localStorage.setItem('token', data.token)
    await fetchProfile()
    // Connect WebSocket for notifications
    const notificationStore = useNotificationStore()
    notificationStore.connectWebSocket(data.token)
    notificationStore.fetchUnreadCount()
    // Connect WebSocket for chat
    const chatStore = useChatStore()
    chatStore.connectWebSocket(data.token)
    chatStore.fetchConversations()
  }

  async function fetchProfile(quiet = false) {
    try {
      const appStore = useAppStore()
      const cachedUserId = tokenSubject(token.value)
      if (cachedUserId) {
        // Cache is only a visual warm start.  The profile response below is
        // always authoritative and replaces this value.
        appStore.restoreCachedUserPreferences(cachedUserId)
      }
      const profile = await getProfile()
      if (user.value?.id && user.value.id !== profile.id) {
        appStore.resetToDefaults()
      }
      user.value = profile
      appStore.applyUserPreferences(profile.id, profile.preferences)
      // Connect WebSocket for notifications after profile is loaded
      if (token.value) {
        const notificationStore = useNotificationStore()
        notificationStore.connectWebSocket(token.value)
        notificationStore.fetchUnreadCount()
        // Connect WebSocket for chat
        const chatStore = useChatStore()
        chatStore.connectWebSocket(token.value)
        chatStore.fetchConversations()
      }
    } catch {
      if (!quiet) {
        ElMessage.error('登录已过期，请重新登录')
      }
      logout()
    }
  }

  function logout() {
    // Disconnect notification WebSocket
    const notificationStore = useNotificationStore()
    notificationStore.disconnectWebSocket()
    // Disconnect chat WebSocket
    const chatStore = useChatStore()
    chatStore.disconnectWebSocket()

    token.value = ''
    user.value = null
    useAppStore().resetToDefaults()
    localStorage.removeItem('token')
    router.push('/login')
  }

  /** 强制改密成功后清除标记，解锁系统功能。 */
  function clearMustChangePassword() {
    if (user.value) {
      user.value.must_change_password = false
    }
  }

  function setUserPreferences(preferences: UserProfile['preferences']) {
    if (!user.value || !preferences) return
    const appStore = useAppStore()
    user.value.preferences = appStore.applyUserPreferences(user.value.id, preferences)
  }

  function tokenSubject(rawToken: string): string | null {
    try {
      const encodedPayload = rawToken.split('.')[1]
      if (!encodedPayload) return null
      const normalized = encodedPayload.replace(/-/g, '+').replace(/_/g, '/')
      const payload = JSON.parse(atob(normalized.padEnd(Math.ceil(normalized.length / 4) * 4, '='))) as { sub?: unknown }
      return typeof payload.sub === 'string' && payload.sub ? payload.sub : null
    } catch {
      return null
    }
  }

  return {
    token, user, isLoggedIn, roles, permissions, isAdmin, isSuperAdmin,
    hasRole, hasAnyRole, hasPermission, can, canAny, canAll,
    login, fetchProfile, logout, clearMustChangePassword, setUserPreferences,
  }
})
