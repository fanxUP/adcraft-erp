/**
 * usePrint — 可复用 A4 打印 composable
 *
 * 用法（模板内 ref）：
 * ```vue
 * <div ref="printContainerRef" class="print-a4-wrapper">...</div>
 * <el-button @click="handlePrint">打印</el-button>
 * ```
 *
 * 用法（选择器 — 适用于 el-dialog teleport 场景）：
 * ```vue
 * <el-dialog>
 *   <div class="print-area">...</div>
 *   <el-button @click="() => handlePrintBySelector('.print-area')">打印</el-button>
 * </el-dialog>
 * ```
 *
 * 功能：
 * - 自动提取打印内容到独立容器（不受 UI 框架 teleport 影响）
 * - 全局 print.scss 保证 A4 宽度、等宽对齐、无内容缺失
 * - 打印完成后自动清理临时 DOM
 */

import { ref, type Ref } from 'vue'

interface UsePrintOptions {
  /** 打印标题（选填） */
  title?: string
}

export function usePrint(options: UsePrintOptions = {}) {
  const printContainerRef: Ref<HTMLElement | null> = ref(null)

  /**
   * 打印：使用 ref 指向的容器内容
   */
  function handlePrint() {
    const el = printContainerRef.value
    if (!el) return
    doPrint(el.innerHTML, options.title)
  }

  /**
   * 打印：使用 CSS 选择器查找容器
   * 适用于 el-dialog teleport 场景
   */
  function handlePrintBySelector(selector: string) {
    const el = document.querySelector(selector)
    if (!el) return
    doPrint(el.innerHTML, options.title)
  }

  return {
    printContainerRef,
    handlePrint,
    handlePrintBySelector,
  }
}

/**
 * 核心打印逻辑
 */
function doPrint(html: string, title?: string) {
  // 创建独立打印容器
  const wrapper = document.createElement('div')
  wrapper.id = '__print_a4_wrapper__'
  wrapper.className = 'print-a4-wrapper'
  wrapper.innerHTML = html

  // 顶部加标题（如果配置了）
  if (title) {
    const h = document.createElement('div')
    h.className = 'print-title'
    h.textContent = title
    wrapper.insertBefore(h, wrapper.firstChild)
  }

  // 替换内嵌的 element-plus el-tag 为纯文本
  wrapper.querySelectorAll('.el-tag').forEach(tag => {
    const span = document.createElement('span')
    span.textContent = tag.textContent || ''
    span.className = 'print-tag-print'
    tag.replaceWith(span)
  })

  // 替换 el-button 为纯文本（只在打印容器里）
  wrapper.querySelectorAll('.el-button').forEach(btn => {
    const span = document.createElement('span')
    span.textContent = btn.textContent?.trim() || ''
    btn.replaceWith(span)
  })

  document.body.appendChild(wrapper)
  window.print()

  // 打印后清理
  setTimeout(() => {
    const el = document.getElementById('__print_a4_wrapper__')
    if (el) el.remove()
  }, 300)
}
