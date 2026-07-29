<template>
  <Teleport to="body">
    <div
      v-if="targetRect && store.pageGuideState === 'active'"
      class="ai-page-target-outline"
      :style="outlineStyle"
      aria-hidden="true"
    />

    <section
      v-if="store.activePageGuide"
      class="ai-page-guide-callout"
      :class="`is-${store.pageGuideState}`"
      :style="calloutStyle"
      role="status"
      aria-live="polite"
    >
      <div class="ai-page-guide-copy">
        <span class="ai-page-guide-eyebrow">{{ stateLabel }}</span>
        <strong>{{ store.activePageGuide.label }}</strong>
        <small v-if="store.pageGuideState === 'active'">请操作高亮区域，完成后 AI 会自动核验。</small>
        <small v-else-if="store.pageGuideState === 'not_found'">控件暂未显示，请先处理页面中的阻塞条件。</small>
        <small v-else-if="store.pageGuideState === 'completed'">已检测到业务状态更新，可以继续下一步。</small>
      </div>
      <div class="ai-page-guide-actions">
        <button
          v-if="store.pageGuideState === 'not_found'"
          type="button"
          @click="startLocating"
        >重试</button>
        <button
          type="button"
          aria-label="关闭页面操作引导"
          @click="store.clearPageActionGuide()"
        >×</button>
      </div>
    </section>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import type { CSSProperties } from 'vue'
import { useAiAssistantStore } from '@/stores/aiAssistantStore'
import { locatePageActionTarget } from '@/utils/pageActionGuide'

const store = useAiAssistantStore()
const targetRect = ref<DOMRect | null>(null)
let targetElement: HTMLElement | null = null
let locateTimer: number | null = null
let completionTimer: number | null = null
let resizeObserver: ResizeObserver | null = null
let locateAttempts = 0
let revealAttempted = false

const stateLabel = computed(() => ({
  idle: '页面引导',
  locating: '正在定位',
  active: '下一步',
  completed: '本步已完成',
  not_found: '暂未找到控件',
}[store.pageGuideState]))

const outlineStyle = computed<CSSProperties>(() => {
  const rect = targetRect.value
  if (!rect) return {}
  return {
    top: `${Math.max(4, rect.top - 6)}px`,
    left: `${Math.max(4, rect.left - 6)}px`,
    width: `${rect.width + 12}px`,
    height: `${rect.height + 12}px`,
  }
})

const calloutStyle = computed<CSSProperties>(() => {
  const rect = targetRect.value
  if (!rect || store.pageGuideState !== 'active') {
    return { right: '24px', bottom: '24px' }
  }
  const width = 320
  const left = Math.max(12, Math.min(rect.left, window.innerWidth - width - 12))
  const spaceBelow = window.innerHeight - rect.bottom
  const top = spaceBelow >= 130
    ? rect.bottom + 14
    : Math.max(12, rect.top - 116)
  return { left: `${left}px`, top: `${top}px`, width: `${width}px` }
})

function updateTargetRect() {
  targetRect.value = targetElement?.getBoundingClientRect() || null
}

function clearLocatingResources() {
  if (locateTimer !== null) {
    window.clearInterval(locateTimer)
    locateTimer = null
  }
  resizeObserver?.disconnect()
  resizeObserver = null
  window.removeEventListener('scroll', updateTargetRect, true)
  window.removeEventListener('resize', updateTargetRect)
  targetElement?.classList.remove('ai-page-guided-control')
  targetElement = null
  targetRect.value = null
}

async function tryLocate() {
  const guide = store.activePageGuide
  if (!guide) return
  locateAttempts += 1
  const located = locatePageActionTarget(guide.target_key)
  if (!located) {
    if (locateAttempts >= 25) {
      clearLocatingResources()
      store.setPageGuideState('not_found')
    }
    return
  }

  if (located.revealControl && !revealAttempted) {
    revealAttempted = true
    located.revealControl.click()
    await nextTick()
    return
  }

  clearLocatingResources()
  targetElement = located.element
  targetElement.classList.add('ai-page-guided-control')
  targetElement.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' })
  updateTargetRect()
  resizeObserver = new ResizeObserver(updateTargetRect)
  resizeObserver.observe(targetElement)
  window.addEventListener('scroll', updateTargetRect, true)
  window.addEventListener('resize', updateTargetRect)
  store.setPageGuideState('active')
}

function startLocating() {
  clearLocatingResources()
  locateAttempts = 0
  revealAttempted = false
  store.setPageGuideState('locating')
  void tryLocate()
  locateTimer = window.setInterval(() => void tryLocate(), 160)
}

watch(
  () => store.activePageGuide?.target_key,
  targetKey => {
    clearLocatingResources()
    if (targetKey) void nextTick(startLocating)
  },
  { immediate: true },
)

watch(
  () => store.pageGuideState,
  state => {
    if (completionTimer !== null) window.clearTimeout(completionTimer)
    if (state === 'completed') {
      clearLocatingResources()
      completionTimer = window.setTimeout(() => store.clearPageActionGuide(), 3500)
    }
  },
)

onBeforeUnmount(() => {
  clearLocatingResources()
  if (completionTimer !== null) window.clearTimeout(completionTimer)
})
</script>

<style>
.ai-page-target-outline {
  position: fixed;
  z-index: 2200;
  border: 3px solid var(--el-color-primary);
  border-radius: 10px;
  box-shadow: 0 0 0 5px color-mix(in srgb, var(--el-color-primary) 20%, transparent);
  pointer-events: none;
  animation: ai-page-guide-pulse 1.4s ease-in-out infinite;
}

.ai-page-guide-callout {
  position: fixed;
  z-index: 2201;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  width: min(320px, calc(100vw - 24px));
  padding: 12px 14px;
  border: 1px solid var(--ad-border);
  border-left: 4px solid var(--el-color-primary);
  border-radius: 8px;
  background: var(--ad-card);
  color: var(--ad-text);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.24);
}

.ai-page-guide-callout.is-completed {
  border-left-color: var(--el-color-success);
}

.ai-page-guide-callout.is-not_found {
  border-left-color: var(--el-color-warning);
}

.ai-page-guide-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 3px;
}

.ai-page-guide-eyebrow {
  color: var(--el-color-primary);
  font-size: 11px;
}

.ai-page-guide-copy strong {
  font-size: 14px;
  line-height: 1.4;
}

.ai-page-guide-copy small {
  color: var(--ad-text-secondary);
  font-size: 12px;
  line-height: 1.5;
}

.ai-page-guide-actions {
  display: flex;
  align-items: flex-start;
  gap: 4px;
}

.ai-page-guide-actions button {
  border: 0;
  border-radius: 4px;
  padding: 2px 6px;
  background: transparent;
  color: var(--ad-text-secondary);
  cursor: pointer;
  font: inherit;
}

.ai-page-guide-actions button:focus-visible {
  outline: 2px solid var(--el-color-primary);
  outline-offset: 2px;
}

@keyframes ai-page-guide-pulse {
  50% { box-shadow: 0 0 0 9px color-mix(in srgb, var(--el-color-primary) 8%, transparent); }
}

@media (prefers-reduced-motion: reduce) {
  .ai-page-target-outline { animation: none; }
}
</style>
