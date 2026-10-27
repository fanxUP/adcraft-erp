<template>
  <div class="payment-account-select">
    <el-select
      :model-value="modelValue || ''"
      filterable
      clearable
      :loading="loading"
      :disabled="!auth.can('company_account:select')"
      placeholder="选择付款账户"
      aria-label="付款账户"
      style="width: 100%"
      @update:model-value="emit('update:modelValue', $event || '')"
      @visible-change="visible => visible && load()"
    >
      <el-option v-if="modelValue && !accounts.some(account => account.id === modelValue)" :value="modelValue" :label="auth.can('company_account:select') ? '原账户（不可用）' : '原付款账户（保留）'" disabled />
      <el-option v-for="account in accounts" :key="account.id" :value="account.id" :label="account.label" :disabled="!account.is_active" />
    </el-select>
    <div v-if="!auth.can('company_account:select')" class="account-help">需要选择付款账户权限，请联系管理员。</div>
    <div v-else-if="error" class="account-help" role="alert">账户加载失败。<el-button text type="primary" @click="load">重试</el-button></div>
    <div v-else-if="!loading && !accounts.some(account => account.is_active)" class="account-help">
      暂无启用的付款账户。
      <router-link v-if="auth.can('company_account:manage')" to="/company-accounts">管理公司账户</router-link>
      <span v-else>请联系财务或管理员添加。</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { getCompanyAccountOptions, type CompanyAccount } from '@/api/companyAccounts'
import { useAuthStore } from '@/stores/auth'

const props = withDefaults(defineProps<{ modelValue?: string | null; autoDefault?: boolean; active?: boolean }>(), { active: true })
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const auth = useAuthStore()
const accounts = ref<CompanyAccount[]>([])
const loading = ref(false)
const error = ref(false)
let request = 0
async function load() {
  if (!auth.can('company_account:select')) return
  const current = ++request
  loading.value = true
  error.value = false
  try {
    const rows = await getCompanyAccountOptions()
    if (current !== request) return
    accounts.value = rows
    if (props.active && props.autoDefault && !props.modelValue) {
      const account = rows.find(row => row.is_default && row.is_active)
      if (account) emit('update:modelValue', account.id)
    }
  } catch { if (current === request) error.value = true }
  finally { if (current === request) loading.value = false }
}
watch(() => props.active, active => { if (active) void load() }, { immediate: true })
</script>

<style scoped>
.payment-account-select { width: 100%; }
.account-help { color: var(--ui-text-secondary); font-size: 12px; line-height: 1.6; margin-top: 4px; }
</style>
