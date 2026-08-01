<template>
  <div class="page">
    <div class="page-header">
      <h2>🧾 工资报表</h2>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
        <el-date-picker v-model="curMonth" type="month" value-format="YYYY-MM" placeholder="选择月份" style="width:160px" @change="fetchData" />
        <el-button @click="fetchData">刷新</el-button>
        <el-button type="primary" @click="handlePrint">🖨️ 打印</el-button>
      </div>
    </div>

    <div class="report-sheet">
      <div class="report-title">{{ title }}</div>
      <div class="report-scroll" v-loading="loading">
        <table class="rep-sheet" v-if="rows.length">
          <thead>
            <tr v-for="(hrow, ri) in headerRows" :key="ri" :class="'rep-hdr-' + (ri + 1)">
              <th v-for="(h, hi) in hrow" :key="ri + '-' + hi"
                  :colspan="h.colspan" :rowspan="h.rowspan"
                  :class="h.key === 'no' || h.key === 'dept' || h.key === 'name' ? 'col-fixed' : 'col-item'"
                  :style="hdrStyle(h, ri)"
                  :title="h.formula ? (h.is_manual ? '手工填写' : h.formula) : ''">
                {{ h.label }}<span v-if="h.is_manual" class="manual-badge" title="手工填写">手</span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.employee_id">
              <template v-for="c in cols" :key="c.key">
                <td v-if="c.type === 'fixed'" :class="c.key === 'name' ? 'c-name' : 'c-center'">
                  {{ c.key === 'no' ? (row.employee_no || '') : c.key === 'dept' ? deptLabel(row.department) : row.employee_name }}
                </td>
                <td v-else-if="c.type === 'item'" class="c-num">{{ fmtVal(row.values[c.key]) }}</td>
                <td v-else-if="c.type === 'remark'" class="c-center">{{ row.remark || '' }}</td>
                <td v-else class="c-center">{{ ({ pending: '待核算', calculated: '已核算', paid: '已发放' })[row.payment_status || 'pending'] }}</td>
              </template>
            </tr>
          </tbody>
          <tfoot>
            <tr class="rep-total">
              <template v-for="c in cols" :key="c.key">
                <td v-if="c.type === 'fixed' && c.key === 'no'" class="c-total-label">合计</td>
                <td v-else-if="c.type === 'item'" class="c-num">{{ fmtVal(totals[c.key]) }}</td>
                <td v-else class="c-center"></td>
              </template>
            </tr>
          </tfoot>
        </table>
        <el-empty v-else description="该月暂无工资记录，请先在「工资管理」计算生成" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue"
import { getSalaryGrid, type SalaryItem, type SalaryGridRow } from "@/api/salaries"
import { buildCols, buildHeaderRows, gridTotals, hdrStyle, fmtVal, deptLabel, type Col, type HCell } from "@/composables/useSalaryGrid"
import { ElMessage } from "element-plus"

/* ====== state ====== */
const curMonth = ref("")
const items = ref<SalaryItem[]>([])
const rows = ref<SalaryGridRow[]>([])
const loading = ref(false)

/* ====== 列/表头/合计：与工资表页共用 useSalaryGrid，保证两页永远一致 ====== */
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
    + '.print-title { text-align: center; font-size: 20px; font-weight: 700; padding: 10px 0 8px; }'
    + 'table { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 10px; white-space: nowrap; }'
    + 'th, td { border: 2px solid #666; padding: 3px 5px; text-align: center; }'
    + 'thead { display: table-header-group; }'
    + 'tr { page-break-inside: avoid; }'
    + 'tfoot td { background: #E0E0E0 !important; font-weight: 700; }'
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
</script>

<style scoped>
.report-sheet { background: #fff; border: 1px solid #e4e7ed; border-radius: 4px; padding: 12px; }
.report-title { text-align: center; font-size: 22px; font-weight: 700; font-family: Songti, "SimSun", serif; padding: 6px 0 12px; border-bottom: 2px solid #333; margin-bottom: 10px; color: #303133; }
.report-scroll { overflow-x: auto; overflow-y: auto; max-height: calc(100vh - 220px); }
.rep-sheet { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 15px; white-space: nowrap; }
.rep-sheet th, .rep-sheet td { border: 2px solid #666; padding: 5px 6px; }
.rep-sheet thead { position: sticky; top: 0; z-index: 2; }
.rep-sheet thead th { font-weight: 700; text-align: center; color: #000; border-color: #333; }
.col-fixed { min-width: 72px; }
.col-item { min-width: 100px; text-align: center; }
.manual-badge { display: inline-block; margin-left: 3px; padding: 0 3px; border-radius: 3px; font-size: 10px; line-height: 14px; color: #e6a23c; background: #fdf6ec; border: 1px solid #f3d19e; }
.c-center { text-align: center; }
.c-name { font-weight: 600; color: #303133; min-width: 96px; }
.c-num { text-align: right; font-family: "SF Mono", "Courier New", monospace; font-weight: 700; color: #000; min-width: 100px; }
.rep-total td { background: #E0E0E0; font-weight: 700; color: #000; }
.c-total-label { text-align: right; font-weight: 700; padding-right: 10px; }
</style>
