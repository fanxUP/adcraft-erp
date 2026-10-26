<template>
  <el-dialog :model-value="modelValue" title="删除订单并处理关联" width="min(960px, 94vw)" :close-on-click-modal="false" @close="emit('update:modelValue', false)">
    <div v-loading="loading">
      <el-alert type="warning" :closable="false" title="确认后订单移入回收站，未执行工作停止；实际收付款、成本和已完成记录保留。" />
      <el-form label-width="130px" style="margin-top: 18px">
        <el-form-item label="最终结算金额" required><el-input-number v-model="amount" :min="0" :precision="2" @change="preview = null" /><span style="margin-left: 12px">包含已交付部分或约定取消费用</span></el-form-item>
        <el-form-item label="删除原因" required><el-input v-model="reason" maxlength="500" @input="preview = null" /></el-form-item>
      </el-form>
      <template v-if="preview">
        <el-descriptions :column="3" border>
          <el-descriptions-item label="结算应收">¥{{ preview.after.total_amount.toFixed(2) }}</el-descriptions-item>
          <el-descriptions-item label="待收">¥{{ preview.after.unpaid_amount.toFixed(2) }}</el-descriptions-item>
          <el-descriptions-item label="超收/待退">¥{{ preview.after.overpaid_amount.toFixed(2) }}</el-descriptions-item>
        </el-descriptions>
        <el-table :data="preview.association_catalog" max-height="340" style="margin-top: 16px" border>
          <el-table-column prop="label" label="关联模块" width="130" />
          <el-table-column prop="record_no" label="业务编号" min-width="180" />
          <el-table-column label="当前状态" width="130"><template #default="{ row }">{{ statusLabel(row.status) }}</template></el-table-column>
          <el-table-column prop="note" label="处理提示" min-width="260" />
        </el-table>
      </template>
    </div>
    <template #footer><el-button @click="emit('update:modelValue', false)">返回</el-button><el-button :loading="loading" @click="loadPreview">{{ preview ? '重新核对影响' : '查看关联影响' }}</el-button><el-button type="danger" :loading="saving" :disabled="!preview" @click="confirmDelete">确认删除</el-button></template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getOrder, previewOrderDelete, deleteOrder, type OrderDeletePreview } from '@/api/orders'
function statusLabel(value?: string | null) { return ({pending:'待处理', draft:'草稿', confirmed:'已确认', completed:'已完成', cancelled:'已取消', active:'有效', accepted:'已验收', settled:'已结算', in_progress:'进行中', designing:'设计中', rejected:'已驳回'} as Record<string,string>)[value || ''] || value || '-' }
const props = defineProps<{ modelValue: boolean; orderId: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean]; deleted: [] }>()
const loading = ref(false), saving = ref(false), amount = ref(0), reason = ref('客户取消订单')
const preview = ref<OrderDeletePreview | null>(null)
const version = ref('')
watch(() => [props.modelValue, props.orderId], async () => {
  if (!props.modelValue || !props.orderId) return
  loading.value = true; preview.value = null
  try {
    const doc = await getOrder(props.orderId)
    amount.value = doc.status === 'pending_confirm' ? 0 : doc.total_amount
    version.value = doc.updated_at || ''
    reason.value = '客户取消订单'
    await loadPreview()
  } finally { loading.value = false }
})
function payload() { return { reason: reason.value.trim(), expected_updated_at: version.value, settlement_amount: amount.value } }
async function loadPreview() {
  if (!reason.value.trim()) { ElMessage.warning('请填写删除原因'); return }
  loading.value = true
  try { preview.value = await previewOrderDelete(props.orderId, payload()) }
  catch (error: unknown) { ElMessage.error(error instanceof Error ? error.message : '预览失败') }
  finally { loading.value = false }
}
async function confirmDelete() {
  if (!preview.value) return
  saving.value = true
  try {
    await deleteOrder(props.orderId, { ...payload(), preview_id: preview.value.preview_id, plan_hash: preview.value.plan_hash, preview_expires_at: preview.value.preview_expires_at, confirm_high_risk: true })
    ElMessage.success('订单已移入回收站，关联处理事项可继续查看')
    emit('update:modelValue', false); emit('deleted')
  } catch (error: unknown) { preview.value = null; ElMessage.error(error instanceof Error ? error.message : '删除失败，请重新核对') }
  finally { saving.value = false }
}
</script>
