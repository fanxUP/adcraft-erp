<template>
  <div class="page">
    <div class="page-header">
      <h2>支出管理</h2>
      <el-button type="danger" @click="openCreate">登记支出</el-button>
    </div>

    <div class="search-bar">
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
      <el-button style="margin-left: 12px" @click="fetchData">搜索</el-button>
    </div>

    <el-table :data="list" v-loading="loading" stripe style="margin-top: 16px">
      <el-table-column prop="expense_no" label="编号" width="180" />
      <el-table-column prop="category" label="分类" width="120">
        <template #default="{ row }">
          <el-tag v-if="row.category" size="small">{{ row.category }}</el-tag>
          <span v-else class="muted">-</span>
        </template>
      </el-table-column>
      <el-table-column label="金额" width="140">
        <template #default="{ row }">¥ {{ row.amount?.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column label="日期" width="120">
        <template #default="{ row }">{{ row.expense_date?.slice(0, 10) || '-' }}</template>
      </el-table-column>
      <el-table-column prop="description" label="说明" min-width="200" show-overflow-tooltip />
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" size="small" @click="openEdit(row as ExpenseResponse)">编辑</el-button>
          <el-button v-if="authStore.isAdmin" text type="danger" size="small" @click="handleDelete(row as ExpenseResponse)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :page-sizes="[10, 20, 50, 100]"
      :total="total"
      layout="total, sizes, prev, pager, next"
      style="margin-top: 16px; justify-content: flex-end"
      @change="fetchData"
    />

    <el-dialog v-model="showDialog" :title="isEditing ? '编辑支出' : '登记支出'" width="480px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="分类">
          <el-select v-model="form.category" placeholder="选择分类" clearable style="width: 100%">
            <el-option v-for="c in CATEGORIES" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="金额">
          <el-input-number v-model="form.amount" :min="0.01" :precision="2" style="width: 100%" />
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
        <el-button type="danger" :loading="saving" @click="handleSave">{{ isEditing ? '保存' : '登记' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getExpenses, createExpense, updateExpense, deleteExpense } from '@/api/payments'
import { useAuthStore } from '@/stores/auth'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { ExpenseResponse } from '@/types/api'

const authStore = useAuthStore()

const CATEGORIES = ['房租', '水电', '材料采购', '外协加工', '运输', '办公', '工资', '税费', '其他']

const loading = ref(false)
const saving = ref(false)
const list = ref<ExpenseResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const filterCategory = ref('')
const dateRange = ref<string[] | null>(null)
const showDialog = ref(false)
const isEditing = ref(false)
const editingId = ref('')
const form = reactive({ category: '', amount: 0, expense_date: '', description: '' })

function resetForm() {
  Object.assign(form, { category: '', amount: 0, expense_date: '', description: '' })
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
  form.expense_date = row.expense_date?.slice(0, 10) || ''
  form.description = row.description || ''
  showDialog.value = true
}

async function fetchData() {
  loading.value = true
  try {
    const params = {
      page: page.value, page_size: pageSize.value,
      ...(filterCategory.value ? { category: filterCategory.value } : {}),
      ...(dateRange.value ? { start_date: dateRange.value[0], end_date: dateRange.value[1] } : {}),
    }
    const data = await getExpenses(params)
    list.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  saving.value = true
  try {
    if (isEditing.value) {
      const payload = {
        ...(form.category ? { category: form.category } : {}),
        ...(form.amount > 0 ? { amount: form.amount } : {}),
        ...(form.expense_date ? { expense_date: form.expense_date } : {}),
        ...(form.description ? { description: form.description } : {}),
      }
      await updateExpense(editingId.value, payload)
      ElMessage.success('支出已更新')
    } else {
      await createExpense({ ...form })
      ElMessage.success('支出登记成功')
    }
    showDialog.value = false
    resetForm()
    fetchData()
  } catch { /* handled by interceptor */ }
  finally { saving.value = false }
}

async function handleDelete(row: ExpenseResponse) {
  try {
    await ElMessageBox.confirm(`确定删除支出「${row.expense_no}」吗？`, '确认删除', {
      confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning',
    })
    await deleteExpense(row.id)
    ElMessage.success('已删除')
    fetchData()
  } catch { /* cancelled or error */ }
}

onMounted(fetchData)
</script>

<style scoped>
.page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; color: var(--ad-text); }
.search-bar { display: flex; align-items: center; }
.muted { color: var(--ad-text-secondary, #888); }
</style>
