<template>
  <template v-if="canViewOutsourceTask">
    <el-dialog :model-value="Boolean(sendItem)" title="发送订单明细外协" width="min(560px, 94vw)"
      :close-on-click-modal="false" :close-on-press-escape="!saving" :show-close="!saving" append-to-body
      @update:model-value="closeSend">
      <template v-if="sendItem">
        <el-alert type="info" :closable="false" show-icon class="dialog-note">
          <template #title>{{ sendItem.item_name }} · {{ isAppend ? '追加外协' : '首次外协' }}</template>
          订单数量 {{ quantityText(sendItem.quantity) }} {{ sendItem.unit || '' }}，
          本任务已分配 {{ quantityText(sendItem.allocated_quantity) }}，剩余可分配 {{ quantityText(sendItem.remaining_quantity) }}。
        </el-alert>
        <el-alert v-if="Number(form.quantity) > sendItem.remaining_quantity" type="warning" :closable="false" show-icon
          class="dialog-note" title="超过剩余可分配数量，必须填写追加原因。" />
        <el-alert v-if="vendorError" type="error" :closable="false" class="dialog-note">
          <template #title>{{ vendorError }}</template>
          <el-button text type="primary" :loading="loadingVendors" @click="loadVendors">重试供应商加载</el-button>
        </el-alert>
        <el-form ref="formRef" :model="form" :rules="rules" label-position="top" :disabled="saving || busy">
          <el-form-item label="外协商" prop="vendor_id">
            <el-select v-model="form.vendor_id" filterable clearable placeholder="选择外协商" :loading="loadingVendors" style="width: 100%">
              <el-option v-for="vendor in eligibleVendors" :key="vendor.id" :label="vendor.name" :value="vendor.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="项目描述"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
          <el-form-item label="外协数量" prop="quantity" required>
            <el-input-number v-model="form.quantity" :min="0.001" :precision="3" controls-position="right" style="width: 100%" />
          </el-form-item>
          <el-form-item v-if="canViewOutsourceCost" label="外协成本单价" prop="unit_price">
            <el-input-number v-model="form.unit_price" :min="0" :precision="2" :step="0.01" controls-position="right" style="width: 100%" />
            <small>供应商成本单价，与订单销售单价分别核算。</small>
          </el-form-item>
          <el-form-item label="预计完成">
            <el-date-picker v-model="form.expected_at" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
          <el-form-item :label="isAppend ? '追加原因/备注' : '备注'" prop="remark" :required="Number(form.quantity) > sendItem.remaining_quantity">
            <el-input v-model="form.remark" type="textarea" :rows="3" placeholder="超过剩余可分配数量时必须填写追加原因" />
          </el-form-item>
        </el-form>
        <el-alert v-if="sendError" :title="sendError" type="error" :closable="false" class="dialog-note" />
      </template>
      <template #footer>
        <el-button :disabled="saving" @click="closeSend(false)">取消</el-button>
        <el-button v-if="canCreateOutsourceTask" type="primary" :loading="saving"
          :disabled="busy || loadingVendors || Boolean(vendorError) || !canViewOutsourceVendor" @click="handleSubmit">确认发送</el-button>
      </template>
    </el-dialog>

    <el-dialog :model-value="Boolean(recordsTarget)" title="外协记录" width="min(1060px, 94vw)" append-to-body
      @update:model-value="value => { if (!value) emit('close-records') }">
      <template v-if="recordsTarget">
        <div class="records-heading">
          <strong>{{ recordsTarget.name }}</strong>
          <el-button text type="primary" :loading="loadingRecords" @click="loadRecords">刷新记录</el-button>
        </div>
        <p v-if="recordsTarget.blocked" class="blocking-note">同阶段有未完成外协，会影响此明细完成或退回。可查看“同明细同阶段全部来源”定位相关任务。</p>
        <el-radio-group v-if="recordsTarget.id" v-model="recordScope" aria-label="外协记录范围" class="record-scope">
          <el-radio-button value="current">本任务发出</el-radio-button>
          <el-radio-button value="stage">同明细同阶段全部来源</el-radio-button>
        </el-radio-group>
        <p class="scope-note">{{ recordScope === 'stage' ? '包含同阶段其他来源外协；行内数量与成本仍仅统计本任务。' : '仅展示本任务发出的外协。' }} 已取消记录不计入分配数量与计划成本。</p>
        <el-alert v-if="recordError" type="error" :closable="false" class="dialog-note">
          <template #title>{{ recordError }}</template>
          <el-button text type="primary" @click="loadRecords">重试记录加载</el-button>
        </el-alert>
        <div v-loading="loadingRecords" class="record-list" aria-live="polite">
          <el-empty v-if="!loadingRecords && !recordError && !records.length" description="暂无外协记录" :image-size="48" />
          <article v-for="record in records" :key="record.id" class="record-card">
            <div class="record-title"><strong>{{ record.task_no }}</strong><StatusTag :status="record.status_view || record.status" size="sm" /></div>
            <dl class="record-fields">
              <div><dt>订单明细</dt><dd>{{ record.order_item_name || '整单外协（历史）' }}</dd></div>
              <div><dt>外协商</dt><dd>{{ record.vendor_name || '—' }}</dd></div>
              <div><dt>数量</dt><dd>{{ quantityText(record.quantity) }}</dd></div>
              <div><dt>来源</dt><dd>
                <span v-if="isCurrentSource(record)">本任务</span>
                <el-button v-else-if="sourceTaskPath(record)" text type="primary" size="small" @click="router.push(sourceTaskPath(record)!)">其他来源任务</el-button>
                <span v-else-if="record.source_task_id">其他来源任务</span>
                <span v-else>历史未记录来源</span>
              </dd></div>
              <template v-if="canViewOutsourceCost">
                <div><dt>外协成本</dt><dd>{{ formatMoney(record.total_amount) }}</dd></div>
                <div><dt>累计已付</dt><dd>{{ formatMoney(record.paid_amount) }}</dd></div>
                <div><dt>剩余待付</dt><dd>{{ formatMoney(record.unpaid_amount) }}</dd></div>
              </template>
            </dl>
          </article>
        </div>
        <el-pagination v-if="recordTotal > 20" v-model:current-page="recordPage" :page-size="20" :total="recordTotal"
          small layout="total, prev, pager, next" class="record-pagination" />
      </template>
      <template #footer>
        <el-button @click="emit('close-records')">关闭</el-button>
        <el-button type="primary" @click="goToOutsourceList">管理外协</el-button>
      </template>
    </el-dialog>
  </template>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { getOutsourceTasks, getOutsourceVendors, sendOutsourceOrderItem } from '@/api/outsource'
import type { OutsourceOrderItemSummary, OutsourceTaskResponse, TaskType, VendorResponse } from '@/types/api'
import { StatusTag } from '@/components/ui'
import { useAuthStore } from '@/stores/auth'
import { formatApiError } from '@/api/requestContract'
import { formatMoney } from '@/utils/format'
import { canUndertakeOutsource } from '@/utils/supplierCapabilities'

const props = defineProps<{
  taskType: TaskType
  taskId: string
  orderId: string
  projectName: string
  sendItem: OutsourceOrderItemSummary | null
  recordsTarget: { id?: string; name: string; blocked: boolean } | null
  busy: boolean
  refreshKey?: string | number | null
}>()
const emit = defineEmits<{ 'close-send': []; 'close-records': []; saving: [value: boolean]; changed: [] }>()
const authStore = useAuthStore()
const router = useRouter()
const canViewOutsourceTask = computed(() => authStore.hasPermission('outsource_center:read') && authStore.hasPermission('outsource_task:read'))
const canCreateOutsourceTask = computed(() => canViewOutsourceTask.value && authStore.hasPermission('outsource_task:create'))
const canViewOutsourceVendor = computed(() => authStore.hasPermission('outsource_vendor:read'))
const canViewOutsourceCost = computed(() => authStore.hasPermission('finance:view_cost'))
const saving = ref(false)
const sendError = ref('')
const formRef = ref<FormInstance>()
const vendors = ref<VendorResponse[]>([])
const loadingVendors = ref(false)
const vendorError = ref('')
const eligibleVendors = computed(() => vendors.value.filter(vendor => canUndertakeOutsource(vendor, props.taskType)))
const isAppend = computed(() => Boolean(props.sendItem?.active_task_count))
const form = reactive({ vendor_id: '', description: '', quantity: 1, unit_price: 0, expected_at: '', remark: '' })
const records = ref<OutsourceTaskResponse[]>([])
const recordScope = ref<'current' | 'stage'>('current')
const recordPage = ref(1)
const recordTotal = ref(0)
const loadingRecords = ref(false)
const recordError = ref('')
let recordsVersion = 0
let vendorsVersion = 0
let alive = true
const rules: FormRules = {
  vendor_id: [{ required: true, message: '请选择外协商', trigger: 'change' }],
  quantity: [{ validator: (_rule, value, callback) => {
    if (!Number.isFinite(Number(value)) || Number(value) <= 0) callback(new Error('外协数量必须大于 0'))
    else callback()
  }, trigger: ['change', 'blur'] }],
  remark: [{ validator: (_rule, value, callback) => {
    if (props.sendItem && Number(form.quantity) > props.sendItem.remaining_quantity && !String(value || '').trim()) callback(new Error('超过剩余数量时必须填写追加原因'))
    else callback()
  }, trigger: ['change', 'blur'] }],
}
function quantityText(value: number) {
  return Number(value).toLocaleString('zh-CN', { maximumFractionDigits: 3 })
}
function closeSend(value: boolean) {
  if (!value && !saving.value) emit('close-send')
}
async function loadVendors() {
  const version = ++vendorsVersion
  if (!canCreateOutsourceTask.value || !canViewOutsourceVendor.value || !props.sendItem) return
  loadingVendors.value = true
  vendorError.value = ''
  vendors.value = []
  try {
    const result: VendorResponse[] = []
    for (let page = 1; ; page++) {
      const data = await getOutsourceVendors({ page, page_size: 100, is_active: true })
      if (version !== vendorsVersion || !alive) return
      result.push(...data.items)
      if (result.length >= data.total || !data.items.length) break
    }
    vendors.value = result
  } catch (cause) {
    if (version === vendorsVersion && alive) vendorError.value = formatApiError(cause, '供应商加载失败，请重试')
  } finally {
    if (version === vendorsVersion && alive) loadingVendors.value = false
  }
}
async function handleSubmit() {
  if (saving.value || props.busy || !props.sendItem || !canCreateOutsourceTask.value || !canViewOutsourceVendor.value || loadingVendors.value || vendorError.value) return
  const item = props.sendItem
  const valid = await formRef.value?.validate().catch(() => false)
  if (!alive || !valid || saving.value || props.busy || props.sendItem !== item) return
  if (!eligibleVendors.value.some(vendor => vendor.id === form.vendor_id)) {
    sendError.value = '请选择可承接当前任务类型的有效外协商'
    return
  }
  saving.value = true
  sendError.value = ''
  emit('saving', true)
  try {
    await sendOutsourceOrderItem(props.orderId, item.id, {
      vendor_id: form.vendor_id, task_type: props.taskType, source_task_type: props.taskType, source_task_id: props.taskId,
      quantity: form.quantity, unit_price: canViewOutsourceCost.value ? form.unit_price : 0,
      description: form.description || undefined, expected_at: form.expected_at || undefined, remark: form.remark || undefined,
    })
    if (!alive) return
    ElMessage.success(isAppend.value ? '已追加订单明细外协' : '已发送订单明细外协')
    emit('close-send')
    emit('changed')
    if (props.recordsTarget) void loadRecords()
  } catch (cause) {
    if (alive) sendError.value = formatApiError(cause, '发送外协失败，请重试')
  } finally {
    if (alive) { saving.value = false; emit('saving', false) }
  }
}
function isCurrentSource(record: OutsourceTaskResponse) {
  return record.source_task_type === props.taskType && record.source_task_id === props.taskId
}
function sourceTaskPath(record: OutsourceTaskResponse) {
  const paths: Record<string, string> = { design: 'design-tasks', production: 'production-tasks', installation: 'installation-tasks' }
  const path = paths[record.source_task_type || '']
  return path && record.source_task_id && authStore.hasPermission(`${record.source_task_type}_task:read`)
    ? `/${path}/${encodeURIComponent(record.source_task_id)}` : null
}
function goToOutsourceList() {
  const query: Record<string, string> = { order_id: props.orderId, task_type: props.taskType }
  if (recordScope.value === 'current') { query.source_task_type = props.taskType; query.source_task_id = props.taskId }
  if (props.recordsTarget?.id) query.order_item_id = props.recordsTarget.id
  void router.push({ path: '/outsource/tasks', query })
}
async function loadRecords() {
  const version = ++recordsVersion
  records.value = []
  recordTotal.value = 0
  recordError.value = ''
  loadingRecords.value = false
  if (!props.recordsTarget || !canViewOutsourceTask.value) return
  loadingRecords.value = true
  try {
    const result = await getOutsourceTasks({
      page: recordPage.value, page_size: 20, order_id: props.orderId, order_item_id: props.recordsTarget.id,
      task_type: props.taskType,
      ...(recordScope.value === 'current' ? { source_task_type: props.taskType, source_task_id: props.taskId } : {}),
    })
    if (version !== recordsVersion || !alive) return
    records.value = result.items
    recordTotal.value = result.total
  } catch (cause) {
    if (version === recordsVersion && alive) recordError.value = formatApiError(cause, '外协记录加载失败，请重试')
  } finally {
    if (version === recordsVersion && alive) loadingRecords.value = false
  }
}
watch(() => props.sendItem, item => {
  vendorsVersion++
  loadingVendors.value = false
  sendError.value = ''
  if (!item) return
  Object.assign(form, { vendor_id: '', description: `${props.projectName || '订单项目'} - ${item.item_name}`,
    quantity: item.remaining_quantity > 0 ? Number(item.remaining_quantity.toFixed(3)) : 1, unit_price: 0, expected_at: '', remark: '' })
  void nextTick(() => formRef.value?.clearValidate())
  void loadVendors()
}, { immediate: true })
watch(() => props.recordsTarget, target => {
  recordScope.value = target?.blocked ? 'stage' : 'current'
  recordPage.value = 1
}, { immediate: true })
watch([() => props.recordsTarget, recordScope, recordPage, () => props.refreshKey], () => void loadRecords(), { immediate: true })
watch(recordScope, () => { recordPage.value = 1 }, { flush: 'sync' })
onBeforeUnmount(() => { alive = false; recordsVersion++; vendorsVersion++ })
</script>

<style scoped>
.dialog-note { margin-bottom: 14px; }
.records-heading, .record-title { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; }
.record-scope { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 12px; }
.scope-note, small { color: var(--ad-text-secondary); font-size: 12px; line-height: 1.6; }
.blocking-note { color: var(--el-color-warning-dark-2); font-size: 13px; line-height: 1.6; }
.record-list { min-height: 60px; }
.record-card { padding: 14px; margin-top: 10px; border: 1px solid var(--ad-border); border-radius: 6px; }
.record-fields { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(150px, 100%), 1fr)); gap: 12px; margin: 12px 0 0; }
.record-fields dt { color: var(--ad-text-secondary); font-size: 12px; }
.record-fields dd { margin: 4px 0 0; overflow-wrap: anywhere; }
.record-fields .el-button { padding: 0; height: auto; }
.record-pagination { justify-content: flex-end; margin-top: 14px; }
</style>
