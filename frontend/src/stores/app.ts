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

export const useAppStore = defineStore('app', () => {
  const sidebarCollapsed = ref(false)
  const theme = ref<ThemeName>((localStorage.getItem('adcraft-theme') as ThemeName) || 'light-blue')

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function setTheme(name: ThemeName) {
    theme.value = name
    document.documentElement.dataset.theme = name
    localStorage.setItem('adcraft-theme', name)
  }

  function initTheme() {
    document.documentElement.dataset.theme = theme.value
  }

  return { sidebarCollapsed, theme, toggleSidebar, setTheme, initTheme }
})
