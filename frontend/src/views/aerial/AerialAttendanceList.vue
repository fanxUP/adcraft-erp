<template>
  <div class="page">
    <div class="page-header">
      <h2>🚜 高空作业考勤表</h2>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
        <el-radio-group v-model="targetType" @change="fetchData">
          <el-radio-button value="vehicle">车辆</el-radio-button>
          <el-radio-button value="personnel">人员</el-radio-button>
        </el-radio-group>
        <el-date-picker v-model="curMonth" type="month" value-format="YYYY-MM" placeholder="选择月份" style="width:160px" @change="fetchData" />
        <el-button @click="fetchData">刷新</el-button>
        <el-button type="danger" @click="openCreate">录入考勤</el-button>
        <el-button @click="handlePrint">🖨️ 打印预览</el-button>
      </div>
    </div>

    <!-- 汇总卡片 -->
    <el-row :gutter="12" style="margin-bottom:16px">
      <el-col :span="5"><el-card shadow="never" body-style="padding:16px"><div style="text-align:center"><div style="font-size:28px;font-weight:700;color:#67c23a">{{ totalStats.present }}</div><div style="font-size:13px;color:#909399;margin-top:4px">出勤记录</div></div></el-card></el-col>
      <el-col :span="5"><el-card shadow="never" body-style="padding:16px"><div style="text-align:center"><div style="font-size:28px;font-weight:700;color:#f56c6c">{{ totalStats.absent }}</div><div style="font-size:13px;color:#909399;margin-top:4px">未出勤</div></div></el-card></el-col>
      <el-col :span="5"><el-card shadow="never" body-style="padding:16px"><div style="text-align:center"><div style="font-size:28px;font-weight:700;color:#409eff">{{ totalStats.trips }}</div><div style="font-size:13px;color:#909399;margin-top:4px">趟数合计</div></div></el-card></el-col>
      <el-col :span="5"><el-card shadow="never" body-style="padding:16px"><div style="text-align:center"><div style="font-size:28px;font-weight:700;color:#e6a23c">{{ fmtMoney(totalStats.receivable) }}</div><div style="font-size:13px;color:#909399;margin-top:4px">应收合计</div></div></el-card></el-col>
      <el-col :span="4"><el-card shadow="never" body-style="padding:16px"><div style="text-align:center"><div style="font-size:28px;font-weight:700;color:#67c23a">{{ fmtMoney(totalStats.received) }}</div><div style="font-size:13px;color:#909399;margin-top:4px">实收合计</div></div></el-card></el-col>
    </el-row>

    <!-- 图例 -->
    <div style="margin-bottom:12px;display:flex;gap:16px;font-size:13px;color:#606266;align-items:center;flex-wrap:wrap">
      <span>图例：</span>
      <span><span class="legend-dot" style="background:#b7e4c7;border:1px solid #98d2a8"></span>出勤/出车</span>
      <span><span class="legend-dot" style="background:#a3d0ff;border:1px solid #82b3f0"></span>半天</span>
      <span><span class="legend-dot" style="background:#ffa940;border:1px solid #e09024"></span>加班</span>
      <span><span class="legend-dot" style="background:#fff;border:1px solid #c0c4cc"></span>未出勤</span>
      <span v-if="targetType === 'vehicle'"><span class="legend-dot" style="background:#dee2e6;border:1px solid #b8bcc4"></span>维修</span>
      <span style="color:#909399">· 蓝色「n趟」徽标 = 当日有出车台账</span>
    </div>

    <!-- 考勤矩阵表 -->
    <div class="sheet-wrapper" :style="{ maxHeight: 'calc(100vh - 320px)' }">
      <table class="att-sheet" v-if="matrix.length">
        <thead>
          <tr class="att-header-top">
            <th rowspan="2" class="att-col-sm">#</th>
            <th rowspan="2" class="att-col-name">{{ targetType === 'vehicle' ? '车辆' : '人员' }}</th>
            <th colspan="5" class="att-col-group">作业汇总</th>
            <th :colspan="days.length" class="att-col-group">每日明细（出车/收车 / 状态）</th>
          </tr>
          <tr class="att-header-bottom">
            <th class="att-col-stat">出车<br><span class="overtime-unit">天数</span></th>
            <th class="att-col-stat">趟数</th>
            <th class="att-col-stat">应收</th>
            <th class="att-col-stat">实收</th>
            <th class="att-col-stat overtime-col">毛利<br><span class="overtime-unit">金额</span></th>
            <th v-for="d in days" :key="d" :class="['att-col-day', { today: d === todayDay && monthMatches }]">{{ monthDayCN(d) }}<span class="att-day-week">周{{ weekdayCN(d) }}</span></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, i) in matrix" :key="row.id">
            <td class="cell-center">{{ i + 1 }}</td>
            <td class="cell-name">{{ row.name }}<span class="cell-sub" v-if="row.sub">（{{ row.sub }}）</span></td>
            <td class="cell-stat">{{ row.summary.workDays || '' }}</td>
            <td class="cell-stat">{{ row.summary.trips || '' }}</td>
            <td class="cell-stat money">{{ fmtMoney(row.summary.receivable) }}</td>
            <td class="cell-stat money">{{ fmtMoney(row.summary.received) }}</td>
            <td class="cell-stat money profit">{{ fmtMoney(row.summary.profit) }}</td>
            <td v-for="d in days" :key="d" :class="['cell-day', getDayCellClass(row.days[d])]" @click="handleCellClick(row, d)">
              <template v-if="row.days[d] && row.days[d].status !== 'absent'">
                <div class="day-cell-inner">
                  <div class="day-times">
                    <span class="day-in">{{ fmtTime(row.days[d].check_in_time) }}</span>
                    <span class="day-sep">|</span>
                    <span class="day-out">{{ fmtTime(row.days[d].check_out_time) }}</span>
                  </div>
                  <div v-if="getStatusLabel(row.days[d].status)" class="day-abnormal">{{ getStatusLabel(row.days[d].status) }}</div>
                  <div v-if="Number(row.days[d].overtime_hours)" class="day-overtime">{{ fmtOvertime(row.days[d].overtime_hours) }}<span class="day-overtime-unit">h</span></div>
                </div>
              </template>
              <template v-else-if="row.days[d] && row.days[d].status === 'absent' && Number(row.days[d].overtime_hours)">
                <div class="day-cell-inner">
                  <div class="day-overtime">{{ fmtOvertime(row.days[d].overtime_hours) }}<span class="day-overtime-unit">h</span></div>
                </div>
              </template>
              <div v-else class="day-empty"></div>
              <div v-if="row.dayTripCounts[d]" class="day-ledger-badge">{{ row.dayTripCounts[d] }}趟</div>
            </td>
          </tr>
        </tbody>
        <tfoot>
          <tr class="att-footer">
            <td colspan="2" style="font-weight:700;text-align:right;padding-right:12px">合计</td>
            <td class="cell-stat">{{ totalStats.workDays || '' }}</td>
            <td class="cell-stat">{{ totalStats.trips || '' }}</td>
            <td class="cell-stat money">{{ fmtMoney(totalStats.receivable) }}</td>
            <td class="cell-stat money">{{ fmtMoney(totalStats.received) }}</td>
            <td class="cell-stat money profit">{{ fmtMoney(totalStats.profit) }}</td>
            <td v-for="d in days" :key="d" class="cell-day footer-day">{{ totalDayStats[d] || '' }}</td>
          </tr>
        </tfoot>
      </table>
      <el-empty v-else :description="loading ? '加载中…' : '暂无数据'" />
    </div>

    <!-- 录入/编辑 Dialog -->
    <el-dialog v-model="showDialog" :title="isEditing ? '编辑考勤' : '录入考勤'" width="500px" destroy-on-close :close-on-click-modal="false">
      <el-form :model="form" label-width="110px">
        <el-form-item :label="targetType === 'vehicle' ? '车辆' : '人员'" v-if="!isEditing" required>
          <el-select v-model="form.vehicle_id" v-if="targetType === 'vehicle'" placeholder="选择车辆" filterable style="width:100%">
            <el-option v-for="v in vehicles" :key="v.id" :label="v.plate_number + ' ' + v.vehicle_name" :value="v.id" />
          </el-select>
          <el-select v-else v-model="form.personnel_id" placeholder="选择人员" filterable style="width:100%">
            <el-option v-for="p in personnel" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期" required>
          <el-date-picker v-model="form.att_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
        </el-form-item>
        <el-form-item label="出车/开工">
          <el-date-picker v-model="form.check_in_time" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width:100%" placeholder="出车/开工时间" />
        </el-form-item>
        <el-form-item label="收车/完工">
          <el-date-picker v-model="form.check_out_time" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width:100%" placeholder="收车/完工时间" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" style="width:100%">
            <el-option v-for="o in statusOptions" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="加班时长(小时)">
          <el-input-number v-model="form.overtime_hours" :min="0" :max="24" :precision="1" :step="0.5" style="width:100%" placeholder="加班小时数" />
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
import { ref, computed, onMounted, watch } from "vue"
import { ElMessage } from "element-plus"
import {
  getAerialVehicles, getAerialPersonnel, getAerialLedgers,
  getAerialAttendance, createAerialAttendance, updateAerialAttendance,
  type AerialVehicle, type AerialPersonnel, type AerialLedger,
  type AerialAttendanceRecord, type AerialQueryParams, type AerialAttendanceCreate,
} from "@/api/aerial"
import type { PaginatedData } from "@/types/api"
import { getErrorMessage } from "@/utils/error"

/* ====== state ====== */
const targetType = ref<"vehicle" | "personnel">("vehicle")
const vehicles = ref<AerialVehicle[]>([])
const personnel = ref<AerialPersonnel[]>([])
const attendanceRecords = ref<AerialAttendanceRecord[]>([])
const ledgers = ref<AerialLedger[]>([])
const loading = ref(false)
const curMonth = ref("")
const showDialog = ref(false)
const isEditing = ref(false)
const saving = ref(false)
const editRecord = ref<AerialAttendanceRecord | null>(null)
const form = ref<{
  att_date: string
  vehicle_id: string
  personnel_id: string
  status: string
  check_in_time?: string | null
  check_out_time?: string | null
  overtime_hours?: number | null
  remark?: string
}>({ att_date: "", vehicle_id: "", personnel_id: "", status: "present", check_in_time: null, check_out_time: null, overtime_hours: null, remark: "" })
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

const statusOptions = computed(() => {
  const opts = [
    { label: "出勤", value: "present" },
    { label: "半天", value: "half_day" },
    { label: "加班", value: "overtime" },
    { label: "未出勤", value: "absent" },
  ]
  if (targetType.value === "vehicle") opts.push({ label: "维修", value: "maintenance" })
  return opts
})

interface AttRow {
  id: string
  name: string
  sub: string
  days: Record<number, AerialAttendanceRecord>
  dayTripCounts: Record<number, number>
  summary: { workDays: number; trips: number; receivable: number; received: number; profit: number }
}

const matrix = computed<AttRow[]>(() => {
  const rowsList: Array<AerialVehicle | AerialPersonnel> = targetType.value === "vehicle" ? vehicles.value : personnel.value
  const keyOf = (r: AerialAttendanceRecord | AerialLedger) => targetType.value === "vehicle"
    ? (r as AerialAttendanceRecord).vehicle_id || (r as AerialLedger).aerial_vehicle_id
    : (r as AerialAttendanceRecord).personnel_id || (r as AerialLedger).personnel_id

  // 考勤按对象 id 分组
  const attMap: Record<string, Record<number, AerialAttendanceRecord>> = {}
  for (const rec of attendanceRecords.value) {
    const key = keyOf(rec)
    if (!key) continue
    const day = new Date(rec.att_date).getDate()
    if (!attMap[key]) attMap[key] = {}
    attMap[key][day] = rec
  }
  // 台账按对象 id 分组到天
  const ledgerBy: Record<string, Record<number, AerialLedger[]>> = {}
  for (const lg of ledgers.value) {
    const key = keyOf(lg)
    if (!key) continue
    const day = new Date(lg.work_date).getDate()
    if (!ledgerBy[key]) ledgerBy[key] = {}
    if (!ledgerBy[key][day]) ledgerBy[key][day] = []
    ledgerBy[key][day].push(lg)
  }

  const out: AttRow[] = []
  for (const ent of rowsList) {
    const id = ent.id
    const name = targetType.value === "vehicle"
      ? `${(ent as AerialVehicle).plate_number} ${(ent as AerialVehicle).vehicle_name}`
      : (ent as AerialPersonnel).name
    const sub = targetType.value === "vehicle"
      ? ""
      : personnelTypeLabel((ent as AerialPersonnel).personnel_type || "")
    const daysRec = attMap[id] || {}
    const lmap = ledgerBy[id] || {}
    const dayTripCounts: Record<number, number> = {}
    const summary = { workDays: 0, trips: 0, receivable: 0, received: 0, profit: 0 }
    for (const dStr of Object.keys(lmap)) {
      const d = Number(dStr)
      const list = lmap[d]
      dayTripCounts[d] = list.length
      summary.workDays++
      summary.trips += list.length
      for (const lg of list) {
        summary.receivable += Number(lg.receivable_amount || 0)
        summary.received += Number(lg.received_amount || 0)
        summary.profit += Number(lg.gross_profit || 0)
      }
    }
    out.push({ id, name, sub, days: daysRec, dayTripCounts, summary })
  }
  return out
})

const totalStats = computed(() => {
  const t = { present: 0, absent: 0, workDays: 0, trips: 0, receivable: 0, received: 0, profit: 0 }
  for (const row of matrix.value) {
    for (const d of days.value) {
      const rec = row.days[d]
      if (!rec) continue
      if (rec.status === "absent") t.absent++
      else if (rec.status !== "maintenance") t.present++
    }
    t.workDays += row.summary.workDays
    t.trips += row.summary.trips
    t.receivable += row.summary.receivable
    t.received += row.summary.received
    t.profit += row.summary.profit
  }
  return t
})

const totalDayStats = computed(() => {
  const stats: Record<number, number> = {}
  for (const d of days.value) {
    let count = 0
    for (const row of matrix.value) {
      if (row.days[d] || row.dayTripCounts[d]) count++
    }
    if (count > 0) stats[d] = count
  }
  return stats
})

/* ====== helpers ====== */
const fmtTime = (dt?: string | null) => (dt ? dt.substring(11, 16) : "")
const fmtOvertime = (h: number) => (h ? Number(h).toFixed(1) : "")
const fmtMoney = (v: number) => (v ? Number(v).toFixed(2) : "")
const weekdayCN = (d: number) => {
  const { year, month } = yearMonth.value
  return ["日", "一", "二", "三", "四", "五", "六"][new Date(year, month - 1, d).getDay()]
}
const monthDayCN = (d: number) => `${yearMonth.value.month}月${d}日`
const personnelTypeLabel = (t: string) => {
  const m: Record<string, string> = { driver: "司机", assistant: "随车", operator: "操作员" }
  return m[t] || t
}
const getStatusLabel = (s: string) => {
  const m: Record<string, string> = { half_day: "半天", overtime: "加班", maintenance: "维修" }
  return m[s] || ""
}
const getDayCellClass = (rec?: AerialAttendanceRecord) => {
  if (!rec) return "day-none"
  if (rec.status === "half_day") return "day-half"
  if (rec.status === "absent") return "day-none"
  if (rec.status === "overtime") return "day-overtime-cell"
  if (rec.status === "maintenance") return "day-weekend"
  return "day-normal"
}

/* ====== date helpers ====== */
function getMonthDateRange(ym: string) {
  const [y, m] = ym.split("-").map(Number)
  const last = new Date(y, m, 0).getDate()
  return { date_from: `${ym}-01`, date_to: `${ym}-${String(last).padStart(2, "0")}` }
}

/* ====== data ====== */
async function fetchAll<T>(fetcher: (p: AerialQueryParams) => Promise<PaginatedData<T>>, params: AerialQueryParams) {
  const out: T[] = []
  let page = 1
  const pageSize = 100
  for (;;) {
    const res = await fetcher({ ...params, page, page_size: pageSize })
    const items = (res && res.items) || []
    out.push(...items)
    const total = res?.total ?? 0
    if (out.length >= total || items.length === 0) break
    page++
  }
  return out
}

async function fetchData() {
  if (!curMonth.value) curMonth.value = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}`
  loading.value = true
  try {
    const { date_from, date_to } = getMonthDateRange(curMonth.value)
    if (targetType.value === "vehicle") {
      vehicles.value = await fetchAll<AerialVehicle>(getAerialVehicles, { status: "active" })
    } else {
      personnel.value = await fetchAll<AerialPersonnel>(getAerialPersonnel, { status: "active" })
    }
    const attRes = await getAerialAttendance({ target_type: targetType.value, date_from, date_to, page: 1, page_size: 2000 })
    attendanceRecords.value = attRes?.items || []
    ledgers.value = await fetchAll<AerialLedger>(getAerialLedgers, { date_from, date_to })
  } catch (e: unknown) {
    ElMessage.error(getErrorMessage(e))
  } finally {
    loading.value = false
  }
}

/* ====== cell click ====== */
function handleCellClick(row: AttRow, d: number) {
  const { year, month } = yearMonth.value
  const dateStr = `${year}-${String(month).padStart(2, "0")}-${String(d).padStart(2, "0")}`
  const rec = row.days[d]
  if (rec) {
    isEditing.value = true
    editRecord.value = rec
    form.value = {
      att_date: rec.att_date,
      vehicle_id: rec.vehicle_id || "",
      personnel_id: rec.personnel_id || "",
      status: rec.status,
      check_in_time: rec.check_in_time || null,
      check_out_time: rec.check_out_time || null,
      overtime_hours: rec.overtime_hours ?? null,
      remark: rec.remark || "",
    }
  } else {
    isEditing.value = false
    editRecord.value = null
    form.value = {
      att_date: dateStr,
      vehicle_id: targetType.value === "vehicle" ? row.id : "",
      personnel_id: targetType.value === "personnel" ? row.id : "",
      status: "present",
      check_in_time: null,
      check_out_time: null,
      overtime_hours: null,
      remark: "",
    }
  }
  showDialog.value = true
}

function openCreate() {
  isEditing.value = false
  editRecord.value = null
  form.value = {
    att_date: `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(todayDay).padStart(2, "0")}`,
    vehicle_id: "",
    personnel_id: "",
    status: "present",
    check_in_time: null,
    check_out_time: null,
    overtime_hours: null,
    remark: "",
  }
  showDialog.value = true
}

/* ====== save ====== */
async function handleSave() {
  saving.value = true
  try {
    if (isEditing.value && editRecord.value) {
      await updateAerialAttendance(editRecord.value.id, form.value)
      ElMessage.success("已更新")
    } else {
      const payload: AerialAttendanceCreate = { ...form.value, target_type: targetType.value }
      await createAerialAttendance(payload)
      ElMessage.success("已创建")
    }
    showDialog.value = false
    await fetchData()
  } catch (e: unknown) {
    ElMessage.error(getErrorMessage(e))
  } finally {
    saving.value = false
  }
}

/* ====== print ====== */
function handlePrint() {
  const table = document.querySelector('.att-sheet')
  if (!table) { ElMessage.warning('暂无数据可打印'); return }
  const monthLabel = curMonth.value || ''
  const title = monthLabel ? monthLabel + ' 高空作业考勤表' : '高空作业考勤表'
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
    + '.day-overtime-cell { background: #ffa940 !important; }'
    + '.day-weekend { background: #dee2e6 !important; }'
    + '.cell-stat.money { color: var(--ad-text-secondary); font-weight: 600; }'
    + '.cell-stat.profit { color: #e6a23c; font-weight: 700; }'
    + '.day-overtime { color: #ffa940; font-weight: 600; }'
    + '.day-ledger-badge { font-size: 10px; color: #fff; background: #409eff; border-radius: 2px; padding: 0 3px; display: inline-block; margin-top: 2px; }'
    + 'thead { display: table-header-group; } tbody { display: table-row-group; }'
    + 'tr { page-break-inside: avoid; }'
    + '.day-times { font-size: 11px; color: var(--ad-text-secondary); }'
    + '.day-in { color: #67c23a; } .day-out { color: #409eff; }'
    + '.day-abnormal { font-size: 11px; font-weight: 600; }'
    + '.day-sep { color: #ccc; margin: 0 2px; }'
    + '</style>'
  const html = '<!DOCTYPE html><html><head><meta charset="utf-8"><title>' + title + '</title>'
    + styleTag
    + '</head><body>'
    + '<div class="print-header">' + title + '</div>'
    + table.outerHTML
    + '<script>window.onload=function(){setTimeout(function(){window.print();window.close()},500)}</scr' + 'ipt>'
    + '</body></html>'
  const win = window.open('', '_blank')
  if (win) { win.document.write(html); win.document.close() }
}

onMounted(fetchData)
watch(targetType, () => { showDialog.value = false; fetchData() })
</script>

<style scoped>
.sheet-wrapper { overflow-x: auto; overflow-y: auto; border: 1px solid var(--ad-border); border-radius: 4px; background: var(--ad-card); padding-bottom: 14px; }
.att-sheet { width: 100%; border-collapse: collapse; font-size: 14px; white-space: nowrap; }
.att-sheet th, .att-sheet td { border: 1px solid var(--ad-border); padding: 4px 6px; }
.att-sheet thead th { background: var(--ad-darker); position: sticky; top: 0; z-index: 2; font-weight: 600; color: var(--ad-text); }
.att-sheet thead th.today { background: #ecf5ff; color: #409eff; }
.att-col-sm { min-width: 36px; width: 36px; }
.att-col-name { min-width: 140px; }
.att-col-stat { min-width: 60px; width: 60px; text-align: center; }
.att-col-group { text-align: center; }
.att-col-day { min-width: 72px; width: 72px; text-align: center; font-size: 12px; padding: 4px 2px !important; }
.att-col-day .att-day-week { display: block; font-size: 11px; font-weight: 400; color: var(--ad-text-secondary); line-height: 1.4; }
.att-col-stat.overtime-col { line-height: 1.3; }
.att-col-stat.overtime-col .overtime-unit { font-size: 13px; font-weight: 400; color: var(--ad-text-secondary); display: block; }
.cell-center { text-align: center; }
.cell-name { font-weight: 600; color: var(--ad-text); }
.cell-sub { font-size: 12px; font-weight: 400; color: var(--ad-text-secondary); }
.cell-stat { text-align: center; font-weight: 600; font-size: 15px; }
.cell-stat.money { font-family: "SF Mono", "Courier New", monospace; font-size: 13px; }
.cell-stat.profit { color: #e6a23c; }
.cell-day { cursor: pointer; padding: 3px 4px !important; transition: background 0.15s; }
.cell-day:hover { background: #ecf5ff !important; }
.day-normal { background: #b7e4c7; }
.day-half { background: #a3d0ff; }
.day-overtime-cell { background: #ffa940; }
.day-weekend { background: #dee2e6; }
.day-none { background: var(--ad-card); }
.day-cell-inner { text-align: center; line-height: 1.5; }
.day-times { font-size: 13px; color: var(--ad-text-secondary); font-family: "SF Mono", "Courier New", monospace; }
.day-in { color: #67c23a; }
.day-sep { color: #dcdfe6; margin: 0 2px; }
.day-out { color: #409eff; }
.day-abnormal { font-size: 12px; font-weight: 600; margin-top: 1px; color: var(--ad-text-secondary); }
.day-empty { text-align: center; color: #dcdfe6; font-size: 14px; }
.day-overtime { color: #e09024; font-weight: 600; font-family: "SF Mono", "Courier New", monospace; font-size: 13px; }
.day-overtime-cell .day-overtime { color: #fff; }
.day-overtime-unit { font-size: 11px; margin-left: 1px; }
.day-ledger-badge { font-size: 10px; color: #fff; background: #409eff; border-radius: 2px; padding: 0 4px; display: inline-block; margin-top: 2px; line-height: 1.5; }
.att-footer td { background: var(--ad-darker); font-weight: 600; color: var(--ad-text); }
.att-footer .footer-day { text-align: center; color: #67c23a; font-size: 13px; }
.legend-dot { display: inline-block; width: 14px; height: 14px; border-radius: 3px; vertical-align: middle; margin-right: 4px; }
</style>
