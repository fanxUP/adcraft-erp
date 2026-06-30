<template>
  <div class="page">
    <div class="page-header">
      <h2>外协商管理</h2>
      <el-button type="danger" @click="handleCreate">新建外协商</el-button>
    </div>

    <div class="search-bar">
      <el-input v-model="keyword" placeholder="搜索外协商名称" clearable style="width: 240px" @keyup.enter="fetchData" />
      <el-select v-model="serviceType" placeholder="服务类型" clearable style="width: 160px; margin-left: 12px">
        <el-option label="制作" value="production" />
        <el-option label="安装" value="installation" />
        <el-option label="设计" value="design" />
        <el-option label="运输" value="transport" />
      </el-select>
      <el-button type="primary" @click="fetchData" style="margin-left: 12px">搜索</el-button>
    </div>

    <el-table :data="list" v-loading="loading" stripe style="margin-top: 16px" empty-text="暂无外协商">
      <el-table-column prop="vendor_no" label="编号" width="150" />
      <el-table-column prop="name" label="名称" min-width="160" />
      <el-table-column prop="contact_person" label="联系人" width="120" />
      <el-table-column prop="phone" label="电话" width="140" />
      <el-table-column label="服务类型" width="100">
        <template #default="{ row }">
          {{ serviceTypeLabel(row.service_type) }}
        </template>
      </el-table-column>
      <el-table-column label="评级" width="80">
        <template #default="{ row }">
          <el-tag :type="row.coop_rating === 'A' ? 'success' : row.coop_rating === 'B' ? 'warning' : 'info'" size="small">
            {{ row.coop_rating || '-' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
            {{ row.is_active ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180">
        <template #default="{ row }">
          <el-button text type="primary" @click="handleEdit(row as VendorResponse)">编辑</el-button>
          <el-button text type="danger" @click="handleDelete(row as VendorResponse)">删除</el-button>
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

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑外协商' : '新建外协商'" width="550px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="联系人">
          <el-input v-model="form.contact_person" />
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="form.phone" />
        </el-form-item>
        <el-form-item label="地址">
          <el-input v-model="form.address" />
        </el-form-item>
        <el-form-item label="服务类型">
          <el-select v-model="form.service_type" clearable style="width: 100%">
            <el-option label="制作" value="production" />
            <el-option label="安装" value="installation" />
            <el-option label="设计" value="design" />
            <el-option label="运输" value="transport" />
          </el-select>
        </el-form-item>
        <el-form-item label="合作评级">
          <el-select v-model="form.coop_rating" clearable style="width: 100%">
            <el-option label="A" value="A" />
            <el-option label="B" value="B" />
            <el-option label="C" value="C" />
          </el-select>
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
import {
  getOutsourceVendors, createOutsourceVendor, updateOutsourceVendor, deleteOutsourceVendor,
} from '@/api/outsource'
import { ElMessage, ElMessageBox } from 'element-plus'
import { VendorResponse } from '@/types/api'

const loading = ref(false)
const saving = ref(false)
const list = ref<VendorResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const serviceType = ref('')
const dialogVisible = ref(false)
const editingId = ref<string | null>(null)
const form = reactive({
  name: '', contact_person: '', phone: '', address: '',
  service_type: '', coop_rating: '', remark: '',
})
const rules = { name: [{ required: true, message: '请输入外协商名称', trigger: 'blur' }] }

function serviceTypeLabel(val: string | null) {
  const map: Record<string, string> = { production: '制作', installation: '安装', design: '设计', transport: '运输' }
  return map[val || ''] || val || '-'
}

async function fetchData() {
  loading.value = true
  try {
    const data = await getOutsourceVendors({
      page: page.value, page_size: pageSize.value,
      keyword: keyword.value || undefined,
      service_type: serviceType.value || undefined,
    })
    list.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function handleCreate() {
  editingId.value = null
  Object.assign(form, { name: '', contact_person: '', phone: '', address: '', service_type: '', coop_rating: '', remark: '' })
  dialogVisible.value = true
}

function handleEdit(row: VendorResponse) {
  editingId.value = row.id
  Object.assign(form, {
    name: row.name, contact_person: row.contact_person, phone: row.phone, address: row.address,
    service_type: row.service_type, coop_rating: row.coop_rating, remark: row.remark,
  })
  dialogVisible.value = true
}

async function handleSave() {
  saving.value = true
  try {
    if (editingId.value) {
      await updateOutsourceVendor(editingId.value, form)
      ElMessage.success('更新成功')
    } else {
      await createOutsourceVendor(form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await fetchData()
  } finally {
    saving.value = false
  }
}

async function handleDelete(row: VendorResponse) {
  try {
    await ElMessageBox.confirm(`确认删除外协商 "${row.name}"？`, '确认', { type: 'warning' })
    await deleteOutsourceVendor(row.id)
    ElMessage.success('已删除')
    await fetchData()
  } catch {
    // User cancelled or API error (handled by interceptor)
  }
}

onMounted(fetchData)
</script>

<style scoped>
.page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; color: var(--ad-text); }
.search-bar { display: flex; align-items: center; }
</style>
