import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import {
  contrastRatio,
  hasMinimumTouchTarget,
  includesAny,
  REQUIRED_VIEWPORTS,
} from './ui-ux-quality'

const srcRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')

function readSource(relativePath: string): string {
  return readFileSync(resolve(srcRoot, relativePath), 'utf8')
}

describe('P08 UI/UX quality guardrails', () => {
  it('keeps the required desktop, tablet and mobile QA profiles', () => {
    expect(REQUIRED_VIEWPORTS.map(viewport => viewport.width)).toEqual([1440, 1024, 390])
    expect(hasMinimumTouchTarget(40, 40)).toBe(true)
    expect(hasMinimumTouchTarget(39, 40)).toBe(false)
  })

  it('keeps shared focus, status, progress and feedback semantics accessible', () => {
    const tokens = readSource('styles/tokens.scss')
    const mobileLayout = readSource('layouts/MobileLayout.vue')
    const statePanel = readSource('components/ui/StatePanel.vue')
    const progressBar = readSource('components/ui/ProgressBar.vue')
    const statusTag = readSource('components/ui/StatusTag.vue')

    expect(tokens).toContain('focus-visible')
    expect(mobileLayout).toContain('focus-visible')
    expect(statePanel).toContain('aria-live="polite"')
    expect(progressBar).toContain('aria-valuenow')
    expect(statusTag).toContain('aria-label')
    expect(contrastRatio('#202124', '#ffffff')).toBeGreaterThan(4.5)
  })

  it('keeps core pages on shared shell or explicit mobile feedback paths', () => {
    const corePages = [
      'views/home/DashboardView.vue',
      'views/orders/OrderList.vue',
      'views/orders/OrderDetail.vue',
      'views/tasks/DesignTaskList.vue',
      'views/tasks/ProductionTaskList.vue',
      'views/tasks/InstallationTaskList.vue',
      'views/inventory/InventoryList.vue',
      'views/employee/EmployeeList.vue',
    ]
    for (const relativePath of corePages) {
      const source = readSource(relativePath)
      expect(includesAny(source, ['<AppPage', '<PageShell', 'StatePanel', '<StatusTag', '<ProgressBar', '<TaskBoardCard'])).toBe(true)
    }

    const mobileInstallation = readSource('views/tasks/MobileInstallation.vue')
    expect(includesAny(mobileInstallation, ['retry-btn', 'fetchTasks()'])).toBe(true)
    expect(includesAny(mobileInstallation, ['capture', 'OrderTaskAttachments'])).toBe(true)
  })

  it('keeps system creation time out of the order list while retaining the right-side actions', () => {
    const orderList = readSource('views/orders/OrderList.vue')

    expect(orderList).not.toContain('label="系统创建时间"')
    expect(orderList).toContain('<el-table-column label="操作" width="200" fixed="right">')
  })

  it('uses employee numbers as the only employee login entry point', () => {
    const employee = readSource('views/employee/EmployeeList.vue')
    const users = readSource('views/admin/UserManage.vue')
    const login = readSource('views/login/LoginView.vue')
    expect(employee).toContain('自动生成登录账号')
    expect(employee).toContain('initial_password')
    expect(users).not.toContain('新增用户')
    expect(users).not.toContain('createUser')
    expect(users).toContain('label="工号"')
    expect(login).toContain('placeholder="工号"')
    expect(login).toContain('请输入工号')
  })

  it('does not introduce obvious credentials into UI source', () => {
    const source = readSource('views/admin/SystemSettings.vue')
    expect(source).not.toMatch(/sk-[A-Za-z0-9]{20,}/)
    expect(source).not.toMatch(/-----BEGIN (RSA|OPENSSH|EC|DSA) PRIVATE KEY-----/)
  })

  it('uses the shared runtime brand on authenticated, login and mobile surfaces', () => {
    const layout = readSource('layouts/DefaultLayout.vue')
    const login = readSource('views/login/LoginView.vue')
    const mobileProfile = readSource('views/mobile/MobileProfile.vue')
    const brandLogo = readSource('components/BrandLogo.vue')

    for (const source of [layout, login, mobileProfile]) {
      expect(source).toContain('useBrandingStore')
      expect(source).not.toContain('AdCraft ERP')
    }
    expect(brandLogo).toContain('logoUrl')
    expect(brandLogo).toContain('appName')
  })

  it('removes legacy page-header and search-bar CSS after shell migration', () => {
    for (const relativePath of [
      'views/ai/AIQuoteAssistant.vue',
      'views/ai/AnomalyDashboard.vue',
      'views/ai/PaymentOCR.vue',
      'views/ai/BusinessNarrativeReport.vue',
      'views/ai/QuoteKnowledgeBase.vue',
      'views/ai/SitePhotoRecognition.vue',
      'views/ai-model-center/ProviderList.vue',
      'views/aerial/AerialLedgerList.vue',
      'views/aerial/AerialPersonnelExpenseList.vue',
      'views/aerial/AerialPersonnelWageList.vue',
      'views/aerial/AerialVehicleCostList.vue',
      'views/outsource/OutsourceVendorList.vue',
      'views/outsource/OutsourceTaskRecycle.vue',
      'views/payments/StatementList.vue',
      'views/payments/ExpenseList.vue',
      'views/payments/CostDebtList.vue',
    ]) {
      const source = readSource(relativePath)
      expect(source).not.toContain('.page-header')
      expect(source).not.toContain('.search-bar')
    }
  })

  it('keeps the expense form focused and groups optional details', () => {
    const source = readSource('views/payments/ExpenseList.vue')
    const formSource = source.slice(source.indexOf('<el-form'))
    const fieldLabels = [
      'label="业务日期"',
      'label="分类"',
      'label="供应商（可选）"',
      'label="登记时已付"',
      'label="登记时未付"',
      '补充信息（付款方式、说明、凭证）',
      'label="登记时付款方式"',
      'label="说明"',
      'label="凭证"',
    ]
    const positions = fieldLabels.map(label => formSource.indexOf(label))

    expect(positions.every(position => position >= 0)).toBe(true)
    expect(positions).toEqual([...positions].sort((left, right) => left - right))
    expect(formSource).toContain('class="expense-amount-summary"')
    expect(formSource).toContain('class="expense-extra-fields"')
    expect(formSource).toContain('v-model="form.payment_method"')
    expect(formSource).toContain('v-for="pm in PAYMENT_METHODS"')
    expect(source).not.toContain('label="应付对象"')
    expect(source).toContain('class="expense-attachment-dropzone"')
    expect(source).toContain('@drop.prevent="handleExpenseAttachmentDrop"')
    expect(source).toContain('getExpenseAttachments')
  })

  it('keeps project-cost entry and list on the simplified financial fields', () => {
    const source = readSource('views/payments/ProjectCostDetail.vue')
    const api = readSource('api/payments.ts')
    const formSource = source.slice(source.indexOf('<el-form'))
    const fieldLabels = [
      'label="日期"',
      'label="供应商"',
      'label="支付金额"',
      'label="欠款金额"',
      'label="分类"',
      'label="付款方式"',
      'label="支出总额"',
      'label="说明"',
      'label="凭证"',
    ]
    const positions = fieldLabels.map(label => formSource.indexOf(label))

    expect(positions.every(position => position >= 0)).toBe(true)
    expect(positions).toEqual([...positions].sort((left, right) => left - right))
    for (const legacyBinding of ['form.summary', 'form.quantity', 'form.specification', 'form.unit', 'form.unit_price', 'form.payee_company_name']) {
      expect(source).not.toContain(legacyBinding)
    }
    expect(source).toContain('label="支付金额"')
    expect(source).toContain('支出总额 = 支付金额 + 欠款金额')
    expect(source).toContain('row.supplier_name || row.payee_company_name')
    expect(source).toContain(':required="!isEditing || editingOriginalHasCostDate || !!form.cost_date"')
    expect(source).toContain("if (!form.cost_date && (!isEditing.value || editingOriginalHasCostDate.value))")
    expect(api).toContain('cost_date: string')
  })

  it('removes the repeated undated-payment warning but preserves record-level reconciliation', () => {
    const expenditure = readSource('components/payments/ExpenditureTable.vue')
    const dashboard = readSource('views/finance/FinanceCenterDashboard.vue')

    expect(expenditure).not.toContain('付款日期待核实 {{ formatMoney(unverifiedAmount) }}')
    expect(expenditure).not.toContain('这部分不计入所选期间的实际付款，也不会用其他日期推测。')
    expect(expenditure).toContain('核实付款日期')
    expect(expenditure).toContain('value="unverified"')
    expect(dashboard).not.toContain('<span>付款日期待核实</span>')
    expect(dashboard).not.toContain('日期口径：不会用业务日期或系统创建时间推测收付款日期。')
  })

  it('shows payment-oriented finance columns with project department context', () => {
    const expenditure = readSource('components/payments/ExpenditureTable.vue')

    expect(expenditure).not.toContain('业务日期 / 最后付款日期')
    expect(expenditure).toContain('label="付款日期"')
    expect(expenditure).toContain('label="项目"')
    expect(expenditure).toContain('prop="department" label="部门/科室"')
    expect(expenditure).toContain('label="供应商 / 收款方"')
    expect(expenditure).toContain('label="本次付款"')
    expect(expenditure).toContain('label="累计已付"')
    expect(expenditure).toContain('label="剩余待付"')
    expect(expenditure).toContain('label="操作"')
  })
})
