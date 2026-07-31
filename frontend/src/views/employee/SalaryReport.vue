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
      <div class="report-scroll">
        <table class="rep-sheet" v-if="rows.length">
          <thead>
            <tr class="rep-header">
              <th rowspan="2">工号</th>
              <th rowspan="2">部门</th>
              <th rowspan="2">姓名</th>
              <th rowspan="2">出勤天数</th>
              <th rowspan="2">旷工</th>
              <th rowspan="2">全勤</th>
              <th rowspan="2">绩效</th>
              <th rowspan="2">未出勤<br>天数</th>
              <th colspan="2">应发工资</th>
              <th rowspan="2">加班费</th>
              <th rowspan="2">本月<br>基本工资</th>
              <th rowspan="2">合计<br>工资</th>
              <th rowspan="2">绩效<br>工资</th>
              <th rowspan="2">伙食<br>补助</th>
              <th rowspan="2">全勤/话费<br>补助</th>
              <th rowspan="2">应发<br>工资</th>
              <th rowspan="2">社保<br>扣款</th>
              <th rowspan="2">实发<br>工资</th>
              <th rowspan="2">社保</th>
              <th rowspan="2">实际<br>应发合计</th>
              <th rowspan="2">备注</th>
              <th rowspan="2">上月</th>
            </tr>
            <tr class="rep-header">
              <th>基本工资</th>
              <th>加班小时</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in rows" :key="i">
              <td class="c-center">{{ row.employee_no || '' }}</td>
              <td class="c-center">{{ deptLabel(row.department) }}</td>
              <td class="c-name">{{ row.employee_name || '' }}</td>
              <td class="c-center">{{ row.attend_days || '' }}</td>
              <td class="c-center">{{ row.missed_days || '' }}</td>
              <td class="c-money">{{ fmt(row.attendance_bonus) }}</td>
              <td class="c-money">{{ fmt(row.performance) }}</td>
              <td class="c-center">{{ row.absent_days || '' }}</td>
              <td class="c-money">{{ fmt(row.base_salary) }}</td>
              <td class="c-money">{{ fmtOt(row.overtime_hours) }}</td>
              <td class="c-money">{{ fmt(row.overtime_pay) }}</td>
              <td class="c-money">{{ fmt(row.base_salary) }}</td>
              <td class="c-money">{{ fmt(row.total_salary) }}</td>
              <td class="c-money">{{ fmt(row.performance_wage) }}</td>
              <td class="c-money">{{ fmt(row.meal_subsidy) }}</td>
              <td class="c-money">{{ fmt(row.attendance_phone_subsidy) }}</td>
              <td class="c-money strong">{{ fmt(row.gross) }}</td>
              <td class="c-money">{{ fmt(row.social_deduction) }}</td>
              <td class="c-money strong">{{ fmt(row.net_salary) }}</td>
              <td class="c-money">{{ fmt(row.social_insurance) }}</td>
              <td class="c-money strong">{{ fmt(row.actual_gross) }}</td>
              <td class="c-center">{{ row.remark || '' }}</td>
              <td class="c-money">{{ fmt(row.prev_month_net) }}</td>
            </tr>
          </tbody>
          <tfoot>
            <tr class="rep-total">
              <td colspan="3" class="c-total-label">合计</td>
              <td class="c-center"></td>
              <td class="c-center"></td>
              <td class="c-money">{{ fmt(total.attendance_bonus) }}</td>
              <td class="c-money">{{ fmt(total.performance) }}</td>
              <td class="c-center"></td>
              <td class="c-money">{{ fmt(total.base_salary) }}</td>
              <td class="c-money">{{ fmtOt(total.overtime_hours) }}</td>
              <td class="c-money">{{ fmt(total.overtime_pay) }}</td>
              <td class="c-money">{{ fmt(total.base_salary) }}</td>
              <td class="c-money">{{ fmt(total.total_salary) }}</td>
              <td class="c-money">{{ fmt(total.performance_wage) }}</td>
              <td class="c-money">{{ fmt(total.meal_subsidy) }}</td>
              <td class="c-money">{{ fmt(total.attendance_phone_subsidy) }}</td>
              <td class="c-money">{{ fmt(total.gross) }}</td>
              <td class="c-money">{{ fmt(total.social_deduction) }}</td>
              <td class="c-money">{{ fmt(total.net_salary) }}</td>
              <td class="c-money">{{ fmt(total.social_insurance) }}</td>
              <td class="c-money">{{ fmt(total.actual_gross) }}</td>
              <td class="c-center"></td>
              <td class="c-money">{{ fmt(total.prev_month_net) }}</td>
            </tr>
          </tfoot>
        </table>
        <el-empty v-else description="该月暂无工资记录，请先在「工资管理」生成或录入" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue"
import { getSalaryReport, type SalaryReportRow } from "@/api/salaries"
import { ElMessage } from "element-plus"

const curMonth = ref("")
const report = ref<{ title: string; rows: SalaryReportRow[] }>({ title: "", rows: [] })

const title = computed(() => report.value.title || "工资计算明细表")
const rows = computed(() => report.value.rows)

const total = computed(() => {
  const t = {
    base_salary: 0, overtime_hours: 0, overtime_pay: 0, total_salary: 0,
    attendance_bonus: 0, performance: 0, performance_wage: 0, meal_subsidy: 0,
    attendance_phone_subsidy: 0, gross: 0, social_deduction: 0, net_salary: 0,
    social_insurance: 0, actual_gross: 0, prev_month_net: 0,
  }
  for (const r of rows.value) {
    t.base_salary += r.base_salary || 0
    t.overtime_hours += r.overtime_hours || 0
    t.overtime_pay += r.overtime_pay || 0
    t.total_salary += r.total_salary || 0
    t.attendance_bonus += r.attendance_bonus || 0
    t.performance += r.performance || 0
    t.performance_wage += r.performance_wage || 0
    t.meal_subsidy += r.meal_subsidy || 0
    t.attendance_phone_subsidy += r.attendance_phone_subsidy || 0
    t.gross += r.gross || 0
    t.social_deduction += r.social_deduction || 0
    t.net_salary += r.net_salary || 0
    t.social_insurance += r.social_insurance || 0
    t.actual_gross += r.actual_gross || 0
    t.prev_month_net += r.prev_month_net || 0
  }
  return t
})

const fmt = (v: unknown) => (v === null || v === undefined || v === "") ? "" : Number(v).toFixed(2)
const fmtOt = (v: unknown) => (v && Number(v) !== 0) ? Number(v).toFixed(1) : ""
const deptLabel = (v?: string | null) => {
  if (!v) return ""
  const m: Record<string, string> = { design: "设计部", production: "生产部", installation: "安装部", sales: "销售部", finance: "财务部", admin: "行政部" }
  return m[v] || v
}

async function fetchData() {
  if (!curMonth.value) curMonth.value = new Date().toISOString().slice(0, 7)
  try {
    const r = await getSalaryReport(curMonth.value)
    report.value = { title: r?.title || "", rows: r?.rows || [] }
  } catch (e: unknown) {
    ElMessage.error((e as { message?: string })?.message || "加载报表失败")
  }
}

function handlePrint() {
  const table = document.querySelector('.rep-sheet')
  if (!table) { ElMessage.warning('暂无数据可打印'); return }
  const styleTag = '<style>'
    + '@page { size: A4 landscape; margin: 8mm; }'
    + '* { -webkit-print-color-adjust: exact; print-color-adjust: exact; box-sizing: border-box; }'
    + 'body { font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; margin: 0; padding: 0; }'
    + '.print-title { text-align: center; font-size: 22px; font-weight: 700; padding: 12px 0 10px; }'
    + 'table { width: 100%; border-collapse: collapse; font-size: 10px; }'
    + 'th, td { border: 1px solid #999 !important; padding: 2px 4px !important; text-align: center; }'
    + 'thead { display: table-header-group; } tbody { display: table-row-group; }'
    + 'tr { page-break-inside: avoid; }'
    + 'thead th { background: #f2f2f2 !important; font-weight: 700; }'
    + '.rep-total td { background: #d6e4f0 !important; font-weight: 700; }'
    + '.c-money { text-align: right !important; font-family: "Courier New", monospace; }'
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
.report-scroll { overflow-x: auto; }
.rep-sheet { width: 100%; border-collapse: collapse; white-space: nowrap; }
.rep-sheet th, .rep-sheet td { border: 1px solid #b0b0b0; padding: 3px 5px; font-size: 12px; }
.rep-sheet thead th { background: #f2f2f2; font-weight: 700; color: #303133; text-align: center; line-height: 1.35; }
.c-money { text-align: right; font-family: "SF Mono", "Courier New", monospace; }
.c-money.strong { font-weight: 700; color: #0b7a1b; }
.c-center { text-align: center; }
.c-name { font-weight: 600; color: #303133; }
.rep-total td { background: #d6e4f0; font-weight: 700; color: #303133; }
.c-total-label { text-align: right; padding-right: 10px; }
</style>
