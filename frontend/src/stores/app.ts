import { defineStore } from 'pinia'
import { ref } from 'vue'

export type ThemeName = 'light-blue' | 'light-white' | 'dark-blue'

export interface ThemeInfo {
  name: ThemeName
  label: string
  desc: string
  colors: [string, string, string] // [accent, bg, card]
}

export const THEME_LIST: ThemeInfo[] = [
  { name: 'light-blue',   label: '冰川蓝',   desc: '浅色商务，蓝色主调',     colors: ['#2563eb', '#f5f7fa', '#ffffff'] },
  { name: 'light-white',  label: '晨曦白',   desc: '纯白简洁，清爽明亮',     colors: ['#2563eb', '#f5f5f5', '#ffffff'] },
  { name: 'dark-blue',    label: '暗夜蓝',   desc: '深色护眼，科技蓝调',     colors: ['#3b82f6', '#0f172a', '#1e293b'] },
]

export const FONT_SIZE_OPTIONS = [12, 13, 14, 15, 16, 18, 20] as const
export const FONT_WEIGHT_OPTIONS = [
  { value: 300, label: '细体' },
  { value: 400, label: '正常' },
  { value: 500, label: '中等' },
  { value: 700, label: '粗体' },
] as const

export const useAppStore = defineStore('app', () => {
  const sidebarCollapsed = ref(false)
  const storedTheme = localStorage.getItem('adcraft-theme')
  const theme = ref<ThemeName>(THEME_LIST.some((t) => t.name === storedTheme) ? (storedTheme as ThemeName) : 'light-blue')
  const fontSize = ref(Number(localStorage.getItem('adcraft-font-size')) || 14)
  const fontWeight = ref(Number(localStorage.getItem('adcraft-font-weight')) || 400)

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function setTheme(name: ThemeName) {
    theme.value = name
    document.documentElement.dataset.theme = name
    document.documentElement.classList.toggle('dark', name.startsWith('dark'))
    localStorage.setItem('adcraft-theme', name)
  }

  function setFontSize(px: number) {
    fontSize.value = px
    document.documentElement.style.setProperty('--ad-font-size-base', `${px}px`)
    localStorage.setItem('adcraft-font-size', String(px))
  }

  function setFontWeight(weight: number) {
    fontWeight.value = weight
    document.documentElement.style.setProperty('--ad-font-weight-base', String(weight))
    localStorage.setItem('adcraft-font-weight', String(weight))
  }

  function initTheme() {
    document.documentElement.dataset.theme = theme.value
    document.documentElement.classList.toggle('dark', theme.value.startsWith('dark'))
    document.documentElement.style.setProperty('--ad-font-size-base', `${fontSize.value}px`)
    document.documentElement.style.setProperty('--ad-font-weight-base', String(fontWeight.value))
  }

  return { sidebarCollapsed, theme, fontSize, fontWeight, toggleSidebar, setTheme, setFontSize, setFontWeight, initTheme }
})
