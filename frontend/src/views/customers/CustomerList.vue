<template>
  <div class="page">
    <div class="page-header">
      <h2>客户管理</h2>
      <div>
        <el-button @click="importDialogVisible = true">导入</el-button>
        <el-button type="danger" @click="handleCreate">新建客户</el-button>
      </div>
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
          <el-button text type="danger" @click="handleDelete(row as CustomerResponse)">删除</el-button>
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
        <el-divider />
        <div style="margin-bottom: 8px; font-weight: 600; font-size: 14px">联系人</div>
        <el-table :data="form.contacts" stripe size="small" empty-text="暂无联系人" style="margin-bottom: 8px">
          <el-table-column prop="name" label="姓名" />
          <el-table-column prop="phone" label="电话" />
          <el-table-column prop="position" label="职位" />
          <el-table-column prop="is_primary" label="首要" width="60">
            <template #default="{ row }">
              <el-tag v-if="row.is_primary" type="danger" size="small">是</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="{ row, $index }">
              <el-button text type="primary" size="small" @click="handleEditContact(row, $index)">编辑</el-button>
              <el-button text type="danger" size="small" @click="form.contacts.splice($index, 1)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-button size="small" @click="handleAddContact">+ 添加联系人</el-button>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="contactDialogVisible" :title="contactEditingIndex >= 0 ? '编辑联系人' : '添加联系人'" width="420px">
      <el-form :model="contactForm" label-width="90px">
        <el-form-item label="姓名">
          <el-input v-model="contactForm.name" />
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="contactForm.phone" />
        </el-form-item>
        <el-form-item label="微信">
          <el-input v-model="contactForm.wechat" />
        </el-form-item>
        <el-form-item label="职位">
          <el-input v-model="contactForm.position" />
        </el-form-item>
        <el-form-item label="首要联系人">
          <el-switch v-model="contactForm.is_primary" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="contactDialogVisible = false">取消</el-button>
        <el-button type="danger" @click="handleConfirmContact">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="importDialogVisible" title="导入客户" width="520px">
      <div style="margin-bottom: 16px; font-size: 13px; color: var(--ad-text-secondary)">
        <p>支持 .xlsx / .xls 格式，请确保 Excel 包含以下列（<span style="color: #f56c6c">*</span>为必填）：</p>
        <el-table :data="templateColumns" border size="small" style="margin: 12px 0">
          <el-table-column prop="name" label="列名" width="120" />
          <el-table-column prop="desc" label="说明" />
          <el-table-column label="必填" width="60">
            <template #default="{ row }">
              <span v-if="row.required" style="color: #f56c6c">*</span>
            </template>
          </el-table-column>
        </el-table>
        <p>样表：可参考下方示例创建 Excel 文件</p>
        <el-table :data="sampleData" border size="small" style="margin: 8px 0">
          <el-table-column prop="name" label="客户名称" />
          <el-table-column prop="customer_type" label="客户类型" />
          <el-table-column prop="level" label="等级" />
          <el-table-column prop="phone" label="电话" />
          <el-table-column prop="remark" label="备注" />
        </el-table>
      </div>
      <el-upload
        ref="uploadRef"
        accept=".xlsx,.xls"
        :auto-upload="false"
        :limit="1"
        :on-change="handleFileChange"
        :on-exceed="() => ElMessage.warning('只能上传一个文件')"
      >
        <template #trigger>
          <el-button type="primary">选择文件</el-button>
        </template>
        <template #tip>
          <div class="el-upload__tip">仅支持 .xlsx / .xls 文件</div>
        </template>
      </el-upload>
      <div v-if="importResult" style="margin-top: 16px">
        <el-alert
          :title="`导入完成：成功 ${importResult.succeeded} 条，失败 ${importResult.failed} 条`"
          :type="importResult.failed > 0 ? 'warning' : 'success'"
          show-icon
        />
        <el-table v-if="importResult.errors?.length" :data="importResult.errors" border size="small" style="margin-top: 8px" max-height="200px">
          <el-table-column prop="row" label="行号" width="60" />
          <el-table-column prop="message" label="错误信息" />
        </el-table>
      </div>
      <template #footer>
        <el-button @click="importDialogVisible = false">关闭</el-button>
        <el-button type="danger" :loading="importing" :disabled="!importFile" @click="handleImport">开始导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getCustomers, createCustomer, updateCustomer, deleteCustomer, importCustomers } from '@/api/customers'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadFile } from 'element-plus'
import type { CustomerResponse, ImportResponse } from '@/types/api'
import { getErrorMessage } from '@/utils/error'

const loading = ref(false)
const saving = ref(false)
const list = ref<CustomerResponse[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const customerType = ref('')
const dialogVisible = ref(false)
const editingId = ref<string | null>(null)
const form = reactive({ name: '', customer_type: '', level: '', phone: '', address: '', remark: '', contacts: [] as { name: string; phone: string | null; wechat: string | null; position: string | null; is_primary: boolean }[] })

// Contact dialog
const contactDialogVisible = ref(false)
const contactEditingIndex = ref(-1)
const contactForm = reactive({ name: '', phone: '', wechat: '', position: '', is_primary: false })

// Import
const importDialogVisible = ref(false)
const importing = ref(false)
const importFile = ref<File | null>(null)
const importResult = ref<ImportResponse | null>(null)
const templateColumns = [
  { name: '客户名称', desc: '客户全称', required: true },
  { name: '客户类型', desc: '直客 / 代理 / 同行', required: false },
  { name: '等级', desc: 'A / B / C', required: false },
  { name: '电话', desc: '联系电话', required: false },
  { name: '微信', desc: '微信号', required: false },
  { name: '地址', desc: '联系地址', required: false },
  { name: '备注', desc: '备注信息', required: false },
]
const sampleData = [
  { name: '示例科技有限公司', customer_type: '直客', level: 'A', phone: '13800138000', remark: '重要客户' },
  { name: '示例广告公司', customer_type: '代理', level: 'B', phone: '13900139000', remark: '' },
]

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
  Object.assign(form, { name: '', customer_type: '', level: '', phone: '', address: '', remark: '', contacts: [] })
  dialogVisible.value = true
}

async function handleSave() {
  saving.value = true
  try {
    const payload = { ...form, contacts: form.contacts.map(c => ({ name: c.name, phone: c.phone || null, wechat: c.wechat || null, position: c.position || null, is_primary: c.is_primary })) }
    if (editingId.value) {
      await updateCustomer(editingId.value, payload)
      ElMessage.success('更新成功')
    } else {
      await createCustomer(payload)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchData()
  } finally {
    saving.value = false
  }
}

function handleAddContact() {
  contactEditingIndex.value = -1
  Object.assign(contactForm, { name: '', phone: '', wechat: '', position: '', is_primary: false })
  contactDialogVisible.value = true
}

function handleEditContact(row: { name: string; phone: string | null; wechat: string | null; position: string | null; is_primary: boolean }, index: number) {
  contactEditingIndex.value = index
  Object.assign(contactForm, {
    name: row.name,
    phone: row.phone || '',
    wechat: row.wechat || '',
    position: row.position || '',
    is_primary: row.is_primary,
  })
  contactDialogVisible.value = true
}

function handleConfirmContact() {
  if (!contactForm.name) {
    ElMessage.warning('请输入联系人姓名')
    return
  }
  const data = { name: contactForm.name, phone: contactForm.phone || null, wechat: contactForm.wechat || null, position: contactForm.position || null, is_primary: contactForm.is_primary }
  if (contactEditingIndex.value >= 0) {
    form.contacts[contactEditingIndex.value] = data
  } else {
    form.contacts.push(data)
  }
  contactDialogVisible.value = false
}

async function handleDelete(row: CustomerResponse) {
  await ElMessageBox.confirm(`确认删除客户 "${row.name}"？`, '确认', { type: 'warning' })
  await deleteCustomer(row.id)
  ElMessage.success('已删除')
  fetchData()
}

function handleFileChange(uploadFile: UploadFile) {
  importFile.value = uploadFile.raw || null
  importResult.value = null
}

async function handleImport() {
  if (!importFile.value) return
  importing.value = true
  try {
    const data = await importCustomers(importFile.value)
    importResult.value = data
    ElMessage.success(`导入完成：成功 ${data.succeeded} 条${data.failed > 0 ? `，失败 ${data.failed} 条` : ''}`)
    fetchData()
  } catch (e: unknown) {
    ElMessage.error(getErrorMessage(e, '导入失败'))
  } finally {
    importing.value = false
  }
}

onMounted(fetchData)
</script>

<style scoped>
.page { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; color: var(--ad-text); }
.search-bar { display: flex; align-items: center; }
:deep(.el-upload__tip) { margin-top: 4px; font-size: 12px; color: var(--ad-text-secondary, #999); }
</style>
