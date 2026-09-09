import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const srcRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')

function readSource(relativePath: string) {
  return readFileSync(resolve(srcRoot, relativePath), 'utf8')
}

describe('P07 资源、AI、人事和系统页面一致性', () => {
  it('资源列表复用页面壳层、筛选工具栏、表格状态和分页页脚', () => {
    for (const relativePath of [
      'views/vehicles/VehicleList.vue',
      'views/vehicles/DriverList.vue',
      'views/vehicles/VehicleDispatchList.vue',
      'views/vehicles/VehicleUseRequestList.vue',
      'views/vehicles/VehicleTripRecordList.vue',
      'views/vehicles/VehicleIncidentList.vue',
      'views/aerial/AerialVehicleList.vue',
      'views/aerial/AerialPersonnelList.vue',
      'views/aerial/AerialLedgerList.vue',
      'views/aerial/AerialPersonnelExpenseList.vue',
      'views/aerial/AerialPersonnelWageList.vue',
      'views/aerial/AerialVehicleCostList.vue',
      'views/aerial/AerialSafetyCheckList.vue',
      'views/inventory/InventoryList.vue',
      'views/outsource/OutsourceVendorList.vue',
      'views/outsource/OutsourceTaskRecycle.vue',
      'views/system/BackupManage.vue',
    ]) {
      const source = readSource(relativePath)
      expect(source).toContain('<AppPage')
      expect(source).toContain('<PageHeader')
      expect(source).toContain('<DataTableShell')
      expect(source).toContain('<StatePanel')
    }
  })

  it('AI、人事和系统列表复用统一状态壳层', () => {
    for (const relativePath of [
      'views/ai-model-center/ProviderList.vue',
      'views/ai-model-center/ModelList.vue',
      'views/employee/EmployeeList.vue',
      'views/employee/DepartmentList.vue',
      'views/admin/UserManage.vue',
      'views/system/OperationLogList.vue',
      'views/aerial/AerialAgentDraftList.vue',
    ]) {
      const source = readSource(relativePath)
      expect(source).toContain('<DataTableShell')
      expect(source).toContain('tableState')
    }
  })

  it('矩阵、报表、AI 专用页和系统设置保留业务布局但复用统一页面标题', () => {
    for (const relativePath of [
      'views/attendance/AttendanceRecordList.vue',
      'views/employee/SalaryList.vue',
      'views/employee/SalaryRuleList.vue',
      'views/aerial/AerialAttendanceList.vue',
      'views/aerial/AerialReports.vue',
      'views/ai/AIQuoteAssistant.vue',
      'views/admin/SystemSettings.vue',
    ]) {
      const source = readSource(relativePath)
      expect(source).toContain('<AppPage')
      expect(source).toContain('<PageHeader')
    }
  })

  it('库存金额与操作日志金额不再各自拼接货币符号', () => {
    expect(readSource('views/inventory/InventoryList.vue')).toContain('formatMoney(row.unit_cost)')
    expect(readSource('views/inventory/InventoryList.vue')).toContain('formatMoney(row.total_cost)')
    expect(readSource('views/system/OperationLogList.vue')).toContain('formatMoney(row.after_data.amount)')
  })
})
