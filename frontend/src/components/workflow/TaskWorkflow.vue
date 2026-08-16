<template>
  <div class="tw-bar">
    <div class="tw-flow">
      <template v-for="(step, i) in steps" :key="step.key">
        <div class="tw-col">
          <div
            class="tw-card"
            :class="cardClass(step.key)"
            @click="handleClick(step.key)"
          >
            <div class="tw-icon" :class="iconClass(step.key)">
              <el-icon v-if="isPast(step.key)" :size="16"><Check /></el-icon>
              <span v-else>{{ i + 1 }}</span>
            </div>
            <div class="tw-text">
              <div class="tw-label">{{ step.label }}</div>
              <div v-if="step.key === currentStatus" class="tw-tag cur-tag">当前</div>
              <div v-else-if="isPast(step.key)" class="tw-tag done-tag">已完成</div>
              <div v-else-if="isReachable(step.key)" class="tw-tag ready-tag">可点击</div>
              <div v-else class="tw-tag future-tag">待进行</div>
            </div>
          </div>
        </div>
        <div v-if="i < steps.length - 1" class="tw-conn" :class="{ 'conn-done': isPast(steps[i + 1].key) }">
          <div class="tw-line"></div>
          <div class="tw-point">▶</div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Check } from '@element-plus/icons-vue'

const props = defineProps<{
  steps: { key: string; label: string }[]
  currentStatus: string
  workflow: Record<string, string[]>
  changing: boolean
}>()

const emit = defineEmits<{
  change: [status: string]
}>()

const currentIdx = computed(() => {
  return props.steps.findIndex(s => s.key === props.currentStatus)
})

function isPast(status: string): boolean {
  const idx = props.steps.findIndex(s => s.key === status)
  return idx >= 0 && idx < currentIdx.value
}

function isReachable(status: string): boolean {
  if (props.changing) return false
  return (props.workflow[props.currentStatus] || []).includes(status)
}

function handleClick(status: string) {
  if (!isReachable(status)) return
  emit('change', status)
}

function cardClass(status: string) {
  if (status === props.currentStatus) return 'card-current'
  if (isPast(status)) return 'card-done'
  if (isReachable(status)) return 'card-ready'
  return 'card-disabled'
}

function iconClass(status: string) {
  if (status === props.currentStatus) return 'icon-current'
  if (isPast(status)) return 'icon-done'
  if (isReachable(status)) return 'icon-ready'
  return 'icon-disabled'
}
</script>

<style scoped>
.tw-bar {
  border: 1px solid var(--ad-border);
  border-radius: 12px;
  padding: 20px 24px;
  margin: 16px 0;
  background: var(--ad-card);
}

.tw-flow {
  display: flex;
  align-items: flex-start;
  gap: 0;
  flex-wrap: wrap;
}

.tw-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
}

/* 卡片 */
.tw-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 18px;
  border-radius: 10px;
  border: 2px solid transparent;
  transition: all 0.25s ease;
  cursor: default;
  min-width: 80px;
  min-height: 44px;
  box-sizing: border-box;
}

.tw-icon {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
  transition: all 0.25s ease;
}

.tw-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.tw-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--ad-text);
  white-space: nowrap;
  letter-spacing: 0.3px;
}

.tw-tag {
  font-size: 10px;
  font-weight: 500;
  white-space: nowrap;
}
.cur-tag { color: var(--el-color-primary); }
.done-tag { color: #52c41a; }
.future-tag { color: #d9d9d9; }
.ready-tag { color: var(--el-color-primary); }

/* 连接箭头 */
.tw-conn {
  display: flex;
  align-items: center;
  padding: 0 2px;
  flex-shrink: 0;
  margin-top: 22px;
}

.tw-line {
  width: 32px;
  height: 2px;
  background: var(--ad-border);
  border-radius: 2px;
  transition: all 0.3s ease;
}

.conn-done .tw-line {
  background: linear-gradient(to right, #52c41a, #73d13d);
  height: 3px;
}

.tw-point {
  font-size: 11px;
  color: #d9d9d9;
  margin-left: -2px;
  transition: all 0.3s ease;
}

.conn-done .tw-point {
  color: #73d13d;
}

/* 卡片状态 */
.card-current {
  border-color: var(--el-color-primary);
  background: linear-gradient(135deg, rgba(64,158,255,0.07), rgba(64,158,255,0.03));
  box-shadow: 0 0 0 4px rgba(64,158,255,0.08);
  cursor: pointer;
}
.card-current:hover {
  background: linear-gradient(135deg, rgba(64,158,255,0.12), rgba(64,158,255,0.06));
  box-shadow: 0 2px 12px rgba(64,158,255,0.15);
}
.card-current .tw-label { color: var(--el-color-primary); }

.icon-current {
  background: linear-gradient(135deg, var(--el-color-primary), #66b1ff);
  color: #fff;
  box-shadow: 0 2px 8px rgba(64,158,255,0.35);
}

/* 已完成 */
.card-done { border-color: transparent; }
.card-done .tw-label { color: #52c41a; }

.icon-done {
  background: linear-gradient(135deg, #52c41a, #73d13d);
  color: #fff;
  box-shadow: 0 2px 6px rgba(82,196,26,0.3);
}

/* 可点击 */
.card-ready {
  border-color: var(--el-color-primary);
  border-style: dashed;
  background: rgba(64,158,255,0.03);
  cursor: pointer;
}
.card-ready:hover {
  background: rgba(64,158,255,0.08);
  box-shadow: 0 2px 10px rgba(64,158,255,0.1);
  transform: translateX(3px);
}
.card-ready:active { transform: translateX(0); }
.card-ready .tw-label { color: var(--el-color-primary); }

.icon-ready {
  background: var(--ad-accent-glow);
  color: var(--el-color-primary);
  border: 2px solid var(--el-color-primary);
  cursor: pointer;
}
.icon-ready:hover {
  background: var(--ad-accent-glow);
  box-shadow: 0 0 0 4px rgba(64,158,255,0.15);
}

/* 不可达 */
.card-disabled { border-color: var(--ad-border); background: var(--ad-darker); }
.card-disabled .tw-label { color: #d9d9d9; }

.icon-disabled {
  background: var(--ad-darker);
  color: #d9d9d9;
  border: 2px solid #e8e8e8;
}

/* 暗色主题 */
:root[data-theme*="dark"] .icon-disabled {
  background: #262626; color: #434343; border-color: #434343;
}
:root[data-theme*="dark"] .icon-ready {
  background: rgba(64,158,255,0.12);
}
:root[data-theme*="dark"] .icon-ready:hover {
  background: rgba(64,158,255,0.2);
}
:root[data-theme*="dark"] .card-disabled {
  border-color: #262626; background: #1a1a1a;
}
:root[data-theme*="dark"] .card-disabled .tw-label { color: #434343; }
:root[data-theme*="dark"] .card-disabled .future-tag { color: #434343; }
:root[data-theme*="dark"] .card-current {
  background: rgba(64,158,255,0.1);
  box-shadow: 0 0 0 4px rgba(64,158,255,0.12);
}
:root[data-theme*="dark"] .card-ready {
  background: rgba(64,158,255,0.06);
}
:root[data-theme*="dark"] .card-ready:hover {
  background: rgba(64,158,255,0.15);
}
:root[data-theme*="dark"] .tw-line { background: #434343; }
:root[data-theme*="dark"] .tw-point { color: #595959; }

@media (max-width: 800px) {
  .tw-bar { padding: 14px; }
  .tw-card { padding: 8px 12px; min-width: 56px; min-height: 38px; gap: 6px; }
  .tw-line { width: 16px; }
  .tw-conn { padding: 0 1px; }
  .tw-tag { display: none; }
}
</style>
