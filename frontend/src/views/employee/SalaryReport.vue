<template>
  <div class="page">
    <div class="page-header">
      <h2><el-icon><Document /></el-icon> 工资报表</h2>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
        <el-date-picker v-model="curMonth" type="month" value-format="YYYY-MM" placeholder="选择月份" style="width:160px" @change="fetchData" />
        <el-button @click="fetchData" type="primary">刷新</el-button>
        <el-button @click="handlePrint" type="primary"><el-icon><Printer /></el-icon> 打印</el-button>
        <el-button plain @click="handlePrintAll" type="primary"><el-icon><Printer /></el-icon> 打印工资条</el-button>
      </div>
    </div>

    <div class="report-sheet">
      <div class="report-title">{{ title }}</div>
      <div class="report-scroll" v-loading="loading">
        <table class="rep-sheet" v-if="rows.length">
          <thead>
            <tr v-for="(hrow, ri) in headerRows" :key="ri">
              <th v-for="(h, hi) in hrow" :key="ri + '-' + hi"
                  :colspan="h.colspan" :rowspan="h.rowspan"
                  :class="h.key === 'no' || h.key === 'dept' || h.key === 'name' ? 'col-fixed' : 'col-item'">
                {{ h.label }}<span v-if="h.is_manual" class="manual-badge" title="手工填写">手</span>
              </th>
              <th v-if="ri === 0" class="no-print" rowspan="3">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.employee_id">
              <template v-for="c in cols" :key="c.key">
                <td v-if="c.type === 'fixed'" :class="c.key === 'name' ? 'c-name' : 'c-center'">
                  {{ c.key === 'no' ? (row.employee_no || '') : c.key === 'dept' ? deptLabel(row.department) : row.employee_name }}
                </td>
                <td v-else-if="c.type === 'item'" :class="['c-num', { 'c-strong': isStrong(c.key) }]">{{ fmtVal(row.values[c.key]) }}</td>
                <td v-else-if="c.type === 'remark'" class="c-center">{{ row.remark || '' }}</td>
                <td v-else class="c-center">{{ ({ pending: '待核算', calculated: '已核算', paid: '已发放' })[row.payment_status || 'pending'] }}</td>
              </template>
              <td class="no-print ops-cell"><el-button size="small" plain @click="openPayslip(row)">工资条</el-button></td>
            </tr>
          </tbody>
          <tfoot>
            <tr class="rep-total">
              <template v-for="c in cols" :key="c.key">
                <td v-if="c.type === 'fixed' && c.key === 'no'" class="c-total-label">合计</td>
                <td v-else-if="c.type === 'item'" class="c-num">{{ fmtVal(totals[c.key]) }}</td>
                <td v-else class="c-center"></td>
              </template>
              <td class="no-print"></td>
            </tr>
          </tfoot>
        </table>
        <el-empty v-else description="该月暂无工资记录，请先在「工资管理」计算生成" />
      </div>
    </div>

    <el-dialog v-model="payslipDialog" :title="dialogTitle" width="780px" top="4vh" @closed="payslipRow = null" :close-on-click-modal="false">
      <iframe ref="payslipFrame" class="payslip-frame" :srcdoc="payslipDoc"></iframe>
      <template #footer>
        <el-button @click="payslipDialog = false">关闭</el-button>
        <el-button @click="printPayslipFromDialog" type="primary"><el-icon><Printer /></el-icon> 打印工资条</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { Document, Printer } from '@element-plus/icons-vue'
import { ref, computed, onMounted } from "vue"
import { getSalaryGrid, type SalaryItem, type SalaryGridRow } from "@/api/salaries"
import { buildCols, buildHeaderRows, gridTotals, fmtVal, deptLabel, isStrong, type Col, type HCell } from "@/composables/useSalaryGrid"
import { buildPayslipDocument, payslipMonthLabel, type PayslipMeta } from "@/composables/usePayslip"
import { ElMessage, ElMessageBox } from "element-plus"

/* ====== state ====== */
const curMonth = ref("")
const items = ref<SalaryItem[]>([])
const rows = ref<SalaryGridRow[]>([])
const loading = ref(false)

/* ====== 列/表头/合计：数据与工资表页共用 useSalaryGrid（列跟随工资表），外观是独立财务报表风格 ====== */
const cols = computed<Col[]>(() => buildCols(items.value))
const headerRows = computed<HCell[][]>(() => buildHeaderRows(cols.value))
const totals = computed<Record<string, number>>(() => gridTotals(items.value, rows.value))

const title = computed(() => {
  if (!curMonth.value) return "工资表"
  const [y, m] = curMonth.value.split("-")
  return `${y}年${Number(m)}月工资表`
})

async function fetchData() {
  if (!curMonth.value) curMonth.value = new Date().toISOString().slice(0, 7)
  loading.value = true
  try {
    const g = await getSalaryGrid(curMonth.value)
    items.value = g?.items || []
    rows.value = g?.rows || []
  } catch (e: unknown) {
    ElMessage.error((e as { message?: string })?.message || "加载报表失败")
  } finally {
    loading.value = false
  }
}

function handlePrint() {
  const table = document.querySelector('.rep-sheet')
  if (!table) { ElMessage.warning('暂无数据可打印'); return }
  const styleTag = '<style>'
    + '@page { size: A4 landscape; margin: 8mm; }'
    + '* { -webkit-print-color-adjust: exact; print-color-adjust: exact; box-sizing: border-box; }'
    + 'body { font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; margin: 0; }'
    + '.print-title { text-align: center; font-size: 22px; font-weight: 700; font-family: Songti, "SimSun", serif; padding: 12px 0 10px; }'
    + 'table { width: 100%; border-collapse: collapse; font-size: 10px; white-space: nowrap; }'
    + 'th, td { border: 1px solid #999 !important; padding: 2px 4px !important; text-align: center; }'
    + 'thead { display: table-header-group; } tbody { display: table-row-group; }'
    + 'tr { page-break-inside: avoid; }'
    + 'thead th { background: #f2f2f2 !important; font-weight: 700; }'
    + '.rep-total td { background: #d6e4f0 !important; font-weight: 700; }'
    + '.c-num { text-align: right !important; font-family: "Courier New", monospace; }'
    + '.c-num.c-strong { color: #0b7a1b !important; }'
    + '.no-print { display: none !important; }'
    + '</style>'
  const html = '<!DOCTYPE html><html><head><meta charset="utf-8"><title>' + title.value + '</title>'
    + styleTag
    + '</head><body>'
    + '<div class="print-title">' + title.value + '</div>'
    + table.outerHTML
    + '<script>window.onload=function(){setTimeout(function(){window.print();window.close()},500)}</scr' + 'ipt>'
    + '</body></html>'
  const win = window.open('', '_blank')
  if (win) { win.document.write(html); win.document.close() }
}

onMounted(() => fetchData())

/* ====== 工资条：单员工弹窗预览 + 批量打印（数据均来自已加载的 grid items/rows，后端零改动） ====== */
const payslipDialog = ref(false)
const payslipRow = ref<SalaryGridRow | null>(null)
const payslipFrame = ref<HTMLIFrameElement | null>(null)

const dialogTitle = computed(() =>
  payslipRow.value ? `${payslipMonthLabel(curMonth.value)} 工资条` : "工资条")

const payslipDoc = computed(() =>
  payslipRow.value
    ? buildPayslipDocument([{ month: curMonth.value, employee: payslipRow.value, items: items.value }], { autoPrint: false })
    : "")

function openPayslip(row: SalaryGridRow) {
  payslipRow.value = row
  payslipDialog.value = true
}

function printPayslipFromDialog() {
  payslipFrame.value?.contentWindow?.print()
}

async function handlePrintAll() {
  if (!rows.value.length) { ElMessage.warning("该月暂无工资记录，无法打印工资条"); return }
  try {
    await ElMessageBox.confirm(`将打印 ${rows.value.length} 位员工的工资条（每人一页 A4），是否继续？`, "批量打印工资条", { type: "info" })
  } catch { return }
  const metas: PayslipMeta[] = rows.value.map(r => ({
    month: curMonth.value, employee: r, items: items.value,
  }))
  const html = buildPayslipDocument(metas, { autoPrint: true })
  const win = window.open("", "_blank")
  if (win) { win.document.write(html); win.document.close() }
}
</script>

<style scoped>
.report-sheet { background: var(--ad-card); border: 1px solid var(--ad-border); border-radius: 4px; padding: 12px; }
.report-title { text-align: center; font-size: 22px; font-weight: 700; font-family: Songti, "SimSun", serif; padding: 6px 0 12px; border-bottom: 2px solid var(--ad-text); margin-bottom: 10px; color: var(--ad-text); }
.report-scroll { overflow-x: auto; overflow-y: auto; max-height: calc(100vh - 220px); padding-bottom: 14px; }
.rep-sheet { width: 100%; border-collapse: collapse; white-space: nowrap; }
.rep-sheet th, .rep-sheet td { border: 1px solid var(--ad-border); padding: 3px 5px; font-size: 12px; }
.rep-sheet thead th { background: var(--ad-darker); font-weight: 700; color: var(--ad-text); text-align: center; line-height: 1.35; }
.col-fixed { min-width: 72px; }
.col-item { min-width: 76px; }
.manual-badge { display: inline-block; margin-left: 3px; padding: 0 3px; border-radius: 3px; font-size: 10px; line-height: 14px; color: var(--el-color-warning); background: #fdf6ec; border: 1px solid #f3d19e; }
.c-center { text-align: center; }
.c-name { font-weight: 600; color: var(--ad-text); }
.c-num { text-align: right; font-family: "SF Mono", "Courier New", monospace; font-weight: 700; color: var(--ad-text); }
.c-num.c-strong { color: var(--el-color-success); }
.rep-total td { background: var(--ad-accent-glow); font-weight: 700; color: var(--ad-text); }
.c-total-label { text-align: right; padding-right: 10px; }
.ops-cell { text-align: center; }
.payslip-frame { width: 100%; height: 560px; border: 1px solid var(--ad-border); border-radius: 4px; background: var(--ad-card); }
</style>
