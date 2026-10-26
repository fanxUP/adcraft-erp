<template>
  <div>
    <el-card v-if="auth.can('order:read')" shadow="never" style="margin-bottom: 16px">
      <template #header><div class="panel-header"><span>订单变更处理事项</span><el-button text @click="load">刷新</el-button></div></template>
      <el-table :data="actions" empty-text="暂无变更处理事项" border>
        <el-table-column prop="record_no" label="关联编号" min-width="160" />
        <el-table-column prop="detail" label="需要处理的内容" min-width="300" />
        <el-table-column label="状态" width="100"><template #default="{ row }"><el-tag :type="row.status === 'resolved' ? 'success' : 'warning'">{{ row.status === 'resolved' ? '已处理' : '待处理' }}</el-tag></template></el-table-column>
        <el-table-column prop="resolution" label="处理结果" min-width="180" />
        <el-table-column label="操作" width="110"><template #default="{ row }"><el-button v-if="row.status === 'pending'" :disabled="!row.can_resolve" :title="row.resolve_reason" text type="primary" @click="resolve(row.id)">登记处理结果</el-button></template></el-table-column>
      </el-table>
    </el-card>
    <el-card v-if="auth.can('payment:read')" shadow="never">
      <template #header><div class="panel-header"><span>收款、退款与预收分配</span><el-button v-if="auth.can('payment:create')" type="primary" @click="openFunds">登记资金处理</el-button></div></template>
      <el-alert v-if="funds && funds.overpaid_amount > 0" type="warning" :closable="false" :title="`超收/待退 ¥${funds.overpaid_amount.toFixed(2)}，请按实际退款或转预收处理`" style="margin-bottom: 12px" />
      <el-table :data="funds?.payments || []" border empty-text="暂无收付款记录">
        <el-table-column prop="payment_no" label="流水编号" min-width="180" />
        <el-table-column label="类型" width="100"><template #default="{ row }">{{ row.record_type === 'refund' ? '退款' : '收款' }}</template></el-table-column>
        <el-table-column label="状态" width="90"><template #default="{ row }"><el-tag :type="row.is_voided ? 'info' : 'success'">{{ row.is_voided ? '已作废' : '有效' }}</el-tag></template></el-table-column>
        <el-table-column label="金额" width="140"><template #default="{ row }">¥{{ Number(row.amount).toFixed(2) }}</template></el-table-column>
        <el-table-column label="实际收付款日期" min-width="150"><template #default="{ row }">{{ row.paid_at?.slice(0, 10) || '未登记' }}</template></el-table-column>
        <el-table-column prop="remark" label="说明" min-width="220" />
      </el-table>
    </el-card>
    <el-dialog v-model="dialog" title="登记收款、退款或预收分配" width="min(560px, 94vw)" :close-on-click-modal="false">
      <el-form label-width="120px">
        <el-form-item label="处理方式" required><el-select v-model="form.operation"><el-option label="登记收款" value="receipt" /><el-option label="实际退款" value="refund" /><el-option label="超收转合同预收" value="release_credit" /><el-option label="合同预收分配至本单" value="apply_credit" /></el-select></el-form-item>
        <el-form-item v-if="form.operation !== 'receipt'" label="原收款凭据" required><el-select v-model="form.payment_id" style="width: 100%"><el-option v-for="payment in sourcePayments" :key="payment.id" :value="payment.id" :label="`${payment.payment_no}　¥${payment.amount}`" /></el-select></el-form-item>
        <el-form-item label="金额" required><el-input-number v-model="form.amount" :min="0.01" :precision="2" /></el-form-item>
        <el-form-item :label="form.operation === 'refund' ? '实际退款日期' : form.operation === 'receipt' ? '实际收款日期' : '处理日期'" required><el-date-picker v-model="form.paid_at" value-format="YYYY-MM-DD" :clearable="false" /></el-form-item>
        <el-form-item label="原因/凭据编号" required><el-input v-model="form.reason" maxlength="500" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialog = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveFunds">确认登记</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { getOrderActions, getOrderFunds, resolveOrderAction, mutateOrderFunds, type OrderAction, type OrderFunds } from '@/api/orders'
import { newRequestId } from '@/utils/requestId'
const props = defineProps<{ orderId: string }>()
const emit = defineEmits<{ updated: [] }>()
const auth = useAuthStore(), actions = ref<OrderAction[]>([]), funds = ref<OrderFunds | null>(null)
const dialog = ref(false), saving = ref(false)
let requestId = newRequestId()
const form = reactive({ payment_id: '', operation: 'refund' as 'receipt' | 'refund' | 'release_credit' | 'apply_credit', amount: 0.01, paid_at: '', reason: '' })
const sourcePayments = computed(() => (funds.value?.payments || []).filter(payment => payment.amount > 0 && !payment.is_voided))
async function load() {
  if (!props.orderId) return
  try {
    const result = await Promise.all([auth.can('order:read') ? getOrderActions(props.orderId) : Promise.resolve([]), auth.can('payment:read') ? getOrderFunds(props.orderId) : Promise.resolve(null)])
    actions.value = result[0]; funds.value = result[1]
  } catch (error: unknown) { ElMessage.error(error instanceof Error ? error.message : '变更信息读取失败') }
}
watch(() => props.orderId, load, { immediate: true })
async function resolve(id: string) {
  try {
    const result = await ElMessageBox.prompt('请填写处理结果及关联凭据编号', '登记处理结果', { inputValidator: value => Boolean(value?.trim()) || '请填写处理结果' })
    await resolveOrderAction(props.orderId, id, result.value); await load()
  } catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error(error instanceof Error ? error.message : '处理失败') }
}
function openFunds() {
  requestId = newRequestId(); form.paid_at = new Date().toLocaleDateString('sv-SE')
  form.operation = funds.value?.overpaid_amount ? 'refund' : 'receipt'; form.payment_id = sourcePayments.value[0]?.id || ''; form.amount = funds.value?.overpaid_amount || funds.value?.unpaid_amount || 0.01; form.reason = ''; dialog.value = true
}
async function saveFunds() {
  if ((form.operation !== 'receipt' && !form.payment_id) || !form.paid_at || !form.reason.trim()) { ElMessage.warning('请完整填写带 * 的必填项'); return }
  saving.value = true
  try { funds.value = await mutateOrderFunds(props.orderId, { ...form, payment_id: form.operation === 'receipt' ? undefined : form.payment_id, request_id: requestId }); dialog.value = false; await load(); emit('updated'); ElMessage.success('资金处理已登记') }
  catch (error: unknown) { ElMessage.error(error instanceof Error ? error.message : '登记失败') }
  finally { saving.value = false }
}
</script>

<style scoped>
.panel-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
</style>
