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
        <small v-if="store.pageGuideState === 'restored'">已恢复上次未完成的流程，可从这里继续。</small>
        <small v-if="store.pageGuideState === 'active'">请操作高亮区域，完成后 AI 会自动核验。</small>
        <small v-else-if="store.pageGuideState === 'not_found'">控件暂未显示，请先处理页面中的阻塞条件。</small>
        <small v-else-if="store.pageGuideState === 'completed'">
          {{ store.pageGuideContinuation ? '本步已完成，正在前往下一业务页面。' : '已检测到业务状态更新，可以继续下一步。' }}
        </small>
      </div>
      <div class="ai-page-guide-actions">
        <button
          v-if="store.pageGuideState === 'restored'"
          type="button"
          @click="resumeRestoredGuide"
        >继续引导</button>
        <button
          v-if="store.pageGuideState === 'completed' && store.pageGuideContinuation"
          type="button"
          @click="continueToNextPage"
        >立即继续</button>
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
import { useRoute, useRouter } from 'vue-router'
import { useAiAssistantStore } from '@/stores/aiAssistantStore'
import {
  getPageGuideCalloutPosition,
  isSameWorkflowPath,
  locatePageActionTarget,
} from '@/utils/pageActionGuide'

const store = useAiAssistantStore()
const route = useRoute()
const router = useRouter()
const targetRect = ref<DOMRect | null>(null)
let targetElement: HTMLElement | null = null
let locateTimer: number | null = null
let completionTimer: number | null = null
let resizeObserver: ResizeObserver | null = null
let locateAttempts = 0
let revealAttempted = false

const stateLabel = computed(() => ({
  idle: '页面引导',
  restored: '已恢复引导',
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
  const { left, top, width } = getPageGuideCalloutPosition(rect, {
    width: window.innerWidth,
    height: window.innerHeight,
  })
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

async function resumeRestoredGuide() {
  const targetPath = store.resumePageActionGuide()
  if (!targetPath) return
  if (!isSameWorkflowPath(route.path, targetPath)) {
    await router.push(targetPath)
  }
  await nextTick()
  startLocating()
}

async function continueToNextPage() {
  if (completionTimer !== null) {
    window.clearTimeout(completionTimer)
    completionTimer = null
  }
  const continuation = store.takePageGuideContinuation()
  if (!continuation) {
    store.clearPageActionGuide()
    return
  }
  store.startPageActionGuide(continuation)
  if (!isSameWorkflowPath(route.path, continuation.target_path)) {
    await router.push(continuation.target_path)
  }
}

watch(
  () => store.activePageGuide?.target_key,
  targetKey => {
    clearLocatingResources()
    if (targetKey && store.pageGuideState !== 'restored') void nextTick(startLocating)
  },
  { immediate: true },
)

watch(
  () => store.pageGuideState,
  state => {
    if (completionTimer !== null) window.clearTimeout(completionTimer)
    if (state === 'completed') {
      clearLocatingResources()
      completionTimer = window.setTimeout(
        store.pageGuideContinuation
          ? () => void continueToNextPage()
          : () => store.clearPageActionGuide(),
        store.pageGuideContinuation ? 1600 : 3500,
      )
    }
  },
)

onBeforeUnmount(() => {
  clearLocatingResources()
  if (completionTimer !== null) window.clearTimeout(completionTimer)
})
</script>

<style src="./AiPageActionSpotlight.css"></style>
