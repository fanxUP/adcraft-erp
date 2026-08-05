<template>
  <div class="page">
    <div class="page-header">
      <h2>每日出车台账</h2>
      <div class="ledger-actions">
        <el-button @click="handleExport" :disabled="!filters.dateRange?.length">导出 Excel</el-button>
        <el-button type="primary" @click="handleCreate">+ 新增台账</el-button>
      </div>
    </div>

    <!-- 筛选 -->
    <el-card shadow="never" class="filter-card">
      <el-form :model="filters" inline>
        <el-form-item label="日期">
          <el-date-picker v-model="filters.dateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" style="width: 240px" />
        </el-form-item>
        <el-form-item label="人员">
          <el-select v-model="filters.personnel_id" placeholder="全部" clearable style="width: 120px">
            <el-option v-for="d in personnelOptions" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="客户名称">
          <el-input v-model="filters.customer_name" placeholder="请输入" clearable style="width: 140px" />
        </el-form-item>
        <el-form-item label="作业地点">
          <el-select v-model="filters.work_location" placeholder="全部" clearable style="width: 130px">
            <el-option v-for="loc in locationOptions" :key="loc" :label="loc" :value="loc" />
          </el-select>
        </el-form-item>
        <el-form-item label="收款状态">
          <el-select v-model="filters.payment_status" placeholder="全部" clearable style="width: 120px">
            <el-option label="未收款" value="unpaid" /><el-option label="部分收款" value="partial" />
            <el-option label="已收款" value="paid" /><el-option label="挂账" value="credit" />
            <el-option label="免费" value="free" /><el-option label="并入订单" value="included_in_order" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchData">搜索</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 列表 -->
    <el-table :data="list" v-loading="loading" stripe style="margin-top: 16px" @sort-change="handleSortChange"
      :show-summary="list.length > 0" :summary-method="summaryMethod">
      <el-table-column prop="ledger_no" label="台账编号" width="140" sortable="custom" show-overflow-tooltip fixed="left" />
      <el-table-column prop="work_date" label="出车日期" width="100" sortable="custom" />
      <el-table-column prop="work_location" label="作业地点" width="110" show-overflow-tooltip sortable="custom" />
      <el-table-column prop="billing_method" label="计费方式" width="96" sortable="custom">
        <template #default="{ row }">{{ billingLabel(row.billing_method) }}</template>
      </el-table-column>
      <el-table-column prop="quantity" label="数量" width="68" align="center" sortable="custom" />
      <el-table-column prop="work_content" label="作业内容" width="150" show-overflow-tooltip sortable="custom" />
      <el-table-column prop="receivable_amount" label="应收金额" width="100" align="right" sortable="custom">
        <template #default="{ row }">¥{{ fmtMoney(row.receivable_amount) }}</template>
      </el-table-column>
      <el-table-column prop="received_amount" label="已收金额" width="100" align="right" sortable="custom">
        <template #default="{ row }">¥{{ fmtMoney(row.received_amount) }}</template>
      </el-table-column>
      <el-table-column prop="unpaid_amount" label="欠款金额" width="100" align="right" sortable="custom">
        <template #default="{ row }">
          <span :style="{ color: row.unpaid_amount > 0 ? '#f56c6c' : '' }">¥{{ fmtMoney(row.unpaid_amount) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="payment_status" label="收款状态" width="94" align="center" sortable="custom">
        <template #default="{ row }">
          <el-tag :type="paymentTagType(row.payment_status)" size="small">{{ paymentLabel(row.payment_status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="name" label="驾驶员" width="110" show-overflow-tooltip sortable="custom" />
      <el-table-column prop="customer_name" label="客户名称" width="150" show-overflow-tooltip sortable="custom" />
      <el-table-column prop="contact_phone" label="联系电话" width="116" show-overflow-tooltip sortable="custom" />
      <el-table-column label="操作" width="200" align="center" fixed="right">
        <template #default="{ row }">
          <el-button link type="success" size="small" @click="handleSettle(row)">结算</el-button>
          <el-button link type="primary" size="small" @click="handleDetail(row)">详情</el-button>
          <el-button link type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
          <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="page" v-model:page-size="pageSize"
      :total="total" :page-sizes="[10, 20, 50, 100]"
      layout="total, sizes, prev, pager, next" style="margin-top: 16px; justify-content: flex-end"
      @change="fetchData"
    />

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑台账' : '新增台账'" width="800px" destroy-on-close :close-on-click-modal="false">
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
            <el-form-item label="人员" required>
              <el-select v-model="form.personnel_id" style="width: 100%">
                <el-option v-for="d in personnelOptions" :key="d.id" :label="d.name" :value="d.id" />
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

        <el-divider content-position="left">计费</el-divider>
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
            <el-form-item label="数量">
              <el-input-number v-model="form.quantity" :min="0" :precision="1" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="应收金额">
              <el-input-number v-model="form.receivable_amount" :min="0" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="备注">
          <el-input v-model="form.remark" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailVisible" title="台账详情" width="900px" destroy-on-close :close-on-click-modal="false">
      <el-tabs v-if="detailData">
        <el-tab-pane label="基础信息">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="台账编号">{{ detailData.ledger_no }}</el-descriptions-item>
            <el-descriptions-item label="出车日期">{{ detailData.work_date }}</el-descriptions-item>
            <el-descriptions-item label="车牌号">{{ detailData.plate_number }}</el-descriptions-item>
            <el-descriptions-item label="人员">{{ detailData.name }}</el-descriptions-item>
            <el-descriptions-item label="随车人员">{{ detailData.assistant_names || '-' }}</el-descriptions-item>
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
            <el-descriptions-item label="人员工资">¥{{ detailData.personnel_wage_amount }}</el-descriptions-item>
            <el-descriptions-item label="报销金额">¥{{ detailData.reimbursement_amount }}</el-descriptions-item>
            <el-descriptions-item label="车辆直接费用">¥{{ detailData.vehicle_direct_cost }}</el-descriptions-item>
            <el-descriptions-item label="毛利润">
              <span :style="{ color: detailData.gross_profit >= 0 ? '#67c23a' : '#f56c6c' }">¥{{ detailData.gross_profit }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="预计利润">¥{{ detailData.estimated_profit }}</el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>
      </el-tabs>
    </el-dialog>

    <!-- 结算对话框 -->
    <el-dialog v-model="settleVisible" title="台账结算" width="680px" destroy-on-close :close-on-click-modal="false">
      <template v-if="settleData">
        <el-descriptions :column="2" border size="small" style="margin-bottom: 16px">
          <el-descriptions-item label="台账编号">{{ settleData.ledger_no }}</el-descriptions-item>
          <el-descriptions-item label="客户">{{ settleData.customer_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="应收金额">¥{{ settleData.receivable_amount }}</el-descriptions-item>
          <el-descriptions-item label="最终金额">¥{{ settleData.final_amount }}</el-descriptions-item>
          <el-descriptions-item label="已收金额">¥{{ settleData.received_amount }}</el-descriptions-item>
          <el-descriptions-item label="未收金额">
            <span :style="{ color: settleData.unpaid_amount > 0 ? '#f56c6c' : '' }">¥{{ settleData.unpaid_amount }}</span>
          </el-descriptions-item>
        </el-descriptions>
        <el-alert v-if="settleReadonly" type="info" :closable="false" title="该台账已结清/无需结算，仅可查看结算记录" style="margin-bottom: 12px" />
        <el-form v-if="!settleReadonly" :model="settleForm" label-width="100px">
          <el-form-item label="本次收款金额" required>
            <el-input-number v-model="settleForm.amount" :min="0.01" :max="settleData.unpaid_amount || 0" :precision="2" style="width: 100%" />
          </el-form-item>
          <el-form-item label="收款方式" required>
            <el-select v-model="settleForm.payment_method" placeholder="请选择" style="width: 100%">
              <el-option label="微信" value="wechat" />
              <el-option label="支付宝" value="alipay" />
              <el-option label="银行转账" value="bank_transfer" />
              <el-option label="现金" value="cash" />
            </el-select>
          </el-form-item>
          <el-form-item label="收款时间">
            <el-date-picker v-model="settleForm.payment_time" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
          <el-form-item label="收款人">
            <el-select v-model="settleForm.payee_id" placeholder="请选择收款人" clearable style="width: 100%">
              <el-option v-for="d in personnelOptions" :key="d.id" :label="d.name" :value="d.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="备注">
            <el-input v-model="settleForm.remark" />
          </el-form-item>
        </el-form>
        <el-divider content-position="left">结算记录</el-divider>
        <el-table :data="settlements" size="small" border v-loading="settlementsLoading" max-height="200">
          <el-table-column label="收款时间" width="130">
            <template #default="{ row }">{{ (row.payment_time || '').slice(0, 10) || '-' }}</template>
          </el-table-column>
          <el-table-column label="收款金额" width="110">
            <template #default="{ row }">¥{{ row.amount }}</template>
          </el-table-column>
          <el-table-column label="收款方式" width="110">
            <template #default="{ row }">{{ paymentMethodLabel(row.payment_method) }}</template>
          </el-table-column>
          <el-table-column label="收款人" width="100">
            <template #default="{ row }">{{ row.payee_name || '-' }}</template>
          </el-table-column>
          <el-table-column label="备注" prop="remark" show-overflow-tooltip>
            <template #default="{ row }">{{ row.remark || '-' }}</template>
          </el-table-column>
          <el-table-column label="操作" width="70" align="center">
            <template #default="{ row }">
              <el-button link type="danger" size="small" @click="handleDeleteSettlement(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </template>
      <template #footer>
        <el-button @click="settleVisible = false">{{ settleReadonly ? '关闭' : '取消' }}</el-button>
        <el-button v-if="!settleReadonly" type="primary" @click="handleSettleSubmit" :loading="settling">确认结算</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, ElTag } from 'element-plus'
// 手动引入的组件不经过 unplugin-vue-components 自动按需补样式，需显式引入，否则表格/标签无样式
import 'element-plus/es/components/tag/style/css'
import {
  getAerialLedgers, getAerialLedger, createAerialLedger, updateAerialLedger,
  settleAerialLedger, getAerialLedgerSettlements, deleteAerialLedgerSettlement,
  deleteAerialLedger, getAerialVehicles, getAerialPersonnel,
  getAerialLedgerLocations, exportAerialLedgers,
  type AerialLedger,
  type AerialLedgerSummary,
  type AerialSettlement,
  type AerialPersonnel,
  type AerialQueryParams,
  type AerialVehicle,
} from '@/api/aerial'
import { getErrorMessage } from '@/utils/error'

const loading = ref(false)
const saving = ref(false)
const list = ref<AerialLedger[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const summary = ref<AerialLedgerSummary | null>(null)
const dialogVisible = ref(false)
const detailVisible = ref(false)
const settleVisible = ref(false)
const settling = ref(false)
const editingId = ref<string | null>(null)
const detailData = ref<AerialLedger | null>(null)
const settleData = ref<AerialLedger | null>(null)
const settleReadonly = ref(false)
const settlements = ref<AerialSettlement[]>([])
const settlementsLoading = ref(false)
const settleForm = reactive({
  amount: 0,
  payment_method: '',
  payment_time: '',
  payee_id: '',
  remark: '',
})
const vehicleOptions = ref<AerialVehicle[]>([])
const personnelOptions = ref<AerialPersonnel[]>([])
const locationOptions = ref<string[]>([])

const filters = reactive({
  dateRange: [] as string[],
  personnel_id: '',
  customer_name: '',
  work_location: '',
  payment_status: '',
})

const sortBy = ref('')
const sortOrder = ref<'asc' | 'desc'>('desc')

const form = reactive({
  work_date: '',
  aerial_vehicle_id: '',
  personnel_id: '',
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
  personnel_wage_amount: 0,
  remark: '',
})

async function fetchData() {
  loading.value = true
  try {
    const params: AerialQueryParams = { page: page.value, page_size: pageSize.value }
    if (filters.dateRange?.length === 2) {
      params.date_from = filters.dateRange[0]
      params.date_to = filters.dateRange[1]
    }
    if (filters.personnel_id) params.personnel_id = filters.personnel_id
    if (filters.customer_name) params.customer_name = filters.customer_name
    if (filters.work_location) params.work_location = filters.work_location
    if (filters.payment_status) params.payment_status = filters.payment_status
    if (sortBy.value) {
      params.sort_by = sortBy.value
      params.sort_order = sortOrder.value
    }
    const res = await getAerialLedgers(params)
    list.value = res.items || []
    total.value = res.total || 0
    summary.value = res.summary || null
  } catch (error: unknown) {
    ElMessage.error(getErrorMessage(error, '加载失败'))
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.dateRange = []
  filters.personnel_id = ''
  filters.customer_name = ''
  filters.work_location = ''
  filters.payment_status = ''
  sortBy.value = ''
  sortOrder.value = 'desc'
  page.value = 1
  fetchData()
}

function handleSortChange({ prop, order }: { prop: string; order: 'ascending' | 'descending' | null }) {
  if (order) {
    sortBy.value = prop
    sortOrder.value = order === 'ascending' ? 'asc' : 'desc'
  } else {
    // 第三次点击：取消排序，恢复默认（按出车日期倒序）
    sortBy.value = ''
    sortOrder.value = 'desc'
  }
  page.value = 1
  fetchData()
}

function handleCreate() {
  editingId.value = null
  Object.assign(form, {
    work_date: '', aerial_vehicle_id: '', personnel_id: '', assistant_names: '',
    customer_name: '', contact_name: '', contact_phone: '', related_order_no: '',
    work_location: '', work_type: '', work_content: '', billing_method: 'trip',
    unit_price: 0, quantity: 1, receivable_amount: 0, discount_amount: 0,
    received_amount: 0, settlement_type: 'separate', personnel_wage_amount: 0, remark: '',
  })
  dialogVisible.value = true
}

function handleEdit(row: AerialLedger) {
  editingId.value = row.id
  Object.assign(form, {
    work_date: row.work_date, aerial_vehicle_id: row.aerial_vehicle_id, personnel_id: row.personnel_id,
    assistant_names: row.assistant_names, customer_name: row.customer_name,
    contact_name: row.contact_name, contact_phone: row.contact_phone,
    related_order_no: row.related_order_no, work_location: row.work_location,
    work_type: row.work_type, work_content: row.work_content,
    billing_method: row.billing_method, unit_price: row.unit_price, quantity: row.quantity,
    receivable_amount: row.receivable_amount, discount_amount: row.discount_amount,
    received_amount: row.received_amount, settlement_type: row.settlement_type,
    personnel_wage_amount: row.personnel_wage_amount, remark: row.remark,
  })
  dialogVisible.value = true
}

async function handleSave() {
  if (!form.work_date) return ElMessage.warning('请选择出车日期')
  if (!form.aerial_vehicle_id) return ElMessage.warning('请选择高空车')
  if (!form.personnel_id) return ElMessage.warning('请选择人员')
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
  } catch (error: unknown) {
    ElMessage.error(getErrorMessage(error, '保存失败'))
  } finally {
    saving.value = false
  }
}

async function handleDetail(row: AerialLedger) {
  try {
    detailData.value = await getAerialLedger(row.id)
    detailVisible.value = true
  } catch (error: unknown) {
    ElMessage.error(getErrorMessage(error, '加载详情失败'))
  }
}

function canSettle(row: AerialLedger) {
  return !['paid', 'free', 'included_in_order'].includes(row.payment_status)
}

function paymentMethodLabel(method?: string) {
  const map: Record<string, string> = { wechat: '微信', alipay: '支付宝', bank_transfer: '银行转账', cash: '现金' }
  return method ? map[method] || method : '-'
}

function nowStr() {
  const d = new Date()
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

async function handleSettle(row: AerialLedger) {
  settleData.value = row
  settleReadonly.value = !canSettle(row)
  settlements.value = []
  settlementsLoading.value = true
  settleVisible.value = true
  try {
    settlements.value = await getAerialLedgerSettlements(row.id)
  } catch (error: unknown) {
    ElMessage.error(getErrorMessage(error, '加载结算记录失败'))
  } finally {
    settlementsLoading.value = false
  }
  settleForm.amount = row.unpaid_amount
  settleForm.payment_method = row.payment_method || ''
  settleForm.payment_time = nowStr()
  settleForm.payee_id = ''
  settleForm.remark = ''
}

async function refreshSettleDialog(id: string) {
  // 结算/删除后弹窗不关闭：重新拉台账聚合与结算记录，并重置表单
  const updated = await getAerialLedger(id)
  settleData.value = updated
  settleReadonly.value = !canSettle(updated)
  settlementsLoading.value = true
  try {
    settlements.value = await getAerialLedgerSettlements(id)
  } catch (error: unknown) {
    ElMessage.error(getErrorMessage(error, '加载结算记录失败'))
  } finally {
    settlementsLoading.value = false
  }
  settleForm.amount = updated.unpaid_amount
  settleForm.payment_method = updated.payment_method || ''
  settleForm.payment_time = nowStr()
  settleForm.payee_id = ''
  settleForm.remark = ''
}

async function handleSettleSubmit() {
  if (!settleData.value) return
  if (!settleForm.amount || settleForm.amount <= 0) return ElMessage.warning('请输入本次收款金额')
  if (!settleForm.payment_method) return ElMessage.warning('请选择收款方式')
  settling.value = true
  try {
    await settleAerialLedger(settleData.value.id, {
      amount: settleForm.amount,
      payment_method: settleForm.payment_method,
      payment_time: settleForm.payment_time,
      payee_id: settleForm.payee_id || undefined,
      remark: settleForm.remark,
    })
    ElMessage.success('结算成功')
    // 结算成功后不关闭弹窗，刷新聚合与记录后由用户手动关闭
    await refreshSettleDialog(settleData.value.id)
    fetchData()
  } catch (error: unknown) {
    ElMessage.error(getErrorMessage(error, '结算失败'))
  } finally {
    settling.value = false
  }
}

async function handleDeleteSettlement(row: AerialSettlement) {
  if (!settleData.value) return
  try {
    await ElMessageBox.confirm(
      `删除该笔收款记录后，台账已收金额将减少 ¥${row.amount}，确定删除？`,
      '删除确认',
      { type: 'warning' },
    )
    await deleteAerialLedgerSettlement(settleData.value.id, row.id)
    ElMessage.success('删除成功')
    await refreshSettleDialog(settleData.value.id)
    fetchData()
  } catch {}
}

async function handleDelete(row: AerialLedger) {
  try {
    await ElMessageBox.confirm('删除后不可恢复，确定删除该台账？', '删除确认', { type: 'warning' })
    await deleteAerialLedger(row.id)
    ElMessage.success('删除成功')
    fetchData()
  } catch {}
}

async function handleExport() {
  if (!filters.dateRange?.length) return ElMessage.warning('请先选择日期范围')
  try {
    await exportAerialLedgers(filters.dateRange[0], filters.dateRange[1])
    ElMessage.success('导出成功')
  } catch (error: unknown) {
    ElMessage.error(getErrorMessage(error, '导出失败'))
  }
}

function fmtMoney(v: number | string | null | undefined) {
  return Number(v || 0).toFixed(2)
}

type SummaryColumn = { property?: string }

function summaryMethod({ columns }: { columns: SummaryColumn[] }) {
  const s = summary.value
  return columns.map((col, i) => {
    if (i === 0) return `合计${s ? `（${s.trip_count} 条）` : ''}`
    if (col.property === 'quantity') return s ? s.quantity : 0
    if (col.property === 'receivable_amount') return s ? `¥${fmtMoney(s.receivable_amount)}` : '¥0.00'
    if (col.property === 'received_amount') return s ? `¥${fmtMoney(s.received_amount)}` : '¥0.00'
    if (col.property === 'unpaid_amount') return s ? `¥${fmtMoney(s.unpaid_amount)}` : '¥0.00'
    return ''
  })
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

async function loadOptions() {
  try {
    const [v, d, locs] = await Promise.all([
      getAerialVehicles({ page_size: 100 }),
      getAerialPersonnel({ page_size: 100 }),
      getAerialLedgerLocations(),
    ])
    vehicleOptions.value = v.items || []
    personnelOptions.value = d.items || []
    locationOptions.value = locs || []
  } catch {}
}

onMounted(() => {
  loadOptions()
  fetchData()
})
</script>

<style scoped>
.page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; color: var(--ad-text); }
.ledger-actions { display: flex; gap: 8px; }
.filter-card { background: var(--ad-card); border: 1px solid var(--ad-border); color: var(--ad-text); margin-bottom: 16px; }
/* 排序箭头与表头文字同行：收窄 caret、表头不换行，避免 4 字表头被箭头挤到两行 */
.el-table :deep(th.el-table__cell .caret-wrapper) { width: 12px; }
.el-table :deep(th.el-table__cell .cell) { white-space: nowrap; }
/* 操作列 4 个 link 按钮收窄间距，保持单行不换行 */
.el-table :deep(td .el-button + .el-button) { margin-left: 6px; }
</style>
