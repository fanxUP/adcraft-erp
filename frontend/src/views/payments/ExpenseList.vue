<template>
  <AppPage>
    <template #header>
      <PageHeader title="支出管理" description="统一登记和维护经营支出，金额与日期格式保持一致。">
        <template #actions><el-button @click="openCreate" type="danger">登记支出</el-button></template>
      </PageHeader>
    </template>

    <template #toolbar>
      <PageToolbar aria-label="支出筛选">
      <el-select v-model="filterCategory" placeholder="支出分类" clearable style="width: 160px" @change="fetchData">
        <el-option v-for="c in CATEGORIES" :key="c" :label="c" :value="c" />
      </el-select>
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        value-format="YYYY-MM-DD"
        style="width: 260px; margin-left: 12px"
        @change="fetchData"
      />
      <el-button style="margin-left: 12px" @click="fetchData" type="primary">搜索</el-button>
      </PageToolbar>
    </template>

    <DataTableShell :state="tableState" aria-label="支出列表">
      <template #error><StatePanel state="error" action-label="重试" @action="fetchData" /></template>
      <el-table :data="list" stripe>
      <el-table-column prop="expense_no" label="编号" width="180" />
      <el-table-column prop="category" label="分类" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.category" size="small">{{ row.category }}</el-tag>
          <span v-else class="muted">-</span>
        </template>
      </el-table-column>
      <el-table-column label="金额" width="120">
        <template #default="{ row }">{{ formatMoney(row.amount) }}</template>
      </el-table-column>
      <el-table-column label="供应商/应付对象" min-width="180" show-overflow-tooltip>
        <template #default="{ row }">{{ row.supplier_name || row.payee_name || '-' }}</template>
      </el-table-column>
      <el-table-column label="待付款" width="120" align="right">
        <template #default="{ row }">
          <span :class="{ 'text-warning': row.payable_amount > 0 }">{{ formatMoney(row.payable_amount) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="日期" width="120">
        <template #default="{ row }">{{ formatDate(row.expense_date) || '-' }}</template>
      </el-table-column>
      <el-table-column prop="description" label="说明" min-width="180" show-overflow-tooltip />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" size="small" @click="openEdit(row as ExpenseResponse)">编辑</el-button>
          <el-button v-if="authStore.isAdmin" text type="danger" size="small" @click="handleDelete(row as ExpenseResponse)">删除</el-button>
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

    <el-dialog v-model="showDialog" :title="isEditing ? '编辑支出' : '登记支出'" width="480px" :close-on-click-modal="false">
      <el-form :model="form" label-width="100px">
        <el-form-item label="分类">
          <el-select v-model="form.category" placeholder="选择分类" clearable style="width: 100%">
            <el-option v-for="c in CATEGORIES" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="金额">
          <el-input-number v-model="form.amount" :min="isEditing ? 0.01 : 0" :precision="2" style="width: 100%" />
          <div class="form-tip">可以先填写待付款金额；如果金额留空，系统会按待付款金额作为支出总额。</div>
        </el-form-item>
        <el-form-item v-if="canUseSupplier" label="供应商">
          <el-select
            v-model="form.supplier_id"
            clearable
            filterable
            placeholder="选择供应商（可选）"
            style="width: 100%"
            @change="handleSupplierChange"
          >
            <el-option v-for="supplier in suppliers" :key="supplier.id" :label="supplier.name" :value="supplier.id" />
          </el-select>
          <div class="form-tip">选择后会自动带入应付对象；非供应商支出仍可直接填写下方文本。</div>
        </el-form-item>
        <el-form-item label="应付对象">
          <el-input v-model="form.payee_name" placeholder="供应商、房东或其他收款对象" />
        </el-form-item>
        <el-form-item label="待付款金额">
          <el-input-number v-model="form.payable_amount" :min="0" :precision="2" style="width: 100%" />
          <div class="form-tip">不需要形成应付时填 0；同时填写金额时，待付款金额不能超过支出总额。</div>
        </el-form-item>
        <el-form-item label="日期">
          <el-date-picker v-model="form.expense_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="支出说明…" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button :loading="saving" @click="handleSave" type="primary">{{ isEditing ? '保存' : '登记' }}</el-button>
      </template>
    </el-dialog>
  </AppPage>
</template>

<script setup lang="ts">
import { formatDate } from '@/utils/datetime'
import { formatMoney } from '@/utils/format'
import { ref, reactive, computed, onMounted } from 'vue'
import { getExpenses, createExpense, updateExpense, deleteExpense } from '@/api/payments'
import { getSuppliers } from '@/api/suppliers'
import { useAuthStore } from '@/stores/auth'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { ExpenseResponse, SupplierResponse } from '@/types/api'
import { normalizeExpenseAmounts, type ExpenseAmountResult } from '@/utils/expenseAmount'
import { AppPage, DataTableShell, PageHeader, PageToolbar, StatePanel } from '@/components/ui'

const authStore = useAuthStore()
const canUseSupplier = computed(() => authStore.can('supplier:read'))

const CATEGORIES = ['房租', '水电', '材料采购', '外协加工', '运输', '办公', '工资', '税费', '其他']

const loading = ref(false)
const saving = ref(false)
const list = ref<ExpenseResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loadError = ref(false)
const filterCategory = ref('')
const dateRange = ref<string[] | null>(null)
const suppliers = ref<SupplierResponse[]>([])
const showDialog = ref(false)
const isEditing = ref(false)
const editingId = ref('')
const form = reactive({ category: '', amount: 0, supplier_id: '', payee_name: '', payable_amount: 0, expense_date: '', description: '' })

const tableState = computed<'loading' | 'empty' | 'error' | 'ready'>(() => {
  if (loadError.value) return 'error'
  if (loading.value) return 'loading'
  return list.value.length ? 'ready' : 'empty'
})

function resetForm() {
  Object.assign(form, { category: '', amount: 0, supplier_id: '', payee_name: '', payable_amount: 0, expense_date: '', description: '' })
  isEditing.value = false
  editingId.value = ''
}

function openCreate() {
  resetForm()
  showDialog.value = true
}

function openEdit(row: ExpenseResponse) {
  isEditing.value = true
  editingId.value = row.id
  form.category = row.category || ''
  form.amount = row.amount
  form.supplier_id = row.supplier_id || ''
  form.payee_name = row.payee_name || ''
  form.payable_amount = row.payable_amount || 0
  form.expense_date = formatDate(row.expense_date) || ''
  form.description = row.description || ''
  showDialog.value = true
}

function handleSupplierChange(supplierId: string | undefined) {
  const supplier = suppliers.value.find(item => item.id === supplierId)
  if (supplier) form.payee_name = supplier.name
}

async function fetchSuppliers() {
  if (!canUseSupplier.value) return
  try {
    const data = await getSuppliers({ page: 1, page_size: 200, is_active: true })
    suppliers.value = data.items
  } catch {
    // The legacy free-text payee field remains available when the directory is unavailable.
  }
}

async function fetchData() {
  loading.value = true
  loadError.value = false
  try {
    const params = {
      page: page.value, page_size: pageSize.value,
      ...(filterCategory.value ? { category: filterCategory.value } : {}),
      ...(dateRange.value ? { start_date: dateRange.value[0], end_date: dateRange.value[1] } : {}),
    }
    const data = await getExpenses(params)
    list.value = data.items
    total.value = data.total
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  let normalizedAmounts: ExpenseAmountResult | undefined
  if (!isEditing.value) {
    try {
      normalizedAmounts = normalizeExpenseAmounts(form.amount, form.payable_amount)
    } catch (error) {
      ElMessage.error(error instanceof Error ? error.message : '请填写有效的支出金额')
      return
    }
  }

  saving.value = true
  try {
    if (isEditing.value) {
      const payload = {
        ...(form.category ? { category: form.category } : {}),
        ...(form.amount > 0 ? { amount: form.amount } : {}),
        supplier_id: form.supplier_id || null,
        payee_name: form.payee_name,
        payable_amount: form.payable_amount,
        ...(form.expense_date ? { expense_date: form.expense_date } : {}),
        ...(form.description ? { description: form.description } : {}),
      }
      await updateExpense(editingId.value, payload)
      ElMessage.success('支出已更新')
    } else {
      await createExpense({
        ...form,
        amount: normalizedAmounts!.amount,
        payable_amount: normalizedAmounts!.payable_amount,
        supplier_id: form.supplier_id || undefined,
      })
      ElMessage.success('支出登记成功')
    }
    showDialog.value = false
    resetForm()
    fetchData()
  } catch {
    // API error handled by interceptor, cancel does nothing
  } finally { saving.value = false }
}

async function handleDelete(row: ExpenseResponse) {
  try {
    await ElMessageBox.confirm(`确定删除支出「${row.expense_no}」吗？`, '确认删除', {
      confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning',
    })
    await deleteExpense(row.id)
    ElMessage.success('已删除')
    fetchData()
  } catch {
    // User cancelled or API error (handled by interceptor)
  }
}

onMounted(() => {
  void fetchData()
  void fetchSuppliers()
})
</script>

<style scoped>
.muted { color: var(--ad-text-secondary, #888); }
.text-warning { color: var(--el-color-warning); font-weight: 600; }
.form-tip { color: var(--ad-text-secondary, #888); font-size: 12px; line-height: 1.5; }
</style>
