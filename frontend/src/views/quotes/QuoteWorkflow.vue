<template>
  <div class="wf-bar">
    <div class="wf-steps">
      <!-- ====== 步骤1: 草稿 ====== -->
      <div class="wf-node" :class="nodeClass('draft')">
        <div class="wf-node-inner">
          <div class="wf-badge" :class="badgeClass('draft')">
            <el-icon v-if="isPast('draft')" :size="18"><Check /></el-icon>
            <span v-else>1</span>
          </div>
          <div class="wf-label">草稿</div>
          <div class="wf-status-text">{{ statusText('draft') }}</div>
        </div>
        <!-- 草稿阶段的操作按钮 -->
        <div v-if="currentStatus === 'draft'" class="wf-actions">
          <button class="wf-action-btn primary" :disabled="saving" @click="$emit('save')">
            <el-icon :size="15"><Edit /></el-icon>
            <span>保存草稿</span>
            <span v-if="saving" class="wf-spinner"></span>
          </button>
        </div>
      </div>

      <!-- 箭头1: 草稿 → 已确认 -->
      <div class="wf-arrow" :class="{ 'arrow-done': isPast('confirmed') }">
        <div class="wf-arrow-body">
          <div class="wf-arrow-line"></div>
          <div class="wf-arrow-head">›</div>
        </div>
        <!-- 确认报价按钮（仅在草稿状态显示） -->
        <Transition name="fade">
          <button
            v-if="currentStatus === 'draft' && isExisting"
            class="wf-action-btn success arrow-btn"
            @click="$emit('confirm')"
          >
            <el-icon :size="15"><CircleCheck /></el-icon>
            <span>确认报价</span>
          </button>
        </Transition>
        <!-- 撤回草稿按钮（仅在已确认状态显示） -->
        <Transition name="fade">
          <button
            v-if="currentStatus === 'confirmed'"
            class="wf-action-btn warning arrow-btn"
            :disabled="reverting"
            @click="$emit('revert')"
          >
            <el-icon :size="15"><Back /></el-icon>
            <span>{{ reverting ? '撤回中…' : '撤回草稿' }}</span>
          </button>
        </Transition>
      </div>

      <!-- ====== 步骤2: 已确认 ====== -->
      <div class="wf-node" :class="nodeClass('confirmed')">
        <div class="wf-node-inner">
          <div class="wf-badge" :class="badgeClass('confirmed')">
            <el-icon v-if="isPast('confirmed')" :size="18"><Check /></el-icon>
            <span v-else>2</span>
          </div>
          <div class="wf-label">已确认</div>
          <div class="wf-status-text">{{ statusText('confirmed') }}</div>
        </div>
      </div>

      <!-- 箭头2: 已确认 → 已转订单 -->
      <div class="wf-arrow" :class="{ 'arrow-done': isPast('converted') }">
        <div class="wf-arrow-body">
          <div class="wf-arrow-line"></div>
          <div class="wf-arrow-head">›</div>
        </div>
        <!-- 转订单按钮（仅在已确认状态显示） -->
        <Transition name="fade">
          <button
            v-if="currentStatus === 'confirmed'"
            class="wf-action-btn danger arrow-btn"
            :disabled="converting"
            @click="$emit('convert')"
          >
            <el-icon :size="15"><Right /></el-icon>
            <span>{{ converting ? '转换中…' : '转订单' }}</span>
          </button>
        </Transition>
      </div>

      <!-- ====== 步骤3: 已转订单 ====== -->
      <div class="wf-node" :class="nodeClass('converted')">
        <div class="wf-node-inner">
          <div class="wf-badge" :class="badgeClass('converted')">
            <el-icon v-if="isPast('converted')" :size="18"><Check /></el-icon>
            <span v-else>3</span>
          </div>
          <div class="wf-label">已转订单</div>
          <div class="wf-status-text">{{ statusText('converted') }}</div>
        </div>
      </div>

      <!-- 预览按钮 -->
      <div class="wf-preview">
        <button class="wf-action-btn outline" @click="$emit('preview')">
          <el-icon :size="15"><View /></el-icon>
          <span>预览</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  currentStatus: string
  isExisting: boolean
  saving: boolean
  converting: boolean
  reverting: boolean
}>()

defineEmits<{
  save: []
  confirm: []
  convert: []
  revert: []
  preview: []
}>()

const statusOrder = ['draft', 'confirmed', 'converted']

function isPast(status: string): boolean {
  return statusOrder.indexOf(props.currentStatus) > statusOrder.indexOf(status)
}

function nodeClass(status: string) {
  if (status === props.currentStatus) return 'node-current'
  if (isPast(status)) return 'node-done'
  return 'node-future'
}

function badgeClass(status: string) {
  if (status === props.currentStatus) return 'badge-current'
  if (isPast(status)) return 'badge-done'
  return 'badge-future'
}

function statusText(status: string): string {
  if (isPast(status) && status !== props.currentStatus) return '已完成'
  if (status === props.currentStatus) {
    const map: Record<string, string> = {
      draft: '进行中',
      confirmed: '等待转订单',
      converted: '流程结束',
    }
    return map[status] || ''
  }
  return ''
}
</script>

<style scoped>
/* ===== 容器 ===== */
.wf-bar {
  background: var(--ad-card);
  border: 1px solid var(--ad-border);
  border-radius: 12px;
  padding: 18px 24px;
  margin-bottom: 20px;
}

.wf-steps {
  display: flex;
  align-items: center;
  gap: 0;
}

/* ===== 节点 ===== */
.wf-node {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
  transition: all 0.3s ease;
}

.wf-node-inner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 18px;
  border-radius: 10px;
  border: 2px solid transparent;
  transition: all 0.35s ease;
  position: relative;
}

/* 当前节点 */
.node-current .wf-node-inner {
  border-color: #409eff;
  background: linear-gradient(135deg, rgba(64, 158, 255, 0.07), rgba(64, 158, 255, 0.03));
  box-shadow: 0 0 0 4px rgba(64, 158, 255, 0.08), 0 2px 6px rgba(64, 158, 255, 0.06);
}

/* 已完成节点 */
.node-done .wf-node-inner {
  border-color: transparent;
  background: transparent;
}

/* 未来节点 */
.node-future .wf-node-inner {
  opacity: 0.5;
}

/* ===== 徽章 ===== */
.wf-badge {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
  flex-shrink: 0;
  transition: all 0.35s ease;
}

.badge-current {
  background: linear-gradient(135deg, #409eff 0%, #2979ff 100%);
  color: #fff;
  box-shadow: 0 3px 10px rgba(64, 158, 255, 0.35);
}

.badge-done {
  background: linear-gradient(135deg, #52c41a 0%, #73d13d 100%);
  color: #fff;
  box-shadow: 0 3px 8px rgba(82, 196, 26, 0.3);
}

.badge-future {
  background: #f5f5f5;
  color: #bfbfbf;
  border: 2px solid #e8e8e8;
}

/* ===== 标签文字 ===== */
.wf-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--ad-text);
  white-space: nowrap;
  letter-spacing: 0.5px;
}

.node-future .wf-label {
  color: #bfbfbf;
}

.wf-status-text {
  font-size: 11px;
  color: var(--ad-text-secondary, #8c8c8c);
  white-space: nowrap;
}

.node-current .wf-status-text {
  color: #409eff;
  font-weight: 500;
}

.node-done .wf-status-text {
  color: #52c41a;
  font-weight: 500;
}

/* ===== 节点内的操作按钮 ===== */
.wf-actions {
  margin-left: 4px;
}

/* ===== 自定义按钮 ===== */
.wf-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 7px 14px;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
  line-height: 1;
  outline: none;
  position: relative;
}

.wf-action-btn:hover {
  transform: translateY(-1px);
}

.wf-action-btn:active {
  transform: translateY(0);
}

.wf-action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none !important;
}

/* 按钮颜色变体 */
.wf-action-btn.primary {
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  color: #fff;
  box-shadow: 0 3px 8px rgba(64, 158, 255, 0.25);
}

.wf-action-btn.primary:hover:not(:disabled) {
  box-shadow: 0 5px 14px rgba(64, 158, 255, 0.35);
}

.wf-action-btn.success {
  background: linear-gradient(135deg, #52c41a 0%, #73d13d 100%);
  color: #fff;
  box-shadow: 0 3px 8px rgba(82, 196, 26, 0.25);
}

.wf-action-btn.success:hover:not(:disabled) {
  box-shadow: 0 5px 14px rgba(82, 196, 26, 0.35);
}

.wf-action-btn.warning {
  background: linear-gradient(135deg, #faad14 0%, #ffc53d 100%);
  color: #fff;
  box-shadow: 0 3px 8px rgba(250, 173, 20, 0.25);
}

.wf-action-btn.warning:hover:not(:disabled) {
  box-shadow: 0 5px 14px rgba(250, 173, 20, 0.35);
}

.wf-action-btn.danger {
  background: linear-gradient(135deg, #ff4d4f 0%, #ff7875 100%);
  color: #fff;
  box-shadow: 0 3px 8px rgba(255, 77, 79, 0.25);
}

.wf-action-btn.danger:hover:not(:disabled) {
  box-shadow: 0 5px 14px rgba(255, 77, 79, 0.35);
}

.wf-action-btn.outline {
  background: var(--ad-card);
  color: var(--ad-text);
  border: 1.5px solid var(--ad-border);
}

.wf-action-btn.outline:hover {
  border-color: #409eff;
  color: #409eff;
  box-shadow: 0 3px 8px rgba(64, 158, 255, 0.1);
}

/* 箭头上的按钮更紧凑 */
.arrow-btn {
  padding: 5px 12px;
  font-size: 12px;
  border-radius: 7px;
}

/* ===== Spinner ===== */
.wf-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  position: absolute;
  right: 8px;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* ===== 箭头 ===== */
.wf-arrow {
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 60px;
  max-width: 120px;
  position: relative;
  height: 60px;
}

.wf-arrow-body {
  display: flex;
  align-items: center;
  width: 100%;
  padding: 0 4px;
}

.wf-arrow-line {
  flex: 1;
  height: 2px;
  background: #e8e8e8;
  border-radius: 2px;
  transition: all 0.3s ease;
}

.arrow-done .wf-arrow-line {
  background: linear-gradient(to right, #52c41a, #73d13d);
  height: 3px;
}

.wf-arrow-head {
  font-size: 20px;
  color: #d9d9d9;
  margin-left: -2px;
  line-height: 1;
  font-weight: 300;
  transition: all 0.3s ease;
}

.arrow-done .wf-arrow-head {
  color: #73d13d;
  font-size: 22px;
}

/* 按钮在箭头上的定位 */
.wf-arrow .wf-action-btn {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 2;
  white-space: nowrap;
}

.wf-arrow .wf-action-btn:hover {
  transform: translate(-50%, -55%);
}

.wf-arrow .wf-action-btn:active {
  transform: translate(-50%, -50%);
}

/* ===== 预览按钮 ===== */
.wf-preview {
  margin-left: 20px;
  padding-left: 20px;
  border-left: 1.5px solid var(--ad-border);
}

/* ===== 过渡动画 ===== */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.fade-enter-from, .fade-leave-to {
  opacity: 0;
  transform: translate(-50%, -50%) scale(0.85);
}

/* ===== 暗色主题 ===== */
:root[data-theme="dark"] .badge-future {
  background: #262626;
  color: #595959;
  border-color: #434343;
}

:root[data-theme="dark"] .node-future {
  opacity: 0.45;
}

:root[data-theme="dark"] .node-future .wf-label {
  color: #595959;
}

:root[data-theme="dark"] .node-current .wf-node-inner {
  background: linear-gradient(135deg, rgba(64, 158, 255, 0.12), rgba(64, 158, 255, 0.05));
  box-shadow: 0 0 0 4px rgba(64, 158, 255, 0.12), 0 2px 6px rgba(64, 158, 255, 0.08);
}

:root[data-theme="dark"] .wf-arrow-line {
  background: #434343;
}

:root[data-theme="dark"] .wf-arrow-head {
  color: #595959;
}

:root[data-theme="dark"] .wf-action-btn.outline {
  border-color: #434343;
}

:root[data-theme="dark"] .wf-action-btn.outline:hover {
  border-color: #409eff;
}

/* ===== 小屏 ===== */
@media (max-width: 860px) {
  .wf-bar {
    padding: 14px 16px;
  }

  .wf-steps {
    flex-wrap: wrap;
    gap: 8px;
  }

  .wf-node-inner {
    padding: 8px 12px;
  }

  .wf-arrow {
    min-width: 30px;
    max-width: 50px;
    height: 50px;
  }

  .wf-arrow .wf-action-btn {
    display: none;
  }

  .wf-preview {
    margin-left: 0;
    padding-left: 0;
    border-left: none;
    width: 100%;
    display: flex;
    justify-content: center;
    padding-top: 8px;
    border-top: 1px solid var(--ad-border);
  }
}
</style>
