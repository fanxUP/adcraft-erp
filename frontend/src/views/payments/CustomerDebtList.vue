<template>
  <div class="page">
    <div class="page-header">
      <h2>客户欠款列表</h2>
      <el-button type="primary" @click="fetchData">刷新</el-button>
    </div>

    <el-table :data="list" v-loading="loading" stripe style="margin-top: 16px">
      <el-table-column prop="customer_name" label="客户名称" min-width="200" />
      <el-table-column label="欠款金额" width="180">
        <template #default="{ row }">
          <span style="color: #e63946; font-weight: bold">¥ {{ row.debt_amount?.toFixed(2) }}</span>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getCustomerDebt } from '@/api/payments'

const loading = ref(false)
const list = ref<any[]>([])

async function fetchData() {
  loading.value = true
  try {
    list.value = await getCustomerDebt()
  } finally { loading.value = false }
}

onMounted(fetchData)
</script>

<style scoped>
.page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; color: var(--ad-text); }
</style>
