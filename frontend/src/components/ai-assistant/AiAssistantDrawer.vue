<template>
  <div>
    <!-- Overlay backdrop -->
    <Transition name="backdrop-fade">
      <div v-if="store.visible" class="ai-overlay" @click="store.closeDrawer()" />
    </Transition>

    <!-- Side panel -->
    <Transition name="panel-slide">
      <div v-if="store.visible" class="ai-panel">
        <!-- Header -->
        <div class="ai-header">
          <div class="ai-header-brand">
            <div class="ai-header-logo">
              <el-icon :size="18"><ChatDotRound /></el-icon>
            </div>
            <div class="ai-header-info">
              <span class="ai-header-title">AI 助手</span>
              <span class="ai-header-subtitle">当前页面：{{ pageLabel }}</span>
            </div>
          </div>
          <div class="ai-header-actions">
            <el-tooltip content="对话历史" placement="bottom" :show-after="300">
              <el-button text size="small" class="ai-header-btn" @click="showHistory = !showHistory">
                <el-icon><Clock /></el-icon>
              </el-button>
            </el-tooltip>
            <el-tooltip content="新对话" placement="bottom" :show-after="300">
              <el-button text size="small" class="ai-header-btn" @click="store.createNewSession()">
                <el-icon><Plus /></el-icon>
              </el-button>
            </el-tooltip>
            <el-tooltip content="收起" placement="bottom" :show-after="300">
              <el-button text size="small" class="ai-header-btn ai-header-close" @click="store.closeDrawer()">
                <el-icon><Fold /></el-icon>
              </el-button>
            </el-tooltip>
          </div>
        </div>

        <!-- History panel -->
        <Transition name="slide-fade">
          <div v-if="showHistory" class="ai-history">
            <div class="ai-history-header">
              <span>对话历史</span>
              <el-button text size="small" class="ai-history-close" @click="showHistory = false">
                <el-icon><Close /></el-icon>
              </el-button>
            </div>
            <div v-if="store.sessions.length === 0" class="ai-history-empty">
              <el-icon :size="28"><Message /></el-icon>
              <span>暂无对话记录</span>
            </div>
            <div v-else class="ai-history-list">
              <div v-for="s in store.sessions" :key="s.id"
                class="ai-history-item" :class="{ active: s.id === store.currentSessionId }"
                @click="selectSession(s.id)">
                <el-icon :size="13" class="ai-history-item-icon"><ChatDotRound /></el-icon>
                <div class="ai-history-item-body">
                  <span class="ai-history-item-title">{{ s.title || '新对话' }}</span>
                  <span class="ai-history-item-time">{{ formatTime(s.created_at) }}</span>
                </div>
              </div>
            </div>
          </div>
        </Transition>

        <!-- Context bar -->
        <AiContextBar />

        <AiWorkflowGuidanceCard v-if="store.activeGuidance" />

        <!-- Chat window -->
        <AiChatWindow />

        <!-- Loading -->
        <Transition name="fade">
          <div v-if="store.loading" class="ai-loading">
            <div class="ai-loading-dots">
              <span class="ai-dot" />
              <span class="ai-dot" />
              <span class="ai-dot" />
            </div>
            <span>AI 思考中...</span>
          </div>
        </Transition>

        <div class="ai-bottom-spacer" />
      </div>
    </Transition>

    <!-- Fixed footer (always visible when panel is open) -->
    <Transition name="panel-slide">
      <div v-if="store.visible" class="ai-footer">
        <Transition name="slide-up">
          <AiActionPreview v-if="store.pendingAction" />
        </Transition>
        <AiInputBox />
      </div>
    </Transition>

    <AiPageActionSpotlight />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useAiAssistantStore } from '@/stores/aiAssistantStore'
import AiChatWindow from './AiChatWindow.vue'
import AiContextBar from './AiContextBar.vue'
import AiWorkflowGuidanceCard from './AiWorkflowGuidanceCard.vue'
import AiActionPreview from './AiActionPreview.vue'
import AiInputBox from './AiInputBox.vue'
import AiPageActionSpotlight from './AiPageActionSpotlight.vue'

const store = useAiAssistantStore()
const showHistory = ref(false)

const pageLabel = computed(() => {
  const ctx = store.pageContext
  // Show business context in subtitle
  const parts: string[] = [ctx.page_title || ctx.page || '未知']
  if (ctx.customer_name) parts.push(ctx.customer_name)
  if (ctx.project_name) parts.push(ctx.project_name)
  return parts.join(' - ')
})

function formatTime(t: string | null) {
  if (!t) return ''
  const d = new Date(t)
  const diff = Date.now() - d.getTime()
  if (diff < 86400000) return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

function selectSession(id: string) {
  store.switchSession(id)
  showHistory.value = false
}
</script>

<style scoped>
/* ── Overlay ── */
.ai-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.35);
  z-index: 1999;
  backdrop-filter: blur(2px);
}

/* ── Side panel ── */
.ai-panel {
  position: fixed;
  top: 0;
  right: 0;
  width: 440px;
  height: 100vh;
  z-index: 2000;
  background: #16162a;
  display: flex;
  flex-direction: column;
  box-shadow: -4px 0 24px rgba(0, 0, 0, 0.3);
  border-left: 1px solid rgba(255, 255, 255, 0.04);
}

/* ── Header ── */
.ai-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px 12px;
  border-bottom: 1px solid #2a2a4a;
  flex-shrink: 0;
  background: linear-gradient(180deg, rgba(245,108,108,0.04) 0%, transparent 100%);
}
.ai-header-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.ai-header-logo {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: linear-gradient(135deg, #f56c6c 0%, #d03050 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  box-shadow: 0 2px 8px rgba(245,108,108,0.35);
  flex-shrink: 0;
}
.ai-header-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.ai-header-title {
  font-weight: 700;
  font-size: 15px;
  color: #e8e8f0;
  line-height: 1.3;
}
.ai-header-subtitle {
  font-size: 11px;
  color: #666688;
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ai-header-actions {
  display: flex;
  gap: 2px;
  flex-shrink: 0;
}
.ai-header-btn {
  color: #8888aa;
  transition: all 0.2s;
  border-radius: 8px;
  width: 32px;
  height: 32px;
}
.ai-header-btn:hover {
  color: #e8e8f0;
  background: #252545;
}
.ai-header-close:hover {
  color: #f56c6c;
  background: rgba(245,108,108,0.1);
}

/* ── History ── */
.ai-history {
  flex-shrink: 0;
  max-height: 260px;
  overflow-y: auto;
  border-bottom: 1px solid #2a2a4a;
  background: #1c1c34;
}
.ai-history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 18px 6px;
  font-size: 12px;
  font-weight: 600;
  color: #8888aa;
  letter-spacing: 0.5px;
}
.ai-history-close { color: #666688; }
.ai-history-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 24px;
  color: #666688;
  font-size: 13px;
}
.ai-history-list { padding: 4px 0 8px; }
.ai-history-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 18px;
  cursor: pointer;
  color: #e8e8f0;
  font-size: 13px;
  transition: background 0.15s;
  border-left: 3px solid transparent;
}
.ai-history-item:hover { background: #252545; }
.ai-history-item.active {
  background: rgba(245,108,108,0.1);
  border-left-color: #f56c6c;
}
.ai-history-item-icon { color: #666688; flex-shrink: 0; }
.ai-history-item.active .ai-history-item-icon { color: #f56c6c; }
.ai-history-item-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.ai-history-item-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.4;
}
.ai-history-item-time {
  font-size: 11px;
  color: #666688;
  line-height: 1.3;
}

/* ── Loading ── */
.ai-loading {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 18px;
  color: #666688;
  font-size: 13px;
}
.ai-loading-dots { display: flex; gap: 4px; }
.ai-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: #f56c6c;
  animation: dotPulse 1.4s ease-in-out infinite both;
}
.ai-dot:nth-child(2) { animation-delay: 0.16s; }
.ai-dot:nth-child(3) { animation-delay: 0.32s; }
@keyframes dotPulse {
  0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1); }
}

.ai-bottom-spacer { height: 180px; flex-shrink: 0; }

/* ── Footer ── */
.ai-footer {
  position: fixed;
  bottom: 0;
  right: 0;
  width: 440px;
  z-index: 2001;
  background: #1a1a2e;
  border-top: 1px solid #2a2a4a;
  border-left: 1px solid rgba(255,255,255,0.04);
}

/* ── Transitions ── */
.backdrop-fade-enter-active,
.backdrop-fade-leave-active { transition: opacity 0.25s ease; }
.backdrop-fade-enter-from,
.backdrop-fade-leave-to { opacity: 0; }

.panel-slide-enter-active,
.panel-slide-leave-active { transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1); }
.panel-slide-enter-from,
.panel-slide-leave-to { transform: translateX(100%); }

.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.slide-fade-enter-active, .slide-fade-leave-active { transition: all 0.2s ease; }
.slide-fade-enter-from, .slide-fade-leave-to { opacity: 0; transform: translateY(-8px); }

.slide-up-enter-active, .slide-up-leave-active { transition: all 0.25s ease; }
.slide-up-enter-from, .slide-up-leave-to { opacity: 0; transform: translateY(10px); }

@media (max-width: 440px) {
  .ai-panel,
  .ai-footer {
    width: 100vw;
  }

  .ai-header {
    padding-right: 10px;
    padding-left: 12px;
  }
}
</style>
