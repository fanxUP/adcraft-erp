import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { get } from '@/api'
import type { BrandingMetadata } from '@/api/admin'

const DEFAULT_APP_NAME = 'AdCraft ERP'
const APP_DESCRIPTION = '广告制作安装工程管理系统'

function safeLogoUrl(value: string | null | undefined): string | null {
  if (!value) return null
  // The public API currently returns a same-origin, versioned URL.  Keep the
  // allow-list here so a malformed or future upstream value cannot turn into
  // an arbitrary image request from the branding surface.
  return value.startsWith('/api/v1/public/branding/logo') ? value : null
}

export const useBrandingStore = defineStore('branding', () => {
  const appName = ref(DEFAULT_APP_NAME)
  const logoUrl = ref<string | null>(null)
  const logoVersion = ref(0)
  const hasCustomLogo = ref(false)
  const loaded = ref(false)
  let pending: Promise<void> | null = null

  const fallbackMark = computed(() => appName.value.trim().charAt(0).toUpperCase() || 'A')

  function updateDocumentHead() {
    if (typeof document === 'undefined') return
    document.title = `${appName.value} - ${APP_DESCRIPTION}`

    let favicon = document.querySelector<HTMLLinkElement>('link[rel~="icon"]')
    if (!favicon) {
      favicon = document.createElement('link')
      favicon.rel = 'icon'
      document.head.appendChild(favicon)
    }
    favicon.href = logoUrl.value || '/favicon.svg'
    if (logoUrl.value) favicon.removeAttribute('type')
    else favicon.type = 'image/svg+xml'
  }

  function applyBranding(data: Partial<BrandingMetadata>) {
    appName.value = data.app_name?.trim() || DEFAULT_APP_NAME
    hasCustomLogo.value = Boolean(data.has_custom_logo && safeLogoUrl(data.logo_url))
    logoUrl.value = hasCustomLogo.value ? safeLogoUrl(data.logo_url) : null
    logoVersion.value = Number(data.logo_version || 0)
    updateDocumentHead()
  }

  function applyFallback() {
    applyBranding({
      app_name: DEFAULT_APP_NAME,
      logo_url: null,
      logo_version: 0,
      has_custom_logo: false,
    })
  }

  async function fetchBranding(force = false) {
    if (pending && !force) return pending
    const request = get<BrandingMetadata>('/public/branding', { timeout: 5000 })
      .then(data => {
        applyBranding(data)
        loaded.value = true
      })
      .catch(() => {
        // Branding is presentation metadata.  A transient failure must not
        // prevent login or blank the existing brand after a successful load.
        if (!loaded.value) applyFallback()
      })
    pending = request
    request.finally(() => {
      if (pending === request) pending = null
    })
    return request
  }

  function setBranding(data: BrandingMetadata) {
    applyBranding(data)
    loaded.value = true
  }

  return {
    appName,
    logoUrl,
    logoVersion,
    hasCustomLogo,
    fallbackMark,
    loaded,
    fetchBranding,
    setBranding,
  }
})
