<template>
  <div class="quote-workflow-bar">
    <!-- 流程图操作栏 -->
    <div class="flow-bar">
      <!-- 步骤1: 草稿 -->
      <div class="flow-step" :class="stepClass('draft')">
        <div class="step-badge" :class="badgeClass('draft')">
          <el-icon v-if="isPast('draft')"><Check /></el-icon>
          <span v-else>1</span>
        </div>
        <div class="step-body">
          <div class="step-title">草稿</div>
          <div class="step-action">
            <!-- 草稿下可点击的操作 -->
            <template v-if="currentStatus === 'draft'">
              <el-button
                type="primary"
                size="small"
                :loading="saving"
                @click="$emit('save')"
                class="flow-btn"
              >
                <el-icon><Edit /></el-icon>
                保存草稿
              </el-button>
            </template>
            <span v-else-if="isPast('draft')" class="step-done">已完成</span>
          </div>
        </div>
      </div>

      <!-- 连接箭头1 -->
      <div class="flow-connector" :class="{ 'connector-active': isPast('confirmed') }">
        <div class="connector-line"></div>
        <div class="connector-arrow">▶</div>
        <!-- 草稿→确认 动作: 确认报价 -->
        <div v-if="currentStatus === 'draft' && isExisting" class="connector-action">
          <el-button
            type="success"
            size="small"
            @click="$emit('confirm')"
            class="flow-btn connector-btn"
          >
            <el-icon><CircleCheck /></el-icon>
            确认报价
          </el-button>
        </div>
        <!-- 已确认→草稿 回退 -->
        <div v-if="currentStatus === 'confirmed'" class="connector-action back-action">
          <el-button
            type="warning"
            size="small"
            :loading="reverting"
            @click="$emit('revert')"
            class="flow-btn connector-btn"
          >
            <el-icon><Refresh /></el-icon>
            撤回草稿
          </el-button>
        </div>
      </div>

      <!-- 步骤2: 已确认 -->
      <div class="flow-step" :class="stepClass('confirmed')">
        <div class="step-badge" :class="badgeClass('confirmed')">
          <el-icon v-if="isPast('confirmed')"><Check /></el-icon>
          <span v-else>2</span>
        </div>
        <div class="step-body">
          <div class="step-title">已确认</div>
          <div class="step-action">
            <span v-if="isPast('confirmed') && currentStatus !== 'confirmed'" class="step-done">已完成</span>
          </div>
        </div>
      </div>

      <!-- 连接箭头2 -->
      <div class="flow-connector" :class="{ 'connector-active': isPast('converted') }">
        <div class="connector-line"></div>
        <div class="connector-arrow">▶</div>
        <!-- 已确认→转订单 动作 -->
        <div v-if="currentStatus === 'confirmed'" class="connector-action">
          <el-button
            type="danger"
            size="small"
            :loading="converting"
            @click="$emit('convert')"
            class="flow-btn connector-btn"
          >
            <el-icon><Right /></el-icon>
            转订单
          </el-button>
        </div>
      </div>

      <!-- 步骤3: 已转订单 -->
      <div class="flow-step" :class="stepClass('converted')">
        <div class="step-badge" :class="badgeClass('converted')">
          <el-icon v-if="isPast('converted')"><Check /></el-icon>
          <span v-else>3</span>
        </div>
        <div class="step-body">
          <div class="step-title">已转订单</div>
          <div class="step-action">
            <span v-if="currentStatus === 'converted'" class="step-done step-final">流程结束</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 预览按钮独立放在右侧 -->
    <div class="flow-extra">
      <el-button type="success" size="small" @click="$emit('preview')" class="flow-btn">
        <el-icon><View /></el-icon>
        预览
      </el-button>
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
  const currentIdx = statusOrder.indexOf(props.currentStatus)
  const stepIdx = statusOrder.indexOf(status)
  return currentIdx > stepIdx
}

function stepClass(status: string) {
  if (status === props.currentStatus) return 'step-current'
  if (isPast(status)) return 'step-done-box'
  return 'step-future'
}

function badgeClass(status: string) {
  if (status === props.currentStatus) return 'badge-current'
  if (isPast(status)) return 'badge-done'
  return 'badge-future'
}
</script>

<style scoped>
.quote-workflow-bar {
  background: var(--ad-card);
  border: 1px solid var(--ad-border);
  border-radius: 10px;
  padding: 20px 24px;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.flow-bar {
  display: flex;
  align-items: center;
  flex: 1;
  gap: 0;
}

/* 每个步骤 */
.flow-step {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 8px;
  border: 2px solid transparent;
  transition: all 0.3s ease;
  min-width: 110px;
}

/* 当前步骤 */
.step-current {
  border-color: #409eff;
  background: rgba(64, 158, 255, 0.06);
  box-shadow: 0 0 0 3px rgba(64, 158, 255, 0.1);
}

/* 已完成步骤 */
.step-done-box {
  border-color: #67c23a;
  background: rgba(103, 194, 58, 0.05);
}

/* 未来步骤 */
.step-future {
  border-color: #e4e7ed;
  background: #fafafa;
  opacity: 0.6;
}

/* 徽章 */
.step-badge {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  flex-shrink: 0;
  transition: all 0.3s ease;
}

.badge-current {
  background: linear-gradient(135deg, #409eff, #66b1ff);
  color: #fff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.35);
}

.badge-done {
  background: linear-gradient(135deg, #67c23a, #85ce61);
  color: #fff;
  box-shadow: 0 2px 6px rgba(103, 194, 58, 0.3);
}

.badge-future {
  background: #f0f2f5;
  color: #c0c4cc;
  border: 2px solid #e4e7ed;
}

/* 步骤标题 */
.step-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--ad-text);
  white-space: nowrap;
}

.step-done {
  font-size: 11px;
  color: #67c23a;
  white-space: nowrap;
}

.step-final {
  color: #67c23a;
  font-weight: 600;
}

/* 连接器 */
.flow-connector {
  display: flex;
  align-items: center;
  position: relative;
  width: 80px;
  flex-shrink: 0;
  padding: 0 4px;
}

.connector-line {
  flex: 1;
  height: 2px;
  background: #dcdfe6;
  transition: all 0.3s ease;
}

.connector-active .connector-line {
  background: linear-gradient(to right, #67c23a, #85ce61);
  height: 3px;
}

.connector-arrow {
  font-size: 8px;
  color: #dcdfe6;
  margin-left: 2px;
  transition: all 0.3s ease;
}

.connector-active .connector-arrow {
  color: #67c23a;
  font-size: 10px;
}

/* 连接器上的动作按钮 */
.connector-action {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 2;
}

.back-action {
  transform: translate(-50%, -50%);
}

.connector-btn {
  white-space: nowrap;
  padding: 2px 8px !important;
  font-size: 11px !important;
  height: 26px !important;
}

/* 通用按钮 */
.flow-btn {
  transition: all 0.2s ease;
}

.flow-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0,0,0,0.12);
}

/* 右侧预览 */
.flow-extra {
  flex-shrink: 0;
  border-left: 1px solid var(--ad-border);
  padding-left: 16px;
}

/* 暗色主题 */
:root[data-theme="dark"] .step-future {
  border-color: #333;
  background: #1a1a1a;
}

:root[data-theme="dark"] .badge-future {
  background: #2c2c2c;
  color: #555;
  border-color: #444;
}

:root[data-theme="dark"] .step-current {
  background: rgba(64, 158, 255, 0.1);
}

:root[data-theme="dark"] .step-done-box {
  background: rgba(103, 194, 58, 0.08);
}

:root[data-theme="dark"] .connector-line {
  background: #444;
}

:root[data-theme="dark"] .connector-arrow {
  color: #444;
}

/* 小屏适配 */
@media (max-width: 800px) {
  .quote-workflow-bar {
    flex-direction: column;
    gap: 12px;
  }

  .flow-bar {
    flex-wrap: wrap;
    gap: 8px;
  }

  .flow-step {
    min-width: 80px;
    padding: 8px 10px;
  }

  .flow-connector {
    width: 40px;
  }

  .connector-action {
    display: none;
  }

  .flow-extra {
    border-left: none;
    border-top: 1px solid var(--ad-border);
    padding-left: 0;
    padding-top: 12px;
    width: 100%;
    display: flex;
    justify-content: center;
  }
}
</style>
