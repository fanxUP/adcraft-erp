<template>
  <div class="aerial-ledger-page">
    <div class="page-header">
      <h2>每日出车台账</h2>
      <div>
        <el-button @click="handleExport" :disabled="!filters.dateRange?.length">导出 Excel</el-button>
        <el-button type="primary" @click="handleCreate">+ 新增台账</el-button>
      </div>
    </div>

    <!-- 筛选 -->
    <div class="search-bar">
      <el-date-picker v-model="filters.dateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" style="width: 260px" />
      <el-select v-model="filters.driver_id" placeholder="驾驶员" clearable style="width: 120px">
        <el-option v-for="d in driverOptions" :key="d.id" :label="d.driver_name" :value="d.id" />
      </el-select>
      <el-input v-model="filters.customer_name" placeholder="客户名称" clearable style="width: 140px" />
      <el-select v-model="filters.payment_status" placeholder="收款状态" clearable style="width: 120px">
        <el-option label="未收款" value="unpaid" /><el-option label="部分收款" value="partial" />
        <el-option label="已收款" value="paid" /><el-option label="挂账" value="credit" />
        <el-option label="免费" value="free" /><el-option label="并入订单" value="included_in_order" />
      </el-select>
      <el-select v-model="filters.status" placeholder="台账状态" clearable style="width: 120px">
        <el-option label="草稿" value="draft" /><el-option label="已审核" value="reviewed" />
        <el-option label="已作废" value="cancelled" />
      </el-select>
      <el-button type="primary" @click="fetchData">搜索</el-button>
      <el-button @click="resetFilters">重置</el-button>
    </div>

    <!-- 列表 -->
    <el-table :data="list" stripe v-loading="loading" style="width: 100%">
      <el-table-column prop="work_date" label="出车日期" width="100" />
      <el-table-column prop="ledger_no" label="台账编号" width="160" />
      <el-table-column prop="driver_name" label="驾驶员" width="80" />
      <el-table-column prop="customer_name" label="客户" width="120" show-overflow-tooltip />
      <el-table-column prop="work_location" label="作业地点" width="140" show-overflow-tooltip />
      <el-table-column prop="work_content" label="作业内容" width="120" show-overflow-tooltip />
      <el-table-column prop="receivable_amount" label="应收" width="90" align="right">
        <template #default="{ row }">¥{{ row.receivable_amount }}</template>
      </el-table-column>
      <el-table-column prop="received_amount" label="实收" width="90" align="right">
        <template #default="{ row }">¥{{ row.received_amount }}</template>
      </el-table-column>
      <el-table-column prop="unpaid_amount" label="未收" width="90" align="right">
        <template #default="{ row }">
          <span :style="{ color: row.unpaid_amount > 0 ? '#f56c6c' : '' }">¥{{ row.unpaid_amount }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="driver_wage_amount" label="工资" width="80" align="right">
        <template #default="{ row }">¥{{ row.driver_wage_amount }}</template>
      </el-table-column>
      <el-table-column prop="gross_profit" label="毛利润" width="90" align="right">
        <template #default="{ row }">
          <span :style="{ color: row.gross_profit >= 0 ? '#67c23a' : '#f56c6c' }">¥{{ row.gross_profit }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="payment_status" label="收款状态" width="90">
        <template #default="{ row }">
          <el-tag :type="paymentTagType(row.payment_status)" size="small">{{ paymentLabel(row.payment_status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="handleDetail(row)">详情</el-button>
          <el-button link type="primary" size="small" @click="handleEdit(row)" v-if="row.status !== 'cancelled'">编辑</el-button>
          <el-button link type="success" size="small" @click="handleApprove(row)" v-if="row.audit_status === 'pending' && row.status !== 'cancelled'">审核</el-button>
          <el-button link type="warning" size="small" @click="handleReject(row)" v-if="row.audit_status === 'pending' && row.status !== 'cancelled'">驳回</el-button>
          <el-button link type="danger" size="small" @click="handleVoid(row)" v-if="row.status !== 'cancelled'">作废</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="page" v-model:page-size="pageSize"
      :total="total" :page-sizes="[20, 50, 100]"
      layout="total, sizes, prev, pager, next, jumper" style="margin-top: 16px; justify-content: flex-end"
      @current-change="fetchData" @size-change="fetchData"
    />

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑台账' : '新增台账'" width="800px" destroy-on-close>
      <el-form :model="form" label-width="100px">
        <el-divider content-position="left">基础信息</el-divider>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="出车日期" required>
              <el-date-picker v-model="form.work_date" type="date" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="高空车" required>
              <el-select v-model="form.aerial_vehicle_id" style="width: 100%">
                <el-option v-for="v in vehicleOptions" :key="v.id" :label="`${v.vehicle_name} (${v.plate_number})`" :value="v.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="驾驶员" required>
              <el-select v-model="form.driver_id" style="width: 100%">
                <el-option v-for="d in driverOptions" :key="d.id" :label="d.driver_name" :value="d.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="随车人员">
              <el-input v-model="form.assistant_names" placeholder="多人用逗号分隔" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">客户与作业</el-divider>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="客户名称">
              <el-input v-model="form.customer_name" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="联系人">
              <el-input v-model="form.contact_name" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="联系电话">
              <el-input v-model="form.contact_phone" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="关联订单号">
              <el-input v-model="form.related_order_no" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="作业地点" required>
              <el-input v-model="form.work_location" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="作业类型">
              <el-input v-model="form.work_type" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="作业内容">
          <el-input v-model="form.work_content" type="textarea" :rows="2" />
        </el-form-item>

        <el-divider content-position="left">计费与收款</el-divider>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="计费方式">
              <el-select v-model="form.billing_method" style="width: 100%">
                <el-option label="按趟" value="trip" /><el-option label="按小时" value="hour" />
                <el-option label="半天" value="half_day" /><el-option label="全天" value="day" />
                <el-option label="按项目" value="project" /><el-option label="免费" value="free" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="单价">
              <el-input-number v-model="form.unit_price" :min="0" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="数量">
              <el-input-number v-model="form.quantity" :min="0" :precision="1" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="应收金额">
              <el-input-number v-model="form.receivable_amount" :min="0" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="优惠金额">
              <el-input-number v-model="form.discount_amount" :min="0" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="实收金额">
              <el-input-number v-model="form.received_amount" :min="0" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="结算方式">
              <el-select v-model="form.settlement_type" style="width: 100%">
                <el-option label="单独收款" value="separate" /><el-option label="并入订单" value="included_in_order" />
                <el-option label="月结" value="monthly" /><el-option label="免费" value="free" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="驾驶员工资">
              <el-input-number v-model="form.driver_wage_amount" :min="0" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="备注">
              <el-input v-model="form.remark" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailVisible" title="台账详情" width="900px" destroy-on-close>
      <el-tabs v-if="detailData">
        <el-tab-pane label="基础信息">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="台账编号">{{ detailData.ledger_no }}</el-descriptions-item>
            <el-descriptions-item label="出车日期">{{ detailData.work_date }}</el-descriptions-item>
            <el-descriptions-item label="车牌号">{{ detailData.plate_number }}</el-descriptions-item>
            <el-descriptions-item label="驾驶员">{{ detailData.driver_name }}</el-descriptions-item>
            <el-descriptions-item label="随车人员">{{ detailData.assistant_names || '-' }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="statusTagType(detailData.status)" size="small">{{ statusLabel(detailData.status) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="客户">{{ detailData.customer_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="联系人">{{ detailData.contact_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="作业地点" :span="2">{{ detailData.work_location }}</el-descriptions-item>
            <el-descriptions-item label="作业内容" :span="2">{{ detailData.work_content || '-' }}</el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>
        <el-tab-pane label="金额与收款">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="计费方式">{{ billingLabel(detailData.billing_method) }}</el-descriptions-item>
            <el-descriptions-item label="应收金额">¥{{ detailData.receivable_amount }}</el-descriptions-item>
            <el-descriptions-item label="优惠金额">¥{{ detailData.discount_amount }}</el-descriptions-item>
            <el-descriptions-item label="最终金额">¥{{ detailData.final_amount }}</el-descriptions-item>
            <el-descriptions-item label="实收金额">¥{{ detailData.received_amount }}</el-descriptions-item>
            <el-descriptions-item label="未收金额">
              <span :style="{ color: detailData.unpaid_amount > 0 ? '#f56c6c' : '' }">¥{{ detailData.unpaid_amount }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="收款状态">
              <el-tag :type="paymentTagType(detailData.payment_status)" size="small">{{ paymentLabel(detailData.payment_status) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="结算方式">{{ settlementLabel(detailData.settlement_type) }}</el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>
        <el-tab-pane label="成本与利润">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="驾驶员工资">¥{{ detailData.driver_wage_amount }}</el-descriptions-item>
            <el-descriptions-item label="已审核报销">¥{{ detailData.reimbursement_amount }}</el-descriptions-item>
            <el-descriptions-item label="车辆直接费用">¥{{ detailData.vehicle_direct_cost }}</el-descriptions-item>
            <el-descriptions-item label="毛利润">
              <span :style="{ color: detailData.gross_profit >= 0 ? '#67c23a' : '#f56c6c' }">¥{{ detailData.gross_profit }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="预计利润">¥{{ detailData.estimated_profit }}</el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>
        <el-tab-pane label="审计日志">
          <AuditLog :ledger-id="detailData.id" />
        </el-tab-pane>
      </el-tabs>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, defineComponent, h } from 'vue'
import { ElMessage, ElMessageBox, ElTable, ElTableColumn, ElTag, ElEmpty } from 'element-plus'
import {
  getAerialLedgers, getAerialLedger, createAerialLedger, updateAerialLedger,
  voidAerialLedger, approveAerialLedger, rejectAerialLedger,
  getAerialVehicles, getAerialDrivers, getAerialAuditLogs,
  exportAerialLedgers,
} from '@/api/aerial'

const loading = ref(false)
const saving = ref(false)
const list = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const dialogVisible = ref(false)
const detailVisible = ref(false)
const editingId = ref<string | null>(null)
const detailData = ref<any>(null)
const vehicleOptions = ref<any[]>([])
const driverOptions = ref<any[]>([])

const filters = reactive({
  dateRange: [] as string[],
  driver_id: '',
  customer_name: '',
  payment_status: '',
  status: '',
})

const form = reactive({
  work_date: '',
  aerial_vehicle_id: '',
  driver_id: '',
  assistant_names: '',
  customer_name: '',
  contact_name: '',
  contact_phone: '',
  related_order_no: '',
  work_location: '',
  work_type: '',
  work_content: '',
  billing_method: 'trip',
  unit_price: 0,
  quantity: 1,
  receivable_amount: 0,
  discount_amount: 0,
  received_amount: 0,
  settlement_type: 'separate',
  driver_wage_amount: 0,
  remark: '',
})

async function fetchData() {
  loading.value = true
  try {
    const params: any = { page: page.value, page_size: pageSize.value }
    if (filters.dateRange?.length === 2) {
      params.date_from = filters.dateRange[0]
      params.date_to = filters.dateRange[1]
    }
    if (filters.driver_id) params.driver_id = filters.driver_id
    if (filters.customer_name) params.customer_name = filters.customer_name
    if (filters.payment_status) params.payment_status = filters.payment_status
    if (filters.status) params.status = filters.status
    const res = await getAerialLedgers(params)
    list.value = res.items || []
    total.value = res.total || 0
  } catch (e: any) {
    ElMessage.error(e.message || '加载失败')
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.dateRange = []
  filters.driver_id = ''
  filters.customer_name = ''
  filters.payment_status = ''
  filters.status = ''
  page.value = 1
  fetchData()
}

function handleCreate() {
  editingId.value = null
  Object.assign(form, {
    work_date: '', aerial_vehicle_id: '', driver_id: '', assistant_names: '',
    customer_name: '', contact_name: '', contact_phone: '', related_order_no: '',
    work_location: '', work_type: '', work_content: '', billing_method: 'trip',
    unit_price: 0, quantity: 1, receivable_amount: 0, discount_amount: 0,
    received_amount: 0, settlement_type: 'separate', driver_wage_amount: 0, remark: '',
  })
  dialogVisible.value = true
}

function handleEdit(row: any) {
  editingId.value = row.id
  Object.assign(form, {
    work_date: row.work_date, aerial_vehicle_id: row.aerial_vehicle_id, driver_id: row.driver_id,
    assistant_names: row.assistant_names, customer_name: row.customer_name,
    contact_name: row.contact_name, contact_phone: row.contact_phone,
    related_order_no: row.related_order_no, work_location: row.work_location,
    work_type: row.work_type, work_content: row.work_content,
    billing_method: row.billing_method, unit_price: row.unit_price, quantity: row.quantity,
    receivable_amount: row.receivable_amount, discount_amount: row.discount_amount,
    received_amount: row.received_amount, settlement_type: row.settlement_type,
    driver_wage_amount: row.driver_wage_amount, remark: row.remark,
  })
  dialogVisible.value = true
}

async function handleSave() {
  if (!form.work_date) return ElMessage.warning('请选择出车日期')
  if (!form.aerial_vehicle_id) return ElMessage.warning('请选择高空车')
  if (!form.driver_id) return ElMessage.warning('请选择驾驶员')
  if (!form.work_location.trim()) return ElMessage.warning('请填写作业地点')

  saving.value = true
  try {
    if (editingId.value) {
      await updateAerialLedger(editingId.value, form)
      ElMessage.success('修改成功')
    } else {
      await createAerialLedger(form)
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    fetchData()
  } catch (e: any) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleDetail(row: any) {
  try {
    detailData.value = await getAerialLedger(row.id)
    detailVisible.value = true
  } catch (e: any) {
    ElMessage.error(e.message || '加载详情失败')
  }
}

async function handleApprove(row: any) {
  try {
    await ElMessageBox.confirm('确定审核通过此台账？', '审核确认')
    await approveAerialLedger(row.id)
    ElMessage.success('审核通过')
    fetchData()
  } catch {}
}

async function handleReject(row: any) {
  try {
    const { value } = await ElMessageBox.prompt('请输入驳回原因', '驳回台账', { inputType: 'textarea' })
    if (!value?.trim()) return ElMessage.warning('请填写驳回原因')
    await rejectAerialLedger(row.id, value)
    ElMessage.success('已驳回')
    fetchData()
  } catch {}
}

async function handleVoid(row: any) {
  try {
    const { value } = await ElMessageBox.prompt('请输入作废原因', '作废台账', { inputType: 'textarea' })
    if (!value?.trim()) return ElMessage.warning('请填写作废原因')
    await voidAerialLedger(row.id, value)
    ElMessage.success('已作废')
    fetchData()
  } catch {}
}

async function handleExport() {
  if (!filters.dateRange?.length) return ElMessage.warning('请先选择日期范围')
  try {
    await exportAerialLedgers(filters.dateRange[0], filters.dateRange[1])
    ElMessage.success('导出成功')
  } catch (e: any) {
    ElMessage.error(e.message || '导出失败')
  }
}

function statusLabel(s: string) {
  const map: Record<string, string> = { draft: '草稿', assigned: '已派', started: '已出发', working: '作业中', completed: '已完成', returned: '已收车', reviewed: '已审核', settled: '已结算', cancelled: '已作废', abnormal: '异常' }
  return map[s] || s
}
function statusTagType(s: string) {
  const map: Record<string, string> = { draft: 'info', cancelled: 'info', abnormal: 'danger', reviewed: 'success', settled: 'success' }
  return map[s] || ''
}
function paymentLabel(s: string) {
  const map: Record<string, string> = { unpaid: '未收款', partial: '部分收款', paid: '已收款', credit: '挂账', free: '免费', included_in_order: '并入订单' }
  return map[s] || s
}
function paymentTagType(s: string) {
  const map: Record<string, string> = { paid: 'success', partial: 'warning', unpaid: 'danger', free: 'info', included_in_order: 'info' }
  return map[s] || ''
}
function billingLabel(s: string) {
  const map: Record<string, string> = { trip: '按趟', hour: '按小时', half_day: '半天', day: '全天', project: '按项目', free: '免费', included_in_order: '并入订单' }
  return map[s] || s
}
function settlementLabel(s: string) {
  const map: Record<string, string> = { separate: '单独收款', included_in_order: '并入订单', monthly: '月结', free: '免费' }
  return map[s] || s
}

// Audit log sub-component
const AuditLog = defineComponent({
  props: { ledgerId: { type: String, required: true } },
  setup(props) {
    const logs = ref<any[]>([])
    const loadingLog = ref(false)
    async function loadLogs() {
      loadingLog.value = true
      try {
        const res = await getAerialAuditLogs({ ledger_id: props.ledgerId, page_size: 100 })
        logs.value = res.items || []
      } catch {} finally { loadingLog.value = false }
    }
    onMounted(loadLogs)
    return () => h(ElTable, { data: logs.value, stripe: true, size: 'small', vLoading: loadingLog.value }, {
      default: () => [
        h(ElTableColumn, { prop: 'created_at', label: '时间', width: '170' }),
        h(ElTableColumn, { prop: 'action', label: '操作', width: '100' }),
        h(ElTableColumn, { prop: 'source', label: '来源', width: '80' }),
        h(ElTableColumn, { prop: 'remark', label: '备注', minWidth: '200' }),
      ]
    })
  }
})

async function loadOptions() {
  try {
    const [v, d] = await Promise.all([
      getAerialVehicles({ page_size: 100 }),
      getAerialDrivers({ page_size: 100 }),
    ])
    vehicleOptions.value = v.items || []
    driverOptions.value = d.items || []
  } catch {}
}

onMounted(() => {
  loadOptions()
  fetchData()
})
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.search-bar { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; align-items: center; }
</style>
