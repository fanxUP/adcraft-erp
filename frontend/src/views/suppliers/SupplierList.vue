<template>
  <AppPage>
    <template #header>
      <PageHeader title="供应商管理" description="统一维护外协、材料、设备、运输和其他服务供应商，并作为成本与应付台账的基础资料。">
        <template #actions>
          <el-button v-if="canCreate" type="primary" @click="openCreate">新建供应商</el-button>
        </template>
      </PageHeader>
    </template>

    <template #toolbar>
      <PageToolbar aria-label="供应商筛选">
        <el-input
          v-model="filters.keyword"
          clearable
          placeholder="名称、简称、联系人或税号"
          style="width: 260px"
          @keyup.enter="handleSearch"
        />
        <el-select
          v-model="filters.supplier_type"
          clearable
          placeholder="供应商类型"
          style="width: 160px"
          @change="handleSearch"
        >
          <el-option v-for="option in supplierTypeOptions" :key="option.value" :label="option.label" :value="option.value" />
        </el-select>
        <el-checkbox v-model="filters.includeInactive" @change="handleSearch">显示停用</el-checkbox>
        <el-button type="primary" @click="handleSearch">搜索</el-button>
        <el-button @click="handleReset">重置</el-button>
      </PageToolbar>
    </template>

    <DataTableShell :state="tableState" aria-label="供应商列表">
      <template #error><StatePanel state="error" action-label="重新加载" @action="fetchData" /></template>
      <el-table :data="list" row-key="id" stripe>
        <el-table-column prop="vendor_no" label="编号" width="170" />
        <el-table-column label="供应商名称" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="supplier-name">{{ row.name }}</div>
            <div v-if="row.short_name" class="supplier-short-name">{{ row.short_name }}</div>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="140">
          <template #default="{ row }">{{ supplierTypeLabel(row.supplier_type) }}</template>
        </el-table-column>
        <el-table-column prop="contact_person" label="联系人" width="120">
          <template #default="{ row }">{{ row.contact_person || '-' }}</template>
        </el-table-column>
        <el-table-column prop="phone" label="联系电话" width="145">
          <template #default="{ row }">{{ row.phone || '-' }}</template>
        </el-table-column>
        <el-table-column label="结算方式" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">
            {{ settlementLabel(row) }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="openDetail(row)">详情</el-button>
            <el-button v-if="canUpdate" text type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button v-if="canUpdate && row.is_active" text type="warning" size="small" @click="handleDeactivate(row)">停用</el-button>
            <el-button v-if="canUpdate && !row.is_active" text type="success" size="small" @click="handleActivate(row)">启用</el-button>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next"
          @change="fetchData"
        />
      </template>
    </DataTableShell>

    <el-dialog v-model="showEditor" :title="editingId ? '编辑供应商' : '新建供应商'" width="760px" :close-on-click-modal="false">
      <el-form :model="form" label-width="100px">
        <div class="form-grid">
          <el-form-item label="供应商名称" required>
            <el-input v-model="form.name" maxlength="255" show-word-limit placeholder="请输入完整名称" />
          </el-form-item>
          <el-form-item label="简称">
            <el-input v-model="form.short_name" maxlength="128" placeholder="列表展示用简称（可选）" />
          </el-form-item>
          <el-form-item label="供应商类型">
            <el-select v-model="form.supplier_type" style="width: 100%">
              <el-option v-for="option in supplierTypeOptions" :key="option.value" :label="option.label" :value="option.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="联系人">
            <el-input v-model="form.contact_person" placeholder="联系人姓名" />
          </el-form-item>
          <el-form-item label="联系电话">
            <el-input v-model="form.phone" placeholder="手机或座机" />
          </el-form-item>
          <el-form-item label="电子邮箱">
            <el-input v-model="form.email" placeholder="电子邮箱（可选）" />
          </el-form-item>
          <el-form-item label="统一税号">
            <el-input v-model="form.tax_id" placeholder="统一社会信用代码（可选）" />
          </el-form-item>
          <el-form-item label="税率">
            <el-input-number v-model="form.tax_rate" :min="0" :max="100" :precision="2" controls-position="right" style="width: 100%" />
          </el-form-item>
          <el-form-item label="结算方式">
            <el-select v-model="form.settlement_method" clearable allow-create filterable style="width: 100%">
              <el-option v-for="method in settlementMethods" :key="method" :label="method" :value="method" />
            </el-select>
          </el-form-item>
          <el-form-item label="账期（天）">
            <el-input-number v-model="form.settlement_days" :min="0" :max="3650" controls-position="right" style="width: 100%" />
          </el-form-item>
          <el-form-item label="服务类型">
            <el-input v-model="form.service_type" placeholder="外协服务的具体类型（可选）" />
          </el-form-item>
          <el-form-item label="合作评级">
            <el-select v-model="form.coop_rating" clearable style="width: 100%">
              <el-option label="A" value="A" />
              <el-option label="B" value="B" />
              <el-option label="C" value="C" />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item label="地址">
          <el-input v-model="form.address" placeholder="供应商地址（可选）" />
        </el-form-item>
        <el-form-item v-if="canBankRead" label="收款账户">
          <div class="bank-grid">
            <el-input v-model="form.bank_name" :disabled="!canBankUpdate" placeholder="开户行" />
            <el-input v-model="form.bank_account" :disabled="!canBankUpdate" placeholder="银行账号" />
          </div>
          <div v-if="!canBankUpdate" class="form-tip">当前角色只能查看收款账户，不能修改。</div>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="3" maxlength="1000" show-word-limit placeholder="合作说明、付款约定或其他备注" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditor = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showDetail" title="供应商详情" width="680px" :close-on-click-modal="false">
      <div v-loading="detailLoading" class="detail-content">
        <template v-if="detail">
          <div class="detail-title-row">
            <div>
              <h3>{{ detail.name }}</h3>
              <span v-if="detail.short_name" class="supplier-short-name">{{ detail.short_name }}</span>
            </div>
            <el-tag :type="detail.is_active ? 'success' : 'info'" size="small">{{ detail.is_active ? '启用' : '停用' }}</el-tag>
          </div>
          <div class="detail-grid">
            <div><span class="detail-label">编号</span>{{ detail.vendor_no }}</div>
            <div><span class="detail-label">类型</span>{{ supplierTypeLabel(detail.supplier_type) }}</div>
            <div><span class="detail-label">联系人</span>{{ detail.contact_person || '-' }}</div>
            <div><span class="detail-label">联系电话</span>{{ detail.phone || '-' }}</div>
            <div><span class="detail-label">电子邮箱</span>{{ detail.email || '-' }}</div>
            <div><span class="detail-label">统一税号</span>{{ detail.tax_id || '-' }}</div>
            <div><span class="detail-label">结算方式</span>{{ settlementLabel(detail) }}</div>
            <div><span class="detail-label">服务类型</span>{{ detail.service_type || '-' }}</div>
            <div class="detail-grid-wide"><span class="detail-label">地址</span>{{ detail.address || '-' }}</div>
            <template v-if="canBankRead">
              <div><span class="detail-label">开户行</span>{{ detail.bank_name || '-' }}</div>
              <div><span class="detail-label">银行账号</span>{{ detail.bank_account || '-' }}</div>
            </template>
          </div>
          <div v-if="canLedgerRead && detail.stats" class="stats-panel">
            <div class="stats-panel-title">业务与应付统计</div>
            <div class="stats-grid">
              <div><span>项目成本</span><strong>{{ formatMoney(detail.stats.project_cost_amount) }}</strong><small>{{ detail.stats.project_cost_count }} 笔 · 应付总额 {{ formatMoney(detail.stats.project_cost_payable) }} · 已付 {{ formatMoney(detail.stats.project_cost_paid) }} · 待付 {{ formatMoney(detail.stats.project_cost_remaining) }}</small></div>
              <div><span>经营支出</span><strong>{{ formatMoney(detail.stats.expense_amount) }}</strong><small>{{ detail.stats.expense_count }} 笔 · 应付总额 {{ formatMoney(detail.stats.expense_payable) }} · 已付 {{ formatMoney(detail.stats.expense_paid) }} · 待付 {{ formatMoney(detail.stats.expense_remaining) }}</small></div>
              <div><span>外协任务</span><strong>{{ formatMoney(detail.stats.outsource_task_amount) }}</strong><small>{{ detail.stats.outsource_task_count }} 笔 · 未付 {{ formatMoney(detail.stats.outsource_task_unpaid) }}</small></div>
            </div>
          </div>
          <div v-if="detail.remark" class="remark-panel"><span class="detail-label">备注</span>{{ detail.remark }}</div>
        </template>
        <el-empty v-else-if="!detailLoading" description="暂无供应商资料" />
      </div>
      <template #footer>
        <el-button @click="showDetail = false">关闭</el-button>
        <el-button v-if="detail && canUpdate" type="primary" @click="openEdit(detail); showDetail = false">编辑</el-button>
      </template>
    </el-dialog>
  </AppPage>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { AppPage, DataTableShell, PageHeader, PageToolbar, StatePanel } from '@/components/ui'
import { createSupplier, deactivateSupplier, getSupplier, getSuppliers, updateSupplier, type SupplierPayload } from '@/api/suppliers'
import { useAuthStore } from '@/stores/auth'
import { formatMoney } from '@/utils/format'
import type { SupplierResponse } from '@/types/api'

const authStore = useAuthStore()
const canCreate = computed(() => authStore.can('supplier:create'))
const canUpdate = computed(() => authStore.can('supplier:update'))
const canBankRead = computed(() => authStore.can('supplier:bank:view'))
const canBankUpdate = computed(() => authStore.can('supplier:bank:edit'))
const canLedgerRead = computed(() => authStore.can('supplier:ledger:read'))

const supplierTypeOptions = [
  { value: 'outsource', label: '外协服务' },
  { value: 'material', label: '材料供应商' },
  { value: 'equipment', label: '设备供应商' },
  { value: 'transport', label: '运输服务' },
  { value: 'service', label: '其他服务' },
  { value: 'other', label: '其他供应商' },
]
const settlementMethods = ['现结', '周结', '月结', '按合同结算']

const loading = ref(false)
const saving = ref(false)
const loadError = ref(false)
const list = ref<SupplierResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filters = reactive({ keyword: '', supplier_type: '', includeInactive: false })
const showEditor = ref(false)
const editingId = ref('')
const showDetail = ref(false)
const detailLoading = ref(false)
const detail = ref<SupplierResponse | null>(null)

const emptyForm = (): SupplierPayload => ({
  name: '',
  short_name: '',
  supplier_type: 'other',
  contact_person: '',
  phone: '',
  email: '',
  address: '',
  tax_id: '',
  bank_name: '',
  bank_account: '',
  tax_rate: undefined,
  settlement_method: '',
  settlement_days: undefined,
  service_type: '',
  coop_rating: '',
  remark: '',
})
const form = reactive<SupplierPayload>(emptyForm())

const tableState = computed<'loading' | 'empty' | 'error' | 'ready'>(() => {
  if (loadError.value) return 'error'
  if (loading.value) return 'loading'
  return list.value.length ? 'ready' : 'empty'
})

function supplierTypeLabel(value?: string | null) {
  return supplierTypeOptions.find(option => option.value === value)?.label || value || '-'
}

function settlementLabel(row: Pick<SupplierResponse, 'settlement_method' | 'settlement_days'>) {
  const method = row.settlement_method || ''
  if (!method && row.settlement_days == null) return '-'
  return `${method || '账期'}${row.settlement_days != null ? ` · ${row.settlement_days}天` : ''}`
}

async function fetchData() {
  loading.value = true
  loadError.value = false
  try {
    const data = await getSuppliers({
      page: page.value,
      page_size: pageSize.value,
      keyword: filters.keyword.trim() || undefined,
      supplier_type: filters.supplier_type || undefined,
      is_active: filters.includeInactive ? undefined : true,
    })
    list.value = data.items
    total.value = data.total
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  void fetchData()
}

function handleReset() {
  filters.keyword = ''
  filters.supplier_type = ''
  filters.includeInactive = false
  page.value = 1
  void fetchData()
}

function openCreate() {
  editingId.value = ''
  Object.assign(form, emptyForm())
  showEditor.value = true
}

function openEdit(row: SupplierResponse) {
  editingId.value = row.id
  Object.assign(form, {
    ...emptyForm(),
    name: row.name,
    short_name: row.short_name || '',
    supplier_type: row.supplier_type || 'other',
    contact_person: row.contact_person || '',
    phone: row.phone || '',
    email: row.email || '',
    address: row.address || '',
    tax_id: row.tax_id || '',
    bank_name: row.bank_name || '',
    bank_account: row.bank_account || '',
    tax_rate: row.tax_rate ?? undefined,
    settlement_method: row.settlement_method || '',
    settlement_days: row.settlement_days ?? undefined,
    service_type: row.service_type || '',
    coop_rating: row.coop_rating || '',
    remark: row.remark || '',
  })
  showEditor.value = true
}

async function handleSave() {
  const name = form.name?.trim()
  if (!name) {
    ElMessage.warning('请输入供应商名称')
    return
  }
  saving.value = true
  try {
    const payload = { ...form, name }
    if (editingId.value) {
      await updateSupplier(editingId.value, payload)
      ElMessage.success('供应商已更新')
    } else {
      await createSupplier(payload)
      ElMessage.success('供应商已创建')
    }
    showEditor.value = false
    await fetchData()
  } catch {
    // API interceptor shows the business error.
  } finally {
    saving.value = false
  }
}

async function openDetail(row: SupplierResponse) {
  showDetail.value = true
  detail.value = null
  detailLoading.value = true
  try {
    detail.value = await getSupplier(row.id)
  } catch {
    // API interceptor shows the business error.
  } finally {
    detailLoading.value = false
  }
}

async function handleDeactivate(row: SupplierResponse) {
  try {
    await ElMessageBox.confirm(
      `停用供应商「${row.name}」后，历史成本仍会保留，但新的成本和支出不能再选择它。确定继续吗？`,
      '确认停用',
      { confirmButtonText: '停用', cancelButtonText: '取消', type: 'warning' },
    )
    await deactivateSupplier(row.id)
    ElMessage.success('供应商已停用')
    await fetchData()
  } catch {
    // User cancelled or API error.
  }
}

async function handleActivate(row: SupplierResponse) {
  try {
    await updateSupplier(row.id, { is_active: true })
    ElMessage.success('供应商已启用')
    await fetchData()
  } catch {
    // API interceptor shows the business error.
  }
}

onMounted(() => { void fetchData() })
</script>

<style scoped>
.form-grid,
.detail-grid,
.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 24px;
}

.bank-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; width: 100%; }
.supplier-name { color: var(--ad-text); font-weight: 600; }
.supplier-short-name,
.form-tip,
.muted { color: var(--ad-text-secondary); font-size: 12px; }
.detail-content { min-height: 220px; }
.detail-title-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 22px; }
.detail-title-row h3 { margin: 0 0 4px; color: var(--ad-text); font-size: 20px; }
.detail-grid { padding-bottom: 8px; }
.detail-grid > div { padding: 10px 0; border-bottom: 1px solid var(--ad-border); color: var(--ad-text); }
.detail-grid-wide { grid-column: 1 / -1; }
.detail-label { display: inline-block; min-width: 82px; margin-right: 8px; color: var(--ad-text-secondary); }
.stats-panel { margin-top: 20px; padding: 16px; border: 1px solid var(--ad-border); border-radius: 8px; background: var(--ad-surface-subtle, #f8fafc); }
.stats-panel-title { margin-bottom: 12px; color: var(--ad-text); font-weight: 600; }
.stats-grid { gap: 12px; }
.stats-grid > div { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.stats-grid span { color: var(--ad-text-secondary); font-size: 13px; }
.stats-grid strong { color: var(--ad-text); font-size: 18px; }
.stats-grid small { color: var(--ad-text-secondary); font-size: 12px; }
.remark-panel { margin-top: 18px; padding: 12px; border-radius: 6px; background: var(--ad-surface-subtle, #f8fafc); color: var(--ad-text); line-height: 1.6; white-space: pre-wrap; }

@media (max-width: 720px) {
  .form-grid,
  .detail-grid,
  .stats-grid,
  .bank-grid { grid-template-columns: 1fr; }
  .detail-grid-wide { grid-column: auto; }
}
</style>
