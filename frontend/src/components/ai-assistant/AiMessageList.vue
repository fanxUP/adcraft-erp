<template>
  <div ref="scrollRef" class="ai-message-list" @scroll="handleScroll">
    <!-- Scroll indicator -->
    <div v-if="showScrollBtn" class="ai-scroll-bottom-btn" @click="scrollToBottom">
      <el-icon :size="14"><ArrowDown /></el-icon>
    </div>

    <AiMessageItem
      v-for="msg in store.messages"
      :key="msg.id"
      :msg="msg"
    />
    <div ref="bottomRef" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onMounted } from 'vue'
import { useAiAssistantStore } from '@/stores/aiAssistantStore'
import AiMessageItem from './AiMessageItem.vue'

const store = useAiAssistantStore()
const scrollRef = ref<HTMLElement | null>(null)
const bottomRef = ref<HTMLElement | null>(null)
const showScrollBtn = ref(false)

async function scrollToBottom() {
  await nextTick()
  if (bottomRef.value) {
    bottomRef.value.scrollIntoView({ behavior: 'smooth' })
  }
  showScrollBtn.value = false
}

function handleScroll() {
  if (!scrollRef.value) return
  const el = scrollRef.value
  const distance = el.scrollHeight - el.scrollTop - el.clientHeight
  showScrollBtn.value = distance > 200
}

// Auto-scroll when messages change or loading state changes
watch(
  () => [store.messages.length, store.loading],
  () => {
    // Only auto-scroll if user is near bottom
    if (!showScrollBtn.value) {
      scrollToBottom()
    }
  },
  { deep: false }
)

onMounted(() => {
  scrollToBottom()
})
</script>

<style scoped>
.ai-message-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
  scroll-behavior: smooth;
  position: relative;
}
.ai-message-list::-webkit-scrollbar {
  width: 4px;
}
.ai-message-list::-webkit-scrollbar-track {
  background: transparent;
}
.ai-message-list::-webkit-scrollbar-thumb {
  background: var(--ai-border, #2a2a4a);
  border-radius: 2px;
}
.ai-scroll-bottom-btn {
  position: sticky;
  bottom: 8px;
  z-index: 10;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--ai-surface, #1c1c34);
  border: 1px solid var(--ai-border, #2a2a4a);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--ai-text-secondary, #8888aa);
  margin: 0 auto;
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
  transition: all 0.2s;
}
.ai-scroll-bottom-btn:hover {
  background: var(--ai-surface-hover, #252545);
  color: var(--ai-text);
}
</style>
