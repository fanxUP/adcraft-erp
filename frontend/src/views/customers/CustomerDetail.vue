<template>
  <div class="page">
    <el-button text @click="$router.back()">
      <el-icon><ArrowLeft /></el-icon> 返回
    </el-button>

    <div v-if="customer" class="detail" v-loading="loading">
      <el-card class="info-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span>基本信息</span>
            <el-button text type="primary" @click="handleEdit">编辑</el-button>
          </div>
        </template>
        <el-descriptions :column="2">
          <el-descriptions-item label="客户编号">{{ customer.customer_no }}</el-descriptions-item>
          <el-descriptions-item label="客户名称">{{ customer.name }}</el-descriptions-item>
          <el-descriptions-item label="类型">{{ customer.customer_type || '-' }}</el-descriptions-item>
          <el-descriptions-item label="等级">{{ customer.level || '-' }}</el-descriptions-item>
          <el-descriptions-item label="电话">{{ customer.phone || '-' }}</el-descriptions-item>
          <el-descriptions-item label="地址">{{ customer.address || '-' }}</el-descriptions-item>
          <el-descriptions-item label="备注" :span="2">{{ customer.remark || '-' }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card class="info-card" shadow="never" style="margin-top: 16px">
        <template #header>
          <span>联系人</span>
        </template>
        <el-table :data="customer.contacts" stripe size="small">
          <el-table-column prop="name" label="姓名" />
          <el-table-column prop="phone" label="电话" />
          <el-table-column prop="position" label="职位" />
          <el-table-column prop="is_primary" label="首要" width="80">
            <template #default="{ row }">
              <el-tag v-if="row.is_primary" type="danger" size="small">是</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>

    <el-dialog v-model="dialogVisible" title="编辑客户" width="600px">
      <el-form :model="editForm" label-width="100px">
        <el-form-item label="客户名称">
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="editForm.customer_type" clearable style="width: 100%">
            <el-option label="直客" value="直客" />
            <el-option label="代理" value="代理" />
            <el-option label="同行" value="同行" />
          </el-select>
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="editForm.phone" />
        </el-form-item>
        <el-form-item label="地址">
          <el-input v-model="editForm.address" />
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
import { useRoute } from 'vue-router'
import { getCustomer, updateCustomer } from '@/api/customers'
import type { CustomerResponse } from '@/types/api'
import { ElMessage } from 'element-plus'

const route = useRoute()
const loading = ref(false)
const saving = ref(false)
const customer = ref<CustomerResponse | null>(null)
const dialogVisible = ref(false)
const editForm = reactive({ name: '', customer_type: '', level: '', phone: '', address: '' })

async function fetchData() {
  loading.value = true
  try {
    customer.value = await getCustomer(route.params.id as string)
  } finally {
    loading.value = false
  }
}

function handleEdit() {
  if (!customer.value) return
  Object.assign(editForm, {
    name: customer.value.name,
    customer_type: customer.value.customer_type,
    level: customer.value.level,
    phone: customer.value.phone,
    address: customer.value.address,
  })
  dialogVisible.value = true
}

async function handleSave() {
  saving.value = true
  try {
    await updateCustomer(route.params.id as string, editForm)
    ElMessage.success('更新成功')
    dialogVisible.value = false
    fetchData()
  } finally {
    saving.value = false
  }
}

onMounted(fetchData)
</script>

<style scoped>
.page { padding: 0; }
.detail { margin-top: 16px; }
.info-card { background: var(--ad-card); border: 1px solid var(--ad-border); color: var(--ad-text); }
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
