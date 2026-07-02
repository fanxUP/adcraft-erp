import { defineStore } from 'pinia'
import { ref } from 'vue'

export type ThemeName =
  | 'dark-red' | 'dark-blue' | 'dark-purple' | 'dark-green' | 'dark-orange'
  | 'light-white' | 'light-blue' | 'china-red' | 'cyber'

export interface ThemeInfo {
  name: ThemeName
  label: string
  desc: string
  colors: [string, string, string] // [accent, bg, card]
}

export const THEME_LIST: ThemeInfo[] = [
  { name: 'dark-red',     label: '暗夜红',   desc: '深邃暗色，红色主调',     colors: ['#e63946', '#1a1a2e', '#1e1e30'] },
  { name: 'dark-blue',    label: '暗夜蓝',   desc: '科技蓝调，专业沉稳',     colors: ['#3b82f6', '#0f172a', '#1e293b'] },
  { name: 'dark-purple',  label: '暗夜紫',   desc: '紫色未来感',             colors: ['#a855f7', '#1a1025', '#231a30'] },
  { name: 'dark-green',   label: '暗夜绿',   desc: '自然绿调，清新护眼',     colors: ['#22c55e', '#0f1a12', '#162118'] },
  { name: 'dark-orange',  label: '暗夜橙',   desc: '暖橙色调，活力十足',     colors: ['#f97316', '#1a1510', '#251e15'] },
  { name: 'light-white',  label: '晨曦白',   desc: '经典亮色，简洁明亮',     colors: ['#e63946', '#f5f5f5', '#ffffff'] },
  { name: 'light-blue',   label: '冰川蓝',   desc: '清新亮蓝，通透舒适',     colors: ['#2563eb', '#f0f7ff', '#ffffff'] },
  { name: 'china-red',    label: '中国红',   desc: '红木古典风',             colors: ['#d4380d', '#1a0a08', '#2a1510'] },
  { name: 'cyber',        label: '赛博朋克', desc: '霓虹科技感',             colors: ['#00ffcc', '#0a0a1a', '#12122a'] },
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
  const theme = ref<ThemeName>((localStorage.getItem('adcraft-theme') as ThemeName) || 'light-blue')
  const fontSize = ref(Number(localStorage.getItem('adcraft-font-size')) || 14)
  const fontWeight = ref(Number(localStorage.getItem('adcraft-font-weight')) || 400)

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function setTheme(name: ThemeName) {
    theme.value = name
    document.documentElement.dataset.theme = name
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
    document.documentElement.style.setProperty('--ad-font-size-base', `${fontSize.value}px`)
    document.documentElement.style.setProperty('--ad-font-weight-base', String(fontWeight.value))
  }

  return { sidebarCollapsed, theme, fontSize, fontWeight, toggleSidebar, setTheme, setFontSize, setFontWeight, initTheme }
})
