<template>
  <div class="page">
    <div class="page-header">
      <h2><el-icon><Calendar /></el-icon> 考勤表</h2>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
        <el-date-picker v-model="curMonth" type="month" value-format="YYYY-MM" placeholder="选择月份" style="width:160px" @change="fetchData" />
        <el-select v-model="fEmp" placeholder="全部员工" clearable filterable style="width:200px" @change="fetchData">
          <el-option v-for="e in employees" :key="e.id" :label="e.name+' ('+e.employee_no+')'" :value="e.id" />
        </el-select>
        <el-button @click="fetchData">刷新</el-button>
        <el-button type="danger" @click="openCreate">录入打卡</el-button>
        <el-button @click="handlePrint"><el-icon><Printer /></el-icon> 打印预览</el-button>
      </div>
    </div>

    <!-- 汇总卡片 -->
    <el-row :gutter="12" style="margin-bottom:16px">
      <el-col :span="5"><el-card shadow="never" body-style="padding:16px"><div style="text-align:center"><div style="font-size:28px;font-weight:700;color:var(--el-color-success)">{{totalStats.present}}</div><div style="font-size:13px;color:var(--el-text-color-secondary);margin-top:4px">总出勤</div></div></el-card></el-col>
      <el-col :span="5"><el-card shadow="never" body-style="padding:16px"><div style="text-align:center"><div style="font-size:28px;font-weight:700;color:var(--el-color-danger)">{{totalStats.absent}}</div><div style="font-size:13px;color:var(--el-text-color-secondary);margin-top:4px">总未出勤</div></div></el-card></el-col>
      <el-col :span="5"><el-card shadow="never" body-style="padding:16px"><div style="text-align:center"><div style="font-size:28px;font-weight:700;color:var(--el-color-warning)">{{totalStats.late}}</div><div style="font-size:13px;color:var(--el-text-color-secondary);margin-top:4px">总迟到</div></div></el-card></el-col>
      <el-col :span="5"><el-card shadow="never" body-style="padding:16px"><div style="text-align:center"><div style="font-size:28px;font-weight:700;color:var(--el-text-color-secondary)">{{totalStats.unauth}}</div><div style="font-size:13px;color:var(--el-text-color-secondary);margin-top:4px">总矿工</div></div></el-card></el-col>
      <el-col :span="4"><el-card shadow="never" body-style="padding:16px"><div style="text-align:center"><div style="font-size:28px;font-weight:700;color:var(--el-color-warning)">{{totalStats.overtimeHours ? totalStats.overtimeHours.toFixed(1) : 0}}</div><div style="font-size:13px;color:var(--el-text-color-secondary);margin-top:4px">总加班(小时)</div></div></el-card></el-col>
    </el-row>

    <!-- 图例 -->
    <div style="margin-bottom:12px;display:flex;gap:16px;font-size:13px;color:var(--ad-text-secondary);align-items:center;flex-wrap:wrap">
      <span>图例：</span>
      <span><span class="legend-dot" style="background:#b7e4c7;border:1px solid #98d2a8"></span>出勤</span>
      <span><span class="legend-dot" style="background:#a3d0ff;border:1px solid #82b3f0"></span>半天</span>
      <span><span class="legend-dot" style="background:#ffe69c;border:1px solid #e8c95c"></span>迟到/早退</span>
      <span><span class="legend-dot" style="background:#f5c2c7;border:1px solid #e29aa0"></span>旷工/缺卡</span>
      <span><span class="legend-dot" style="background:var(--ad-card);border:1px solid var(--ad-border)"></span>未出勤</span>
      <span><span class="legend-dot" style="background:var(--el-color-warning);border:1px solid #e09024"></span>加班</span>
      <span><span class="legend-dot" style="background:#dee2e6;border:1px solid #b8bcc4"></span>休息日</span>
    </div>

    <!-- 考勤矩阵表 -->
    <div class="sheet-wrapper" :style="{ maxHeight: 'calc(100vh - 320px)' }">
      <table class="att-sheet" v-if="matrix.length">
        <thead>
          <tr class="att-header-top">
            <th rowspan="2" class="att-col-sm">#</th>
            <th rowspan="2" class="att-col-name">姓名</th>
            <th rowspan="2" class="att-col-dept">部门</th>
            <th colspan="5" class="att-col-group">出勤汇总</th>
            <th :colspan="days.length" class="att-col-group">每日明细（签到/签退 / 状态）</th>
          </tr>
          <tr class="att-header-bottom">
            <th class="att-col-stat">出勤</th>
            <th class="att-col-stat">未出勤</th>
            <th class="att-col-stat">迟到</th>
            <th class="att-col-stat">矿工</th>
            <th class="att-col-stat overtime-col">加班<br><span class="overtime-unit">小时</span></th>
            <th v-for="d in days" :key="d" :class="['att-col-day', { weekend: isWeekend(d), today: d === todayDay && monthMatches }]">{{ monthDayCN(d) }}<span class="att-day-week">周{{ weekdayCN(d) }}</span></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, i) in matrix" :key="row.employee.id">
            <td class="cell-center">{{ i + 1 }}</td>
            <td class="cell-name">{{ row.employee.name }}</td>
            <td class="cell-dept">{{ deptLabel(row.employee.department) }}</td>
            <td class="cell-stat present">{{ row.summary.present }}</td>
            <td class="cell-stat absent" :class="{ highlight: row.summary.absent > 0 }">{{ row.summary.absent || '' }}</td>
            <td class="cell-stat late" :class="{ highlight: row.summary.late > 0 }">{{ row.summary.late || '' }}</td>
            <td class="cell-stat unauth" :class="{ highlight: row.summary.unauth > 0 }">{{ row.summary.unauth || '' }}</td>
            <td class="cell-stat overtime">{{ fmtOvertime(row.summary.overtimeHours) }}</td>
            <td v-for="d in days" :key="d" :class="['cell-day', getDayCellClass(row, d)]" @click="handleCellClick(row.employee, d)">
              <template v-if="row.days[d] && !isAbsent(row.days[d])">
                <div class="day-cell-inner">
                  <div class="day-times">
                    <span class="day-in">{{ fmtTime(row.days[d].check_in_time) }}</span>
                    <span class="day-sep">|</span>
                    <span class="day-out">{{ fmtTime(row.days[d].check_out_time) }}</span>
                  </div>
                  <div v-if="isAbnormal(row.days[d])" class="day-abnormal">{{ getAbnormalLabel(row.days[d]) }}</div>
                </div>
              </template>
              <template v-else-if="row.days[d] && isAbsent(row.days[d]) && row.days[d].overtime_hours">
                <div class="day-cell-inner">
                  <div class="day-overtime">{{ fmtOvertime(row.days[d].overtime_hours) }}<span class="day-overtime-unit">h</span></div>
                </div>
              </template>
              <div v-else class="day-empty">{{ isWeekend(d) ? '休' : '' }}</div>
            </td>
          </tr>
        </tbody>
        <tfoot>
          <tr class="att-footer">
            <td colspan="3" style="font-weight:700;text-align:right;padding-right:12px">合计</td>
            <td class="cell-stat present">{{ totalStats.present }}</td>
            <td class="cell-stat absent">{{ totalStats.absent || '' }}</td>
            <td class="cell-stat late">{{ totalStats.late || '' }}</td>
            <td class="cell-stat unauth">{{ totalStats.unauth || '' }}</td>
            <td class="cell-stat overtime">{{ totalStats.overtimeHours ? totalStats.overtimeHours.toFixed(1) : '' }}</td>
            <td v-for="d in days" :key="d" class="cell-day footer-day">{{ totalDayStats[d] || '' }}</td>
          </tr>
        </tfoot>
      </table>
      <el-empty v-else description="暂无数据" />
    </div>

    <!-- 录入/编辑 Dialog -->
    <el-dialog v-model="showDialog" :title="isEditing?'编辑打卡':'录入打卡'" width="500px" @closed="form={employee_id:'',date:'',check_in_time:null,check_out_time:null,check_in_status:'normal',check_out_status:'normal',overtime_hours:null,remark:''}" :close-on-click-modal="false">
      <el-form :model="form" label-width="110px">
        <el-form-item label="员工" v-if="!isEditing" required>
          <el-select v-model="form.employee_id" placeholder="选择员工" filterable style="width:100%">
            <el-option v-for="e in employees" :key="e.id" :label="e.name+' ('+e.employee_no+')'" :value="e.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期" required>
          <el-date-picker v-model="form.date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
        </el-form-item>
        <el-form-item label="签到时间">
          <el-date-picker v-model="form.check_in_time" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width:100%" placeholder="选择签到时间" />
        </el-form-item>
        <el-form-item label="加班时长(小时)">
          <el-input-number v-model="form.overtime_hours" :min="0" :max="24" :precision="1" :step="0.5" style="width:100%" placeholder="加班小时数" />
        </el-form-item>
        <el-form-item label="签到状态">
          <el-select v-model="form.check_in_status" style="width:100%">
            <el-option label="出勤" value="normal" /><el-option label="半天" value="half_day" /><el-option label="迟到" value="late" /><el-option label="未出勤" value="absent" /><el-option label="旷工" value="missed" />
          </el-select>
        </el-form-item>
        <el-form-item label="签退时间">
          <el-date-picker v-model="form.check_out_time" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width:100%" placeholder="选择签退时间" />
        </el-form-item>
        <el-form-item label="签退状态">
          <el-select v-model="form.check_out_status" style="width:100%">
            <el-option label="正常" value="normal" /><el-option label="早退" value="early" /><el-option label="半天" value="half_day" /><el-option label="缺卡" value="missed" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog=false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { Calendar, Printer } from '@element-plus/icons-vue'
import { ref, computed, onMounted } from "vue"
import { getAttendanceRecords, createAttendanceRecord, updateAttendanceRecord, getAttendanceEmployees, type AttendanceRecordItem, type EmployeeOption } from "@/api/attendance"
import { ElMessage } from "element-plus"

/* ====== state ====== */
const employees = ref<EmployeeOption[]>([])
const allRecords = ref<AttendanceRecordItem[]>([])
const loading = ref(false)
const curMonth = ref("")
const fEmp = ref("")
const showDialog = ref(false)
const isEditing = ref(false)
const saving = ref(false)
const editRecord = ref<AttendanceRecordItem | null>(null)
const form = ref<{ employee_id: string; date: string; check_in_time?: string | null; check_out_time?: string | null; check_in_status?: string; check_out_status?: string; overtime_hours?: number | null; remark?: string | null }>({ employee_id: "", date: "", check_in_time: null, check_out_time: null, check_in_status: "normal", check_out_status: "normal", overtime_hours: null, remark: "" })
const today = new Date()
const todayDay = today.getDate()

/* ====== computed ====== */
const monthMatches = computed(() => {
  const m = curMonth.value
  return m === `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}`
})

const yearMonth = computed(() => {
  if (!curMonth.value) return { year: 0, month: 0 }
  const [y, m] = curMonth.value.split("-").map(Number)
  return { year: y, month: m }
})

const days = computed(() => {
  if (!yearMonth.value.year) return []
  const { year, month } = yearMonth.value
  return Array.from({ length: new Date(year, month, 0).getDate() }, (_, i) => i + 1)
})

const filteredEmps = computed(() => {
  if (!fEmp.value) return employees.value
  return employees.value.filter(e => e.id === fEmp.value)
})

interface MatrixRow {
  employee: EmployeeOption
  days: Record<number, AttendanceRecordItem>
  summary: { present: number; absent: number; late: number; unauth: number; overtimeHours: number }
}

const matrix = computed<MatrixRow[]>(() => {
  const map: Record<string, Record<number, AttendanceRecordItem>> = {}
  for (const rec of allRecords.value) {
    const day = new Date(rec.date).getDate()
    if (!map[rec.employee_id]) map[rec.employee_id] = {}
    map[rec.employee_id][day] = rec
  }
  const rows: MatrixRow[] = []
  for (const emp of filteredEmps.value) {
    const empDays = map[emp.id] || {}
    const summary = { present: 0, absent: 0, late: 0, unauth: 0, overtimeHours: 0 }
    for (const d of days.value) {
      const rec = empDays[d]
      if (!rec) {
        if (!isWeekend(d)) summary.absent++
        continue
      }
      if (rec.check_in_status === "half_day" || rec.check_out_status === "half_day") summary.present += 0.5
      else if (rec.check_in_status === "normal") summary.present++
      if (rec.check_in_status === "late") summary.late++
      if (rec.check_in_status === "absent") summary.absent++
      if (rec.check_in_status === "missed") summary.unauth++
      else if (rec.check_out_status === "missed" && rec.check_in_status !== "missed") summary.unauth++
      if (rec.overtime_hours) summary.overtimeHours += Number(rec.overtime_hours)
    }
    rows.push({ employee: emp, days: empDays, summary })
  }
  return rows
})

const totalStats = computed(() => {
  const t = { present: 0, absent: 0, late: 0, unauth: 0, overtimeHours: 0 }
  for (const row of matrix.value) {
    t.present += row.summary.present
    t.absent += row.summary.absent
    t.late += row.summary.late
    t.unauth += row.summary.unauth
    t.overtimeHours += row.summary.overtimeHours
  }
  return t
})

const totalDayStats = computed(() => {
  const stats: Record<number, number> = {}
  for (const d of days.value) {
    let count = 0
    for (const row of matrix.value) {
      if (row.days[d]) count++
    }
    if (count > 0) stats[d] = count
  }
  return stats
})

/* ====== helpers ====== */
const deptLabel = (v?: string | null) => {
  if (!v) return "-"
  const m: Record<string, string> = { design: "设计部", production: "生产部", installation: "安装部", sales: "销售部", finance: "财务部", admin: "行政部" }
  return m[v] || v
}
const fmtTime = (dt?: string | null) => dt ? dt.substring(11, 16) : ""
const fmtOvertime = (h: number) => h ? h.toFixed(1) : ""
const isWeekend = (d: number) => {
  const { year, month } = yearMonth.value
  const day = new Date(year, month - 1, d).getDay()
  return day === 0 || day === 6
}
const weekdayCN = (d: number) => {
  const { year, month } = yearMonth.value
  return ["日", "一", "二", "三", "四", "五", "六"][new Date(year, month - 1, d).getDay()]
}
const monthDayCN = (d: number) => `${yearMonth.value.month}月${d}日`
const isAbsent = (rec: AttendanceRecordItem) => rec.check_in_status === "absent" || rec.check_out_status === "absent"
const isAbnormal = (rec: AttendanceRecordItem) => (rec.check_in_status !== "normal" && rec.check_in_status !== "half_day") || (rec.check_out_status !== "normal" && rec.check_out_status !== "half_day")
const getAbnormalLabel = (rec: AttendanceRecordItem) => {
  if (rec.check_in_status === "half_day" || rec.check_out_status === "half_day") return "半天"
  const parts: string[] = []
  if (rec.check_in_status === "late") parts.push("迟到")
  if (rec.check_in_status === "missed") parts.push("缺签到")
  if (rec.check_out_status === "early") parts.push("早退")
  if (rec.check_out_status === "missed") parts.push("缺签退")
  return parts.join("、") || ""
}
const getDayCellClass = (row: MatrixRow, d: number) => {
  const rec = row.days[d]
  if (!rec) {
    if (isWeekend(d)) return "day-weekend"
    return "day-none"
  }
  if (rec.check_in_status === "half_day" || rec.check_out_status === "half_day") return "day-half"
  if (rec.check_in_status === "absent" || rec.check_out_status === "absent") return "day-none"
  if (rec.check_in_status === "late" || rec.check_out_status === "early") return "day-warning"
  if (rec.check_in_status === "missed" || rec.check_out_status === "missed") return "day-danger"
  return "day-normal"
}

/* ====== date helpers ====== */
function getMonthDateRange(ym: string) {
  const [y, m] = ym.split("-").map(Number)
  const last = new Date(y, m, 0).getDate()
  return { date_from: `${ym}-01`, date_to: `${ym}-${String(last).padStart(2, "0")}` }
}

/* ====== data ====== */
async function fetchData() {
  if (!curMonth.value) { curMonth.value = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}` }
  loading.value = true
  try {
    const { date_from, date_to } = getMonthDateRange(curMonth.value)
    const r = await getAttendanceRecords({ date_from, date_to, page: 1, page_size: 1000 })
    allRecords.value = r?.items || []
  } finally { loading.value = false }
}
async function loadEmps() { employees.value = (await getAttendanceEmployees()) || [] }

function handleCellClick(emp: EmployeeOption, d: number) {
  const rec = allRecords.value.find(r => r.employee_id === emp.id && new Date(r.date).getDate() === d)
  if (rec) {
    isEditing.value = true
    editRecord.value = rec
    form.value = { employee_id: emp.id, date: rec.date, check_in_time: rec.check_in_time, check_out_time: rec.check_out_time, check_in_status: rec.check_in_status, check_out_status: rec.check_out_status, overtime_hours: rec.overtime_hours ?? null, remark: rec.remark }
  } else {
    isEditing.value = false
    editRecord.value = null
    const { year, month } = yearMonth.value
    const dateStr = `${year}-${String(month).padStart(2, "0")}-${String(d).padStart(2, "0")}`
    form.value = { employee_id: emp.id, date: dateStr, check_in_time: null, check_out_time: null, check_in_status: "normal", check_out_status: "normal", overtime_hours: null, remark: "" }
  }
  showDialog.value = true
}

function openCreate() {
  isEditing.value = false
  editRecord.value = null
  form.value = { employee_id: "", date: "", check_in_time: null, check_out_time: null, check_in_status: "normal", check_out_status: "normal", overtime_hours: null, remark: "" }
  showDialog.value = true
}

function handlePrint() {
  const table = document.querySelector('.att-sheet')
  if (!table) { ElMessage.warning('暂无数据可打印'); return }
  const monthLabel = curMonth.value || ''
  const title = monthLabel ? monthLabel + ' 考勤表' : '考勤表'
  const styleTag = '<style>'
    + '@page { size: landscape; margin: 8mm; }'
    + '* { -webkit-print-color-adjust: exact; print-color-adjust: exact; box-sizing: border-box; }'
    + 'body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; padding: 0; margin: 0; }'
    + '.print-header { text-align: center; font-size: 18px; font-weight: 700; padding: 14px 0 10px; }'
    + 'table { width: 100%; border-collapse: collapse; font-size: 12px; }'
    + 'th, td { border: 1px solid #ccc; padding: 3px 5px; text-align: center; }'
    + 'thead th { background: #f5f7fa !important; font-weight: 600; }'
    + '.day-normal { background: #b7e4c7 !important; }'
    + '.day-half { background: #a3d0ff !important; }'
    + '.day-warning { background: #ffe69c !important; }'
    + '.day-danger { background: #f5c2c7 !important; }'
    + '.day-weekend { background: #dee2e6 !important; }'
    + '.cell-stat.present { color: var(--el-color-success); font-weight: 700; }'
    + '.cell-stat.overtime { color: var(--el-color-warning); font-weight: 700; }'
    + '.day-overtime { color: var(--el-color-warning); font-weight: 600; }'
    + 'thead { display: table-header-group; } tbody { display: table-row-group; }'
    + 'tr { page-break-inside: avoid; }'
    + '.day-times { font-size: 11px; color: var(--ad-text-secondary); }'
    + '.day-in { color: var(--el-color-success); } .day-out { color: var(--el-color-primary); }'
    + '.day-abnormal { font-size: 11px; font-weight: 600; }'
    + '.day-sep { color: #ccc; margin: 0 2px; }'
    + '</style>'
  const html = '<!DOCTYPE html><html><head><meta charset="utf-8"><title>'+title+'</title>'
    + styleTag
    + '</head><body>'
    + '<div class="print-header">'+title+'</div>'
    + table.outerHTML
    + '<script>window.onload=function(){setTimeout(function(){window.print();window.close()},500)}</scr'+'ipt>'
    + '</body></html>'
  const win = window.open('', '_blank')
  if (win) { win.document.write(html); win.document.close() }
}

async function handleSave() {
  saving.value = true
  try {
    if (isEditing.value && editRecord.value) { await updateAttendanceRecord(editRecord.value.id, form.value); ElMessage.success("已更新") }
    else { await createAttendanceRecord(form.value); ElMessage.success("已创建") }
    showDialog.value = false
    await fetchData()
  } catch (e: unknown) { ElMessage.error((e as { message?: string })?.message || "保存失败") }
  finally { saving.value = false }
}

onMounted(async () => {
  await loadEmps()
  await fetchData()
})
</script>

<style scoped>
.sheet-wrapper { overflow-x: auto; overflow-y: auto; border: 1px solid var(--ad-border); border-radius: 4px; background: var(--ad-card); padding-bottom: 14px; }
.att-sheet { width: 100%; border-collapse: collapse; font-size: 14px; white-space: nowrap; }
.att-sheet th, .att-sheet td { border: 1px solid var(--ad-border); padding: 4px 6px; }
.att-sheet thead th { background: var(--ad-darker); position: sticky; top: 0; z-index: 2; font-weight: 600; color: var(--ad-text); }
.att-sheet thead th.weekend { background: var(--ad-darker); color: var(--ad-text-secondary); }
.att-sheet thead th.today { background: var(--ad-accent-glow); color: var(--el-color-primary); }
.att-col-sm { min-width: 36px; width: 36px; }
.att-col-name { min-width: 70px; }
.att-col-dept { min-width: 60px; }
.att-col-stat { min-width: 42px; width: 42px; text-align: center; }
.att-col-group { text-align: center; }
.att-col-day { min-width: 72px; width: 72px; text-align: center; font-size: 12px; padding: 4px 2px !important; }
.att-col-day .att-day-week { display: block; font-size: 11px; font-weight: 400; color: var(--el-text-color-secondary); line-height: 1.4; }
.cell-center { text-align: center; }
.cell-name { font-weight: 600; color: var(--ad-text); }
.cell-dept { color: var(--ad-text-secondary); }
.cell-stat { text-align: center; font-weight: 600; font-size: 15px; }
.cell-stat.present { color: var(--el-color-success); }
.cell-stat.late { color: var(--el-text-color-secondary); }
.cell-stat.late.highlight { color: var(--el-color-warning); }
.cell-stat.absent { color: var(--el-text-color-secondary); }
.cell-stat.absent.highlight { color: var(--el-color-danger); }
.cell-stat.unauth { color: var(--el-text-color-secondary); }
.cell-stat.unauth.highlight { color: var(--el-color-danger); }
.cell-stat.overtime { color: var(--el-color-warning); font-family: 'SF Mono', 'Courier New', monospace; }
.att-col-stat.overtime-col { line-height: 1.3; }
.att-col-stat.overtime-col .overtime-unit { font-size: 13px; font-weight: 400; color: var(--el-text-color-secondary); display: block; }

.cell-day { cursor: pointer; padding: 3px 4px !important; transition: background 0.15s; }
.cell-day:hover { background: #ecf5ff !important; }
.day-normal { background: #b7e4c7; }
.day-half { background: #a3d0ff; }

.day-warning { background: #ffe69c; }
.day-danger { background: #f5c2c7; }
.day-weekend { background: #dee2e6; }
.day-none { background: var(--ad-card); }
.day-cell-inner { text-align: center; line-height: 1.5; }
.day-times { font-size: 13px; color: var(--ad-text-secondary); font-family: "SF Mono", "Courier New", monospace; }
.day-in { color: var(--el-color-success); }
.day-sep { color: #dcdfe6; margin: 0 2px; }
.day-out { color: var(--el-color-primary); }
.day-abnormal { font-size: 12px; font-weight: 600; margin-top: 1px; }
.day-warning .day-abnormal { color: var(--el-color-warning); }
.day-danger .day-abnormal { color: var(--el-color-danger); }
.day-empty { text-align: center; color: #dcdfe6; font-size: 14px; }
.day-overtime { color: var(--el-color-warning); font-weight: 600; font-family: "SF Mono", "Courier New", monospace; font-size: 13px; }
.day-overtime-unit { font-size: 11px; margin-left: 1px; }
.att-footer td { background: var(--ad-darker); font-weight: 600; color: var(--ad-text); }
.att-footer .footer-day { text-align: center; color: var(--el-color-success); font-size: 13px; }
.legend-dot { display: inline-block; width: 14px; height: 14px; border-radius: 3px; vertical-align: middle; margin-right: 4px; }
/* overtime now inside summary group */


</style>
