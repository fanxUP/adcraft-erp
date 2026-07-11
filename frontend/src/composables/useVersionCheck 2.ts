import { ref, onMounted, onUnmounted } from 'vue'

const VERSION_KEY = 'app_version'
const CHECK_INTERVAL = 2 * 60 * 1000 // 2 分钟轮询一次

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

/** 切换回该标签页时立即检查版本，避免用户长时间挂在后台漏掉更新 */
function onVisibilityChange() {
  if (document.visibilityState === 'visible') {
    checkVersion()
  }
}

export function useVersionCheck() {
  onMounted(() => {
    checkVersion()
    timer = setInterval(checkVersion, CHECK_INTERVAL)
    document.addEventListener('visibilitychange', onVisibilityChange)
  })

  onUnmounted(() => {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
    document.removeEventListener('visibilitychange', onVisibilityChange)
  })

  /** 用户点了「立即刷新」后刷新页面 */
  function refreshPage() {
    if (serverVersion.value) {
      localStorage.setItem(VERSION_KEY, serverVersion.value)
    }
    window.location.reload()
  }

  return {
    hasUpdate,
    refreshPage,
  }
}
