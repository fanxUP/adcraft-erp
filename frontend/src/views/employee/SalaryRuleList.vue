<template>
  <div class="page">
    <div class="page-header">
      <h2>⚙️ 工资规则</h2>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
        <el-select v-model="fEmp" placeholder="全部员工" clearable filterable style="width:200px">
          <el-option v-for="e in employees" :key="e.id" :label="e.name+' ('+e.employee_no+')'" :value="e.id" />
        </el-select>
        <el-select v-model="fDept" placeholder="部门筛选" clearable style="width:130px">
          <el-option v-for="d in DEPTS" :key="d.value" :label="d.label" :value="d.value" />
        </el-select>
        <el-button @click="fetchData">刷新</el-button>
        <el-button type="danger" @click="openBatchEdit">批量设置</el-button>
      </div>
    </div>

    <!-- 汇总 -->
    <el-row :gutter="16" style="margin-bottom:16px">
      <el-col :span="8"><el-card shadow="never" body-style="padding:16px"><div style="text-align:center"><div style="font-size:28px;font-weight:700;color:#409eff">{{setRows.length}}</div><div style="font-size:13px;color:#909399;margin-top:4px">已设置规则人数</div></div></el-card></el-col>
      <el-col :span="8"><el-card shadow="never" body-style="padding:16px"><div style="text-align:center"><div style="font-size:28px;font-weight:700;color:#67c23a">{{totalBase.toFixed(2)}}</div><div style="font-size:13px;color:#909399;margin-top:4px">月工资标准合计/月</div></div></el-card></el-col>
      <el-col :span="8"><el-card shadow="never" body-style="padding:16px"><div style="text-align:center"><div style="font-size:28px;font-weight:700;color:#f56c6c">{{totalDeduction.toFixed(2)}}</div><div style="font-size:13px;color:#909399;margin-top:4px">社保金额合计/月</div></div></el-card></el-col>
    </el-row>

    <!-- 工资规则表 -->
    <div class="sheet-wrapper" :style="{ maxHeight: 'calc(100vh - 320px)' }">
      <table class="rule-sheet" v-if="list.length">
        <thead>
          <tr>
            <th class="col-sm">#</th>
            <th v-for="c in sortableCols" :key="c.key" :class="[c.cls, 'sortable', { 'sort-active': sortKey === c.key }]" @click="setSort(c.key)">
              {{ c.label }}<span v-if="sortKey === c.key" class="sort-arrow">{{ sortDir === 'asc' ? '▲' : '▼' }}</span>
            </th>
            <th class="col-op">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, i) in sortedList" :key="row.id">
            <td class="cell-center">{{ i + 1 }}</td>
            <td>{{ row.employee_no || '-' }}</td>
            <td class="cell-name">{{ row.employee_name || '-' }}</td>
            <td>{{ deptLabel(row.employee_id) }}</td>
            <td class="cell-date">{{ row.effective_date }}</td>
            <td class="cell-num"><strong>{{ fmt(row.base_salary) }}</strong></td>
            <td class="cell-num deduction">{{ fmt(row.social_insurance) }}</td>
            <td class="cell-op">
              <template v-if="row.id">
                <el-button text type="primary" size="small" @click="openEdit(row)">编辑</el-button>
                <el-button text type="danger" size="small" @click="handleDelete(row)">删除</el-button>
              </template>
              <el-button v-else text type="primary" size="small" @click="openAdd(row)">设置</el-button>
            </td>
          </tr>
        </tbody>
      </table>
      <el-empty v-else description="暂无数据，请先设置员工工资规则" :image-size="80" />
    </div>

    <!-- 编辑 Dialog -->
    <el-dialog v-model="showDialog" :title="'工资规则 - ' + form.employee_name" width="760px" top="3vh">
      <el-form :model="form" label-width="110px" label-position="top" style="display:grid;grid-template-columns:1fr 1fr;gap:0 20px">
        <el-form-item label="员工" v-if="!isEditing"><el-select v-model="form.employee_id" filterable style="width:100%"><el-option v-for="e in employees" :key="e.id" :label="e.name+' ('+e.employee_no+')'" :value="e.id" /></el-select></el-form-item>
        <el-form-item label="生效日期" required><el-date-picker v-model="form.effective_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
        <el-form-item label="月工资标准 (元)"><el-input-number v-model="form.base_salary" :min="0" :precision="2" style="width:100%" /></el-form-item>
        <el-form-item label="社保金额 (元)"><el-input-number v-model="form.social_insurance" :min="0" :precision="2" style="width:100%" /></el-form-item>
        <el-form-item label="备注" style="grid-column:1/3"><el-input v-model="form.remark" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showDialog=false">取消</el-button><el-button type="primary" @click="handleSave" :loading="saving">保存</el-button></template>
    </el-dialog>

    <!-- 批量设置 Dialog -->
    <el-dialog v-model="showBatchDialog" title="批量设置工资规则" width="560px">
      <el-form :model="batchForm" label-width="100px">
        <el-form-item label="适用员工" required>
          <el-select v-model="batchForm.employee_ids" multiple filterable style="width:100%" placeholder="选择需要设置规则的员工">
            <el-option v-for="e in employees" :key="e.id" :label="e.name+' ('+e.employee_no+')'" :value="e.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="生效日期" required>
          <el-date-picker v-model="batchForm.effective_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
        </el-form-item>
        <el-divider>统一设置以下标准（留空则不修改）</el-divider>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
          <el-form-item label="月工资标准"><el-input-number v-model="batchForm.base_salary" :min="0" :precision="2" style="width:100%" /></el-form-item>
          <el-form-item label="社保金额"><el-input-number v-model="batchForm.social_insurance" :min="0" :precision="2" style="width:100%" /></el-form-item>
        </div>
      </el-form>
      <template #footer><el-button @click="showBatchDialog=false">取消</el-button><el-button type="primary" @click="handleBatchSave" :loading="batchSaving">批量保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue"
import { getSalaryRules, createSalaryRule, updateSalaryRule, deleteSalaryRule } from "@/api/salaryRules"
import { getAttendanceEmployees, type EmployeeOption } from "@/api/attendance"
import { ElMessage, ElMessageBox } from "element-plus"

const DEPTS = [{ value: "design", label: "设计部" }, { value: "production", label: "生产部" }, { value: "installation", label: "安装部" }, { value: "sales", label: "销售部" }, { value: "finance", label: "财务部" }, { value: "admin", label: "行政部" }]

/* ====== state ====== */
interface RuleRow {
  employee_id: string
  employee_no: string
  employee_name: string
  id?: string
  effective_date: string
  base_salary?: number | null
  social_insurance?: number | null
  remark?: string
}
const list = ref<RuleRow[]>([])
const employees = ref<EmployeeOption[]>([])
const loading = ref(false)
const fEmp = ref("")
const fDept = ref("")
const showDialog = ref(false)
const isEditing = ref(false)
const saving = ref(false)
const editId = ref("")

const initForm = {
  employee_id: "", effective_date: "", base_salary: 0,
  social_insurance: null, remark: "", employee_name: "",
}
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const form = ref<any>({ ...initForm })

/* batch */
const showBatchDialog = ref(false)
const batchSaving = ref(false)
const initBatchForm = {
  employee_ids: [], effective_date: "", base_salary: null, social_insurance: null,
}
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const batchForm = ref<any>({ ...initBatchForm })

/* ====== helpers ====== */
const fmt = (v: unknown) => v != null ? Number(v).toFixed(2) : "-"
const deptLabel = (eid: string) => {
  const emp = employees.value.find(e => e.id === eid)
  if (!emp || !emp.department) return "-"
  const d = DEPTS.find(d => d.value === emp.department)
  return d ? d.label : emp.department
}

/* ====== sorting ====== */
const sortableCols = [
  { key: "employee_no", label: "工号", cls: "col-emp" },
  { key: "employee_name", label: "姓名", cls: "col-emp" },
  { key: "department", label: "部门", cls: "col-dept" },
  { key: "effective_date", label: "生效日期", cls: "col-date" },
  { key: "base_salary", label: "月工资标准", cls: "col-num" },
  { key: "social_insurance", label: "社保金额", cls: "col-num" },
] as const
const sortKey = ref<string>("employee_no")
const sortDir = ref<"asc" | "desc">("asc")

const sortVal = (row: RuleRow, key: string): string | number => {
  switch (key) {
    case "employee_no": return row.employee_no || ""
    case "employee_name": return row.employee_name || ""
    case "department": return deptLabel(row.employee_id)
    case "effective_date": return row.effective_date || ""
    case "base_salary": return row.base_salary ?? 0
    case "social_insurance": return row.social_insurance ?? 0
    default: return ""
  }
}
function setSort(key: string) {
  if (sortKey.value === key) sortDir.value = sortDir.value === "asc" ? "desc" : "asc"
  else { sortKey.value = key; sortDir.value = "asc" }
}

/* ====== filters / sorted ====== */
const filteredList = computed(() => {
  let rows = list.value
  if (fEmp.value) rows = rows.filter(r => r.employee_id === fEmp.value)
  if (fDept.value) {
    const deptEmps = employees.value.filter(e => e.department === fDept.value).map(e => e.id)
    rows = rows.filter(r => deptEmps.includes(r.employee_id))
  }
  return rows
})
const sortedList = computed(() => {
  if (!sortKey.value) return filteredList.value
  const dir = sortDir.value === "asc" ? 1 : -1
  return [...filteredList.value].sort((a, b) => {
    const va = sortVal(a, sortKey.value), vb = sortVal(b, sortKey.value)
    if (va < vb) return -dir
    if (va > vb) return dir
    return 0
  })
})

/* ====== totals ====== */
const setRows = computed(() => filteredList.value.filter(r => r.id))
const totalBase = computed(() => setRows.value.reduce((s, r) => s + (r.base_salary || 0), 0))
const totalDeduction = computed(() => setRows.value.reduce((s, r) => s + (r.social_insurance || 0), 0))

/* ====== data ====== */
async function fetchData() {
  loading.value = true
  try {
    // 名单（在职员工）+ 规则合并：未设规则员工也展示，操作列显示「设置」
    const r = await getSalaryRules({ page: 1, page_size: 200 })
    const rules = r?.items || []
    const ruleMap = new Map(rules.map(x => [x.employee_id, x]))
    list.value = employees.value.map(e => {
      const rule = ruleMap.get(e.id)
      return {
        employee_id: e.id,
        employee_no: e.employee_no,
        employee_name: e.name,
        id: rule?.id,
        effective_date: rule?.effective_date ?? "",
        base_salary: rule?.base_salary ?? null,
        social_insurance: rule?.social_insurance ?? null,
        remark: rule?.remark ?? "",
      }
    })
  } finally { loading.value = false }
}
async function loadEmps() { employees.value = (await getAttendanceEmployees()) || [] }

function openEdit(r: RuleRow) {
  isEditing.value = true
  editId.value = r.id || ""
  form.value = { ...r, employee_name: r.employee_name || '' }
  showDialog.value = true
}
function openAdd(r: RuleRow) {
  isEditing.value = false
  editId.value = ""
  form.value = { ...initForm, employee_id: r.employee_id, employee_name: r.employee_name }
  showDialog.value = true
}
async function handleSave() {
  saving.value = true
  try {
    if (isEditing.value) {
      await updateSalaryRule(editId.value, form.value)
      ElMessage.success("已更新")
    } else {
      await createSalaryRule(form.value)
      ElMessage.success("已创建")
    }
    showDialog.value = false
    await fetchData()
  } catch (e: unknown) { ElMessage.error((e as { message?: string })?.message || "保存失败") }
  finally { saving.value = false }
}

async function handleDelete(r: RuleRow) {
  if (!r.id) return
  await ElMessageBox.confirm("确定删除此工资规则？", "提示", { type: "warning" })
  await deleteSalaryRule(r.id)
  ElMessage.success("已删除")
  await fetchData()
}

/* batch */
function openBatchEdit() {
  batchForm.value = { ...initBatchForm, effective_date: new Date().toISOString().slice(0, 10) }
  showBatchDialog.value = true
}
async function handleBatchSave() {
  if (!batchForm.value.employee_ids?.length) {
    ElMessage.warning("请选择员工")
    return
  }
  batchSaving.value = true
  let ok = 0, fail = 0
  for (const eid of batchForm.value.employee_ids) {
    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const data: any = {
        employee_id: eid,
        effective_date: batchForm.value.effective_date,
        base_salary: batchForm.value.base_salary ?? 0,
      }
      if (batchForm.value.social_insurance != null) data.social_insurance = batchForm.value.social_insurance
      await createSalaryRule(data)
      ok++
    } catch { fail++ }
  }
  showBatchDialog.value = false
  batchSaving.value = false
  ElMessage.success(`批量完成：成功 ${ok} 人${fail ? `，失败 ${fail} 人` : ''}`)
  await fetchData()
}

onMounted(async () => { await loadEmps(); await fetchData() })
</script>

<style scoped>
.sheet-wrapper { overflow-x: auto; overflow-y: auto; border: 1px solid #e4e7ed; border-radius: 4px; background: #fff; padding-bottom: 14px; }
.rule-sheet { width: 100%; border-collapse: collapse; font-size: 15px; white-space: nowrap; }
.rule-sheet th, .rule-sheet td { border: 1px solid #e4e7ed; padding: 7px 10px; }
.rule-sheet thead th { background: #f5f7fa; position: sticky; top: 0; z-index: 2; font-weight: 600; color: #303133; }
.rule-sheet th.sortable { cursor: pointer; user-select: none; }
.rule-sheet th.sortable:hover { color: #409eff; }
.rule-sheet th.sort-active { color: #409eff; }
.sort-arrow { margin-left: 3px; font-size: 10px; }
.col-sm { width: 40px; text-align: center; }
.col-emp { min-width: 70px; }
.col-dept { width: 75px; text-align: center; }
.col-date { width: 100px; text-align: center; }
.col-num { min-width: 85px; text-align: right; }
.col-op { width: 100px; text-align: center; }
.cell-center { text-align: center; }
.cell-name { font-weight: 600; color: #303133; }
.cell-date { text-align: center; font-family: "SF Mono", "Courier New", monospace; color: #606266; }
.cell-num { text-align: right; font-family: "SF Mono", "Courier New", monospace; color: #606266; }
.cell-num.deduction { color: #f56c6c; }
.cell-op { text-align: center; }
</style>
