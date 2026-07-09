import { ref, onMounted, onUnmounted } from 'vue'

const VERSION_KEY = 'app_version'
const CHECK_INTERVAL = 5 * 60 * 1000 // 5 分钟

const hasUpdate = ref(false)
const serverVersion = ref('')

let timer: ReturnType<typeof setInterval> | null = null

async function checkVersion() {
  try {
    const res = await fetch(`/version.json?t=${Date.now()}`)
    if (!res.ok) return
    const data = await res.json()
    const currentVersion = data.version || ''
    if (!currentVersion) return

    const storedVersion = localStorage.getItem(VERSION_KEY)

    // 首次运行，存下版本号
    if (!storedVersion) {
      localStorage.setItem(VERSION_KEY, currentVersion)
      return
    }

    // 版本变了 → 提示刷新
    if (storedVersion !== currentVersion) {
      serverVersion.value = currentVersion
      hasUpdate.value = true
    }
  } catch {
    // 网络错误静默忽略
  }
}

export function useVersionCheck() {
  onMounted(() => {
    checkVersion()
    timer = setInterval(checkVersion, CHECK_INTERVAL)
  })

  onUnmounted(() => {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  })

  function dismissUpdate() {
    // 用户点了刷新或关闭，更新本地版本号，不再提示
    if (serverVersion.value) {
      localStorage.setItem(VERSION_KEY, serverVersion.value)
    }
    hasUpdate.value = false
  }

  function refreshPage() {
    localStorage.setItem(VERSION_KEY, serverVersion.value)
    window.location.reload()
  }

  return {
    hasUpdate,
    dismissUpdate,
    refreshPage,
  }
}
