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
    expect(includesAny(mobileInstallation, ['capture="environment"', 'uploadPhoto'])).toBe(true)
  })

  it('does not introduce obvious credentials into UI source', () => {
    const source = readSource('views/admin/SystemSettings.vue')
    expect(source).not.toMatch(/sk-[A-Za-z0-9]{20,}/)
    expect(source).not.toMatch(/-----BEGIN (RSA|OPENSSH|EC|DSA) PRIVATE KEY-----/)
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
})
