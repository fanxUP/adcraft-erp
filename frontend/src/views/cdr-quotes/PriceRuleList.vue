<template>
  <div class="page">
    <div class="page-header">
      <h2>定价规则管理</h2>
      <el-button type="danger" @click="createDialogVisible = true">新建规则集</el-button>
    </div>

    <el-table :data="ruleSets" v-loading="loading" stripe>
      <el-table-column prop="code" label="编码" width="150" />
      <el-table-column prop="name" label="名称" min-width="200" />
      <el-table-column prop="version" label="版本" width="80" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'published' ? 'success' : row.status === 'archived' ? 'info' : 'warning'">
            {{ { draft: '草稿', published: '已发布', archived: '已归档' }[row.status] || row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="effective_from" label="生效日期" width="120" />
      <el-table-column prop="effective_to" label="失效日期" width="120" />
      <el-table-column prop="description" label="说明" min-width="200" />
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" @click="viewRules(row)">查看规则</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新建规则集弹窗 -->
    <el-dialog v-model="createDialogVisible" title="新建规则集" width="600px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="编码" required>
          <el-input v-model="form.code" placeholder="如：PVC-PRICE-2026" />
        </el-form-item>
        <el-form-item label="名称" required>
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="生效日期">
          <el-input v-model="form.effective_from" placeholder="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="失效日期">
          <el-input v-model="form.effective_to" placeholder="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="danger" @click="handleCreate" :loading="submitting">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { listRuleSets, createRuleSet } from '@/api/cdrQuote'

const loading = ref(false)
const submitting = ref(false)
const ruleSets = ref<any[]>([])
const createDialogVisible = ref(false)
const form = ref({
  code: '',
  name: '',
  effective_from: '',
  effective_to: '',
  description: '',
})

async function fetchData() {
  loading.value = true
  try {
    ruleSets.value = await listRuleSets()
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  if (!form.value.code || !form.value.name) {
    ElMessage.warning('请填写必填项')
    return
  }
  submitting.value = true
  try {
    await createRuleSet({ ...form.value })
    ElMessage.success('创建成功')
    createDialogVisible.value = false
    form.value = { code: '', name: '', effective_from: '', effective_to: '', description: '' }
    await fetchData()
  } finally {
    submitting.value = false
  }
}

function viewRules() {
  ElMessage.info('规则详情功能将在后续版本完善')
}

onMounted(fetchData)
</script>
