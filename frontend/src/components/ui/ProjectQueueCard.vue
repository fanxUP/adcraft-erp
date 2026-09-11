<template>
  <el-card
    shadow="hover"
    class="project-queue-card"
    role="button"
    tabindex="0"
    :aria-label="`打开项目 ${order.order_no}`"
    @click="openOrder"
    @keydown="handleKeydown"
  >
    <div class="card-topline">
      <span class="order-no" :title="order.order_no">{{ order.order_no }}</span>
      <StatusTag :status="order.status_view || order.status" size="sm" />
    </div>

    <div class="project-name" :title="order.project_name">{{ order.project_name }}</div>

    <div class="project-context">
      <div class="project-field">
        <span class="field-label">客户名称</span>
        <span class="field-value" :title="order.customer_name || undefined">{{ order.customer_name || '-' }}</span>
      </div>
      <div class="project-field">
        <span class="field-label">部门/科室</span>
        <span class="field-value" :title="order.department || undefined">{{ order.department || '-' }}</span>
      </div>
    </div>

    <div v-if="authStore.can('order:view_price')" class="order-amount">
      <span class="field-label">订单金额</span>
      <strong>{{ formatMoney(order.total_amount) }}</strong>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import type { OrderListResponse } from '@/types/api'
import { formatMoney } from '@/utils/format'
import { useAuthStore } from '@/stores/auth'
import StatusTag from './StatusTag.vue'

defineProps<{
  order: OrderListResponse
}>()

const emit = defineEmits<{
  open: []
}>()

const authStore = useAuthStore()

function openOrder() {
  emit('open')
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    openOrder()
  }
}
</script>

<style scoped>
.project-queue-card {
  margin-bottom: 8px;
  cursor: pointer;
  background: var(--ad-card);
  border: 1px solid var(--ad-border);
  color: var(--ad-text);
  outline: none;
}

.project-queue-card:hover,
.project-queue-card:focus-visible {
  border-color: var(--ad-primary, #409eff);
}

:deep(.el-card__body) {
  padding: 12px;
}

.card-topline,
.order-amount {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.order-no,
.field-value {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.order-no {
  color: var(--ad-text-secondary, #888);
  font-size: 12px;
}

.project-name {
  margin: 8px 0 10px;
  overflow: hidden;
  color: var(--ad-text);
  font-size: 16px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-context {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 10px;
}

.project-field {
  min-width: 0;
}

.field-label {
  display: block;
  margin-bottom: 2px;
  color: var(--ad-text-secondary, #888);
  font-size: 11px;
}

.field-value {
  display: block;
  color: var(--ad-text);
  font-size: 13px;
}

.order-amount {
  align-items: baseline;
  padding-top: 8px;
  border-top: 1px solid var(--ad-border);
}

.order-amount strong {
  color: var(--ad-text);
  font-size: 16px;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

@media (max-width: 420px) {
  .project-context {
    grid-template-columns: 1fr;
  }
}
</style>
