<template>
  <AppPage>
    <template #header>
      <PageHeader title="银行台账" description="按银行、微信和支付宝账户查看已登记且有付款日期的支出。" />
    </template>

    <StatePanel v-if="accountsLoading" state="loading" title="正在加载账户" />
    <StatePanel
      v-else-if="accountsError"
      state="error"
      title="账户加载失败"
      action-label="重试"
      @action="loadAccounts"
    />
    <StatePanel v-else-if="!accounts.length" title="暂无可用账户" description="请先在公司账户中登记银行、微信或支付宝账户。">
      <template #actions>
        <router-link :to="{ name: 'CompanyAccountList' }">查看公司账户</router-link>
      </template>
    </StatePanel>

    <el-tabs v-else :model-value="activeAccountId" class="bank-account-tabs" aria-label="资金账户" @update:model-value="selectAccount">
      <el-tab-pane v-for="account in accounts" :key="account.id" :name="account.id" lazy>
        <template #label>
          <span class="bank-account-label" :title="accountTabLabel(account)">{{ accountTabLabel(account) }}</span>
          <el-tag v-if="!account.is_active" class="bank-account-status" type="info" size="small">已停用</el-tag>
        </template>

        <template v-if="account.id === activeAccountId">
          <dl class="bank-ledger-summary" aria-label="账户统计" :aria-busy="loading">
            <div><dt>付款笔数</dt><dd>{{ result ? `${result.total} 笔` : '—' }}</dd></div>
            <div><dt>收入合计</dt><dd>待接入</dd></div>
            <div><dt>支出合计</dt><dd>{{ result ? formatMoney(result.summary.amount) : '—' }}</dd></div>
            <div><dt>账户余额</dt><dd>未建账</dd></div>
          </dl>

          <DataTableShell aria-label="账户流水">
            <el-table :data="result?.items ?? []" row-key="row_key" stripe>
              <el-table-column label="日期" width="115">
                <template #default="{ row }">{{ expenditureDateLabel(row.paid_at) }}</template>
              </el-table-column>
              <el-table-column label="摘要" min-width="170" show-overflow-tooltip>
                <template #default="{ row }">{{ row.description || '—' }}</template>
              </el-table-column>
              <el-table-column label="对方账号" min-width="130">
                <template #default>—</template>
              </el-table-column>
              <el-table-column label="对方户名" min-width="145" show-overflow-tooltip>
                <template #default="{ row }">{{ row.supplier_name || '—' }}</template>
              </el-table-column>
              <el-table-column label="分类" min-width="100" show-overflow-tooltip>
                <template #default="{ row }">{{ expenditureCategoryLabel(row.source_type, row.category) }}</template>
              </el-table-column>
              <el-table-column label="收入金额" min-width="115" align="right">
                <template #default>—</template>
              </el-table-column>
              <el-table-column label="支出金额" min-width="115" align="right">
                <template #default="{ row }">{{ formatMoney(row.amount) }}</template>
              </el-table-column>
              <el-table-column label="余额" min-width="115" align="right">
                <template #default>—</template>
              </el-table-column>
              <el-table-column label="项目" min-width="150" show-overflow-tooltip>
                <template #default="{ row }">{{ row.project_name || '—' }}</template>
              </el-table-column>
              <el-table-column label="部门/科室" min-width="120" show-overflow-tooltip>
                <template #default="{ row }">{{ row.department || '—' }}</template>
              </el-table-column>
              <template #empty>
                <StatePanel v-if="loading" state="loading" title="正在加载账户流水" />
                <StatePanel v-else-if="loadError" state="error" title="账户流水加载失败" action-label="重试" @action="loadPayments" />
                <StatePanel v-else title="暂无付款记录" description="该账户暂无有付款日期的已登记支出。" />
              </template>
            </el-table>
            <template v-if="result && result.total > pageSize" #footer>
              <el-pagination
                v-model:current-page="page"
                :page-size="pageSize"
                :total="result.total"
                :pager-count="5"
                layout="prev, pager, next"
              />
            </template>
          </DataTableShell>
          <p v-if="result?.items.length" class="bank-ledger-note">对方户名按 ERP 支出记录中的收款方显示。</p>
        </template>
      </el-tab-pane>
    </el-tabs>
  </AppPage>
</template>

<script setup lang="ts">
import { onMounted, ref, shallowRef, watch } from 'vue'
import { accountTypeLabels, getCompanyAccountOptions, type CompanyAccount } from '@/api/companyAccounts'
import { getExpenditure, type ExpenditureResult } from '@/api/payments'
import { AppPage, DataTableShell, PageHeader, StatePanel } from '@/components/ui'
import { expenditureCategoryLabel, expenditureDateLabel, latestRequest } from '@/utils/expenditure'
import { formatMoney } from '@/utils/format'

const accounts = shallowRef<CompanyAccount[]>([])
const accountsLoading = ref(true)
const accountsError = ref(false)
const activeAccountId = ref('')
const page = ref(1)
const pageSize = 20
const result = shallowRef<ExpenditureResult | null>(null)
const loading = ref(false)
const loadError = ref(false)
const requests = latestRequest()

function accountTabLabel(account: CompanyAccount) {
  const label = account.label
  return account.account_type === 'bank' ? label : `${accountTypeLabels[account.account_type]} · ${label}`
}

function selectAccount(id: string | number) {
  page.value = 1
  activeAccountId.value = String(id)
}

async function loadAccounts() {
  accountsLoading.value = true
  accountsError.value = false
  try {
    accounts.value = (await getCompanyAccountOptions()).filter(account =>
      ['bank', 'wechat', 'alipay'].includes(account.account_type),
    )
    const firstAccount = accounts.value.find(account => account.is_active) ?? accounts.value[0]
    if (firstAccount) selectAccount(firstAccount.id)
  } catch {
    accountsError.value = true
  } finally {
    accountsLoading.value = false
  }
}

async function loadPayments() {
  if (!activeAccountId.value) return
  const request = requests.begin()
  loading.value = true
  loadError.value = false
  result.value = null
  try {
    const data = await getExpenditure('disbursements', {
      page: page.value,
      page_size: pageSize,
      payment_account_id: activeAccountId.value,
      date_status: 'confirmed',
    })
    if (requests.isCurrent(request)) result.value = data
  } catch {
    if (requests.isCurrent(request)) loadError.value = true
  } finally {
    if (requests.isCurrent(request)) loading.value = false
  }
}

watch([activeAccountId, page], loadPayments)
onMounted(loadAccounts)
</script>

<style scoped>
.bank-account-tabs { min-width: 0; }
.bank-account-tabs :deep(.el-tabs__item) { height: 44px; }
.bank-account-label {
  display: inline-block;
  max-width: clamp(125px, 48vw, 260px);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.bank-account-status { margin-left: var(--ui-space-2); }
.bank-ledger-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 150px), 1fr));
  gap: var(--ui-space-4);
  margin: 0 0 var(--ui-space-4);
  padding: var(--ui-space-4);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-sm);
  background: var(--ui-surface);
}
.bank-ledger-summary dt { color: var(--ui-text-secondary); margin-bottom: var(--ui-space-2); }
.bank-ledger-summary dd {
  margin: 0;
  color: var(--ui-text);
  font-size: var(--ui-font-size-title);
  font-weight: var(--ui-font-weight-semibold);
  font-variant-numeric: tabular-nums;
}
.bank-ledger-note { margin: var(--ui-space-3) 0 0; color: var(--ui-text-secondary); }
</style>
