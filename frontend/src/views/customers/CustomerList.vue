<template>
  <div class="page">
    <div class="page-header">
      <h2>客户管理</h2>
      <el-button type="danger" @click="handleCreate">新建客户</el-button>
    </div>

    <div class="search-bar">
      <el-input v-model="keyword" placeholder="搜索客户名称或电话" clearable style="width: 300px" @keyup.enter="fetchData" />
      <el-select v-model="customerType" placeholder="客户类型" clearable style="width: 160px; margin-left: 12px">
        <el-option label="直客" value="直客" />
        <el-option label="代理" value="代理" />
        <el-option label="同行" value="同行" />
      </el-select>
      <el-button type="primary" @click="fetchData" style="margin-left: 12px">搜索</el-button>
    </div>

    <el-table :data="list" v-loading="loading" stripe style="margin-top: 16px">
      <el-table-column prop="customer_no" label="客户编号" width="160" />
      <el-table-column prop="name" label="客户名称" min-width="180" />
      <el-table-column label="联系人" width="120">
        <template #default="{ row }">
          {{ row.contacts?.[0]?.name || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="phone" label="电话" width="140" />
      <el-table-column prop="customer_type" label="类型" width="80" />
      <el-table-column prop="level" label="等级" width="80" />
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button text type="primary" @click="$router.push(`/customers/${row.id}`)">详情</el-button>
          <el-button text type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :total="total"
      layout="total, prev, pager, next"
      style="margin-top: 16px; justify-content: flex-end"
      @change="fetchData"
    />

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑客户' : '新建客户'" width="600px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="客户名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="客户类型">
          <el-select v-model="form.customer_type" clearable style="width: 100%">
            <el-option label="直客" value="直客" />
            <el-option label="代理" value="代理" />
            <el-option label="同行" value="同行" />
          </el-select>
        </el-form-item>
        <el-form-item label="等级">
          <el-select v-model="form.level" clearable style="width: 100%">
            <el-option label="A" value="A" />
            <el-option label="B" value="B" />
            <el-option label="C" value="C" />
          </el-select>
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="form.phone" />
        </el-form-item>
        <el-form-item label="地址">
          <el-input v-model="form.address" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getCustomers, createCustomer, updateCustomer, deleteCustomer } from '@/api/customers'
import { ElMessage, ElMessageBox } from 'element-plus'

const loading = ref(false)
const saving = ref(false)
const list = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const customerType = ref('')
const dialogVisible = ref(false)
const editingId = ref<string | null>(null)
const form = reactive({ name: '', customer_type: '', level: '', phone: '', address: '', remark: '' })

const rules = { name: [{ required: true, message: '请输入客户名称', trigger: 'blur' }] }

async function fetchData() {
  loading.value = true
  try {
    const data = await getCustomers({ page: page.value, page_size: pageSize.value, keyword: keyword.value, customer_type: customerType.value || undefined })
    list.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function handleCreate() {
  editingId.value = null
  Object.assign(form, { name: '', customer_type: '', level: '', phone: '', address: '', remark: '' })
  dialogVisible.value = true
}

async function handleSave() {
  saving.value = true
  try {
    if (editingId.value) {
      await updateCustomer(editingId.value, form)
      ElMessage.success('更新成功')
    } else {
      await createCustomer(form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchData()
  } finally {
    saving.value = false
  }
}

async function handleDelete(row: any) {
  await ElMessageBox.confirm(`确认删除客户 "${row.name}"？`, '确认', { type: 'warning' })
  await deleteCustomer(row.id)
  ElMessage.success('已删除')
  fetchData()
}

onMounted(fetchData)
</script>

<style scoped>
.page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; color: var(--ad-text); }
.search-bar { display: flex; align-items: center; }
</style>
