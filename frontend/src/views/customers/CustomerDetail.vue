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
          <div class="card-header">
            <span>联系人</span>
            <el-button text type="primary" size="small" @click="handleAddContact">添加联系人</el-button>
          </div>
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
          <el-table-column label="操作" width="140">
            <template #default="{ row }">
              <el-button text type="primary" size="small" @click="handleEditContact(row)">编辑</el-button>
              <el-button text type="danger" size="small" @click="handleDeleteContact(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

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
          <el-button type="danger" :loading="savingContact" @click="handleSaveContact">保存</el-button>
        </template>
      </el-dialog>
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
import { ElMessage, ElMessageBox } from 'element-plus'

const route = useRoute()
const loading = ref(false)
const saving = ref(false)
const customer = ref<CustomerResponse | null>(null)
const dialogVisible = ref(false)
const editForm = reactive({ name: '', customer_type: '', level: '', phone: '', address: '' })

// Contact management
const contactDialogVisible = ref(false)
const savingContact = ref(false)
const contactEditingIndex = ref(-1)
const contactForm = reactive({ name: '', phone: '', wechat: '', position: '', is_primary: false })

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

function handleAddContact() {
  contactEditingIndex.value = -1
  Object.assign(contactForm, { name: '', phone: '', wechat: '', position: '', is_primary: false })
  contactDialogVisible.value = true
}

function handleEditContact(row: CustomerResponse['contacts'][0]) {
  const idx = customer.value?.contacts.findIndex(c => c.id === row.id) ?? -1
  contactEditingIndex.value = idx
  Object.assign(contactForm, {
    name: row.name,
    phone: row.phone || '',
    wechat: row.wechat || '',
    position: row.position || '',
    is_primary: row.is_primary,
  })
  contactDialogVisible.value = true
}

function handleDeleteContact(row: CustomerResponse['contacts'][0]) {
  ElMessageBox.confirm(`确认删除联系人 "${row.name}"？`, '确认', { type: 'warning' }).then(async () => {
    if (!customer.value) return
    customer.value.contacts = customer.value.contacts.filter(c => c.id !== row.id)
    await updateCustomer(route.params.id as string, { contacts: customer.value.contacts.map(c => ({
      name: c.name,
      phone: c.phone,
      wechat: c.wechat,
      position: c.position,
      is_primary: c.is_primary,
    })) })
    ElMessage.success('联系人已删除')
  }).catch(() => {})
}

async function handleSaveContact() {
  if (!contactForm.name) {
    ElMessage.warning('请输入联系人姓名')
    return
  }
  if (!customer.value) return
  savingContact.value = true
  try {
    const contactData = { name: contactForm.name, phone: contactForm.phone || null, wechat: contactForm.wechat || null, position: contactForm.position || null, is_primary: contactForm.is_primary }
    if (contactEditingIndex.value >= 0) {
      // Edit existing — replace in-place
      customer.value.contacts[contactEditingIndex.value] = { ...customer.value.contacts[contactEditingIndex.value], ...contactData }
    } else {
      // Add new — push a temp object (id will come from backend response)
      customer.value.contacts.push({ id: '', ...contactData } as CustomerResponse['contacts'][0])
    }
    // Persist to server
    await updateCustomer(route.params.id as string, { contacts: customer.value.contacts.map(c => ({
      name: c.name,
      phone: c.phone,
      wechat: c.wechat,
      position: c.position,
      is_primary: c.is_primary,
    })) })
    ElMessage.success(contactEditingIndex.value >= 0 ? '联系人已更新' : '联系人已添加')
    contactDialogVisible.value = false
    fetchData()  // Re-fetch to get proper ids for new contacts
  } finally {
    savingContact.value = false
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
