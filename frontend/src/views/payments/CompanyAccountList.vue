<template>
  <AppPage>
    <template #header>
      <PageHeader title="公司账户" description="维护公司付款账户，按每笔付款查看资金来源。">
        <template #actions><el-button v-if="canManage" type="primary" @click="openEditor()">新增账户</el-button></template>
      </PageHeader>
    </template>
    <template #toolbar>
      <PageToolbar>
        <el-input v-model="keyword" clearable placeholder="搜索账户名称、开户行或尾号" aria-label="搜索公司账户" style="max-width: 320px" />
        <el-select v-model="status" aria-label="账户状态" style="width: 130px">
          <el-option label="全部状态" value="all" /><el-option label="启用" value="active" /><el-option label="停用" value="inactive" />
        </el-select>
        <el-button :loading="loading" @click="load">刷新</el-button>
      </PageToolbar>
    </template>
    <DataTableShell :state="state">
      <template #error><StatePanel state="error" action-label="重试" @action="load" /></template>
      <el-table :data="filtered" row-key="id" stripe>
        <el-table-column prop="name" label="账户名称" min-width="150">
          <template #default="{ row }">{{ row.name }} <el-tag v-if="row.is_default" size="small">默认付款</el-tag></template>
        </el-table-column>
        <el-table-column label="类型" width="100"><template #default="{ row }">{{ accountTypeLabels[row.account_type as CompanyAccountType] }}</template></el-table-column>
        <el-table-column prop="holder_name" label="开户名称" min-width="140" show-overflow-tooltip><template #default="{ row }">{{ row.holder_name || '—' }}</template></el-table-column>
        <el-table-column prop="bank_name" label="开户行" min-width="130" show-overflow-tooltip><template #default="{ row }">{{ row.bank_name || '—' }}</template></el-table-column>
        <el-table-column label="账号" min-width="180"><template #default="{ row }">{{ row.account_number || row.masked_number || '—' }}</template></el-table-column>
        <el-table-column label="状态" width="80"><template #default="{ row }"><el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? '启用' : '停用' }}</el-tag></template></el-table-column>
        <el-table-column label="操作" min-width="260" fixed="right">
          <template #default="{ row }">
            <el-button v-if="auth.can('expense:read')" text type="primary" @click="paymentAccount = row">付款记录</el-button>
            <template v-if="canManage">
              <el-button text type="primary" @click="openEditor(row)">编辑</el-button>
              <el-button v-if="row.is_active && !row.is_default" text type="primary" :disabled="mutating" @click="change(row, { is_default: true })">设为默认</el-button>
              <el-button text :type="row.is_active ? 'warning' : 'success'" :disabled="mutating" @click="toggle(row)">{{ row.is_active ? '停用' : '启用' }}</el-button>
              <el-button v-if="!row.is_referenced" text type="danger" :disabled="mutating" @click="remove(row)">删除</el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>
    </DataTableShell>

    <el-dialog v-model="editorVisible" :title="editing ? '编辑公司账户' : '新增公司账户'" width="min(94vw, 620px)" class="company-account-dialog" top="5vh" :close-on-click-modal="false">
      <el-alert v-if="editing?.is_referenced" title="该账户已有付款关联，账户类型和开户信息已锁定；更换账号请新建账户。" type="info" :closable="false" />
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" class="account-form">
        <el-form-item label="账户名称" prop="name"><el-input v-model="form.name" maxlength="100" placeholder="例如：公司基本户、现金备用金" /></el-form-item>
        <el-form-item label="账户类型" prop="account_type">
          <el-select v-model="form.account_type" :disabled="editing?.is_referenced" style="width: 100%">
            <el-option v-for="(label, value) in accountTypeLabels" :key="value" :value="value" :label="label" />
          </el-select>
        </el-form-item>
        <template v-if="form.account_type !== 'cash'">
          <el-form-item label="开户名称" prop="holder_name" :required="form.account_type === 'bank'"><el-input v-model="form.holder_name" :disabled="editing?.is_referenced" maxlength="200" /></el-form-item>
          <el-form-item v-if="form.account_type === 'bank'" label="开户行" prop="bank_name" required><el-input v-model="form.bank_name" :disabled="editing?.is_referenced" maxlength="200" /></el-form-item>
          <el-form-item label="账号" prop="account_number" :required="form.account_type !== 'other'"><el-input v-model="form.account_number" :disabled="editing?.is_referenced" maxlength="200" autocomplete="off" /></el-form-item>
        </template>
        <el-form-item label="状态"><el-switch v-model="form.is_active" active-text="启用" inactive-text="停用" @change="value => { if (!value) form.is_default = false }" /></el-form-item>
        <el-form-item label="默认付款账户"><el-switch v-model="form.is_default" :disabled="!form.is_active" /><span class="account-hint">新增付款时优先选中，可随时更换。</span></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" :rows="2" maxlength="2000" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="editorVisible = false">取消</el-button><el-button type="primary" :loading="mutating" @click="save">保存</el-button></template>
    </el-dialog>

    <el-drawer :model-value="!!paymentAccount" :title="`${paymentAccount?.name || ''} · 付款记录`" size="min(1200px, 100vw)" destroy-on-close @close="paymentAccount = null">
      <p class="account-hint">合计为当前权限和筛选范围内已登记的付款，不代表银行余额。</p>
      <ExpenditureTable v-if="paymentAccount" view="disbursements" :refresh-key="0" :payment-account-id="paymentAccount.id" @manage-expense="id => router.push({ path: '/expenses', query: { expense_id: id } })" />
    </el-drawer>
  </AppPage>
</template>

<script setup lang="ts">
import { getErrorMessage } from '@/utils/error'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormItemRule } from 'element-plus'
import { accountTypeLabels, createCompanyAccount, deleteCompanyAccount, getCompanyAccounts, updateCompanyAccount, type CompanyAccount, type CompanyAccountType } from '@/api/companyAccounts'
import { useAuthStore } from '@/stores/auth'
import { AppPage, PageHeader, PageToolbar, DataTableShell, StatePanel } from '@/components/ui'
import ExpenditureTable from '@/components/payments/ExpenditureTable.vue'

const auth = useAuthStore()
const router = useRouter()
const canManage = computed(() => auth.canAll(['company_account:manage', 'company_account:view_number']))
const accounts = ref<CompanyAccount[]>([])
const loading = ref(false)
const error = ref(false)
const mutating = ref(false)
const keyword = ref('')
const status = ref('all')
const filtered = computed(() => accounts.value.filter(row =>
  (status.value === 'all' || row.is_active === (status.value === 'active')) &&
  [row.name, row.bank_name, row.masked_number].some(value => value?.includes(keyword.value.trim())),
))
const state = computed(() => loading.value ? 'loading' : error.value ? 'error' : filtered.value.length ? 'ready' : 'empty')
const editorVisible = ref(false)
const editing = ref<CompanyAccount | null>(null)
const paymentAccount = ref<CompanyAccount | null>(null)
const formRef = ref<FormInstance>()
const defaults = () => ({ name: '', account_type: 'bank' as CompanyAccountType, holder_name: '', bank_name: '', account_number: '', is_active: true, is_default: false, remark: '' })
const form = reactive(defaults())
const conditionalRequired = (key: 'holder_name' | 'bank_name' | 'account_number'): FormItemRule => ({
  validator: (_rule, value, callback) => {
    const required = form.account_type === 'bank' || (key === 'account_number' && ['wechat', 'alipay'].includes(form.account_type))
    callback(required && !String(value || '').trim() ? new Error('请填写此项') : undefined)
  }, trigger: 'blur',
})
const rules = { name: [{ required: true, whitespace: true, message: '请填写账户名称', trigger: 'blur' }], holder_name: [conditionalRequired('holder_name')], bank_name: [conditionalRequired('bank_name')], account_number: [conditionalRequired('account_number')] }
async function load() {
  loading.value = true; error.value = false
  try { accounts.value = await getCompanyAccounts() } catch { error.value = true } finally { loading.value = false }
}
function openEditor(row?: CompanyAccount) {
  editing.value = row || null
  Object.assign(form, defaults(), row ? { name: row.name, account_type: row.account_type, holder_name: row.holder_name || '', bank_name: row.bank_name || '', account_number: row.account_number || '', is_active: row.is_active, is_default: row.is_default, remark: row.remark || '' } : {})
  editorVisible.value = true
  formRef.value?.clearValidate()
}
async function save() {
  if (!await formRef.value?.validate().catch(() => false)) return
  mutating.value = true
  try {
    if (editing.value) await updateCompanyAccount(editing.value.id, { ...form })
    else await createCompanyAccount({ ...form })
    ElMessage.success('公司账户已保存'); editorVisible.value = false; await load()
  } catch (error) { ElMessage.error(getErrorMessage(error, '保存账户失败')) } finally { mutating.value = false }
}
async function change(row: CompanyAccount, data: Partial<CompanyAccount>) {
  mutating.value = true
  try { await updateCompanyAccount(row.id, data); ElMessage.success('账户已更新'); await load() }
  catch (error) { ElMessage.error(getErrorMessage(error, '更新账户失败')) } finally { mutating.value = false }
}
async function toggle(row: CompanyAccount) {
  if (row.is_active && !await ElMessageBox.confirm('停用后不能用于新增付款，历史记录继续保留。', '停用账户', { type: 'warning' }).then(() => true).catch(() => false)) return
  await change(row, { is_active: !row.is_active })
}
async function remove(row: CompanyAccount) {
  if (!await ElMessageBox.confirm(`确认删除未使用的账户“${row.name}”？`, '删除公司账户', { type: 'warning' }).then(() => true).catch(() => false)) return
  mutating.value = true
  try { await deleteCompanyAccount(row.id); ElMessage.success('账户已删除'); await load() }
  catch (error) { ElMessage.error(getErrorMessage(error, '删除账户失败')) } finally { mutating.value = false }
}
onMounted(load)
</script>

<style scoped>
:global(.company-account-dialog) { max-height: 90vh; display: flex; flex-direction: column; }
:global(.company-account-dialog .el-dialog__body) { overflow-y: auto; min-height: 0; }
.account-form { margin-top: var(--ui-space-4); }
.account-hint { color: var(--ui-text-secondary); line-height: 1.6; margin-left: var(--ui-space-2); }
</style>
