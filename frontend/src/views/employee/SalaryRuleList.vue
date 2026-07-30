<template>
  <div class="page">
    <div class="page-header">
      <h2>⚙️ 工资规则</h2>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
        <el-select v-model="fEmp" placeholder="全部员工" clearable filterable style="width:200px" @change="fetchData">
          <el-option v-for="e in employees" :key="e.id" :label="e.name+' ('+e.employee_no+')'" :value="e.id" />
        </el-select>
        <el-select v-model="fDept" placeholder="部门筛选" clearable style="width:130px" @change="fetchData">
          <el-option v-for="d in DEPTS" :key="d.value" :label="d.label" :value="d.value" />
        </el-select>
        <el-button @click="fetchData">刷新</el-button>
        <el-button type="danger" @click="openBatchEdit">批量设置</el-button>
      </div>
    </div>

    <!-- 汇总 -->
    <el-row :gutter="16" style="margin-bottom:16px">
      <el-col :span="6"><el-card shadow="never" body-style="padding:16px"><div style="text-align:center"><div style="font-size:28px;font-weight:700;color:#409eff">{{list.length}}</div><div style="font-size:13px;color:#909399;margin-top:4px">已设置规则人数</div></div></el-card></el-col>
      <el-col :span="6"><el-card shadow="never" body-style="padding:16px"><div style="text-align:center"><div style="font-size:28px;font-weight:700;color:#67c23a">{{totalBase.toFixed(2)}}</div><div style="font-size:13px;color:#909399;margin-top:4px">基本工资合计/月</div></div></el-card></el-col>
      <el-col :span="6"><el-card shadow="never" body-style="padding:16px"><div style="text-align:center"><div style="font-size:28px;font-weight:700;color:#e6a23c">{{totalSubsidy.toFixed(2)}}</div><div style="font-size:13px;color:#909399;margin-top:4px">补贴合计/月</div></div></el-card></el-col>
      <el-col :span="6"><el-card shadow="never" body-style="padding:16px"><div style="text-align:center"><div style="font-size:28px;font-weight:700;color:#f56c6c">{{totalDeduction.toFixed(2)}}</div><div style="font-size:13px;color:#909399;margin-top:4px">社保公积金扣款合计/月</div></div></el-card></el-col>
    </el-row>

    <!-- 工资规则表 -->
    <div class="sheet-wrapper" :style="{ maxHeight: 'calc(100vh - 320px)' }">
      <table class="rule-sheet" v-if="list.length">
        <thead>
          <tr>
            <th rowspan="2" class="col-sm">#</th>
            <th rowspan="2" class="col-emp">工号</th>
            <th rowspan="2" class="col-emp">姓名</th>
            <th rowspan="2" class="col-dept">部门</th>
            <th rowspan="2" class="col-date">生效日期</th>
            <th colspan="5" class="col-group">应发标准</th>
            <th colspan="3" class="col-group">扣款标准</th>
            <th rowspan="2" class="col-op">操作</th>
          </tr>
          <tr>
            <th class="col-num">基本工资</th>
            <th class="col-num">加班费率</th>
            <th class="col-num">奖金标准</th>
            <th class="col-num">提成比例</th>
            <th class="col-num">补贴标准</th>
            <th class="col-num">全勤奖</th>
            <th class="col-num">社保</th>
            <th class="col-num">公积金</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, i) in list" :key="row.id">
            <td class="cell-center">{{ i + 1 }}</td>
            <td>{{ row.employee_no || '-' }}</td>
            <td class="cell-name">{{ row.employee_name || '-' }}</td>
            <td>{{ deptLabel(row.employee_id) }}</td>
            <td class="cell-date">{{ row.effective_date }}</td>
            <td class="cell-num"><strong>{{ fmt(row.base_salary) }}</strong></td>
            <td class="cell-num">{{ row.overtime_rate != null ? row.overtime_rate + 'x' : '-' }}</td>
            <td class="cell-num">{{ fmt(row.bonus_standard) }}</td>
            <td class="cell-num">{{ row.commission_rate != null ? row.commission_rate + '%' : '-' }}</td>
            <td class="cell-num">{{ fmt(row.subsidy_standard) }}</td>
            <td class="cell-num">{{ fmt(row.attendance_bonus) }}</td>
            <td class="cell-num deduction">{{ fmt(row.social_insurance) }}</td>
            <td class="cell-num deduction">{{ fmt(row.housing_fund) }}</td>
            <td class="cell-op">
              <el-button text type="primary" size="small" @click="openEdit(row)">编辑</el-button>
              <el-button text type="danger" size="small" @click="handleDelete(row)">删除</el-button>
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
        <el-form-item label="基本工资 (元)"><el-input-number v-model="form.base_salary" :min="0" :precision="2" style="width:100%" /></el-form-item>
        <el-form-item label="加班费率 (倍)"><el-input-number v-model="form.overtime_rate" :min="1" :max="3" :step="0.1" :precision="1" style="width:100%" placeholder="默认1.5" /></el-form-item>
        <el-form-item label="奖金标准 (元)"><el-input-number v-model="form.bonus_standard" :min="0" :precision="2" style="width:100%" /></el-form-item>
        <el-form-item label="提成比例 (%)"><el-input-number v-model="form.commission_rate" :min="0" :max="100" :precision="1" style="width:100%" /></el-form-item>
        <el-form-item label="补贴标准 (元/月)"><el-input-number v-model="form.subsidy_standard" :min="0" :precision="2" style="width:100%" /></el-form-item>
        <el-form-item label="全勤奖 (元)"><el-input-number v-model="form.attendance_bonus" :min="0" :precision="2" style="width:100%" /></el-form-item>
        <el-form-item label="社保扣款 (元)"><el-input-number v-model="form.social_insurance" :min="0" :precision="2" style="width:100%" /></el-form-item>
        <el-form-item label="公积金扣款 (元)"><el-input-number v-model="form.housing_fund" :min="0" :precision="2" style="width:100%" /></el-form-item>
        <el-form-item label="其他扣款 (元)"><el-input-number v-model="form.deduction_standard" :min="0" :precision="2" style="width:100%" /></el-form-item>
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
          <el-form-item label="基本工资"><el-input-number v-model="batchForm.base_salary" :min="0" :precision="2" style="width:100%" /></el-form-item>
          <el-form-item label="补贴标准"><el-input-number v-model="batchForm.subsidy_standard" :min="0" :precision="2" style="width:100%" /></el-form-item>
          <el-form-item label="加班费率"><el-input-number v-model="batchForm.overtime_rate" :min="1" :max="3" :step="0.1" :precision="1" style="width:100%" /></el-form-item>
          <el-form-item label="提成比例"><el-input-number v-model="batchForm.commission_rate" :min="0" :max="100" :precision="1" style="width:100%" /></el-form-item>
          <el-form-item label="社保扣款"><el-input-number v-model="batchForm.social_insurance" :min="0" :precision="2" style="width:100%" /></el-form-item>
          <el-form-item label="公积金扣款"><el-input-number v-model="batchForm.housing_fund" :min="0" :precision="2" style="width:100%" /></el-form-item>
        </div>
      </el-form>
      <template #footer><el-button @click="showBatchDialog=false">取消</el-button><el-button type="primary" @click="handleBatchSave" :loading="batchSaving">批量保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue"
import { getSalaryRules, createSalaryRule, updateSalaryRule, deleteSalaryRule, type SalaryRuleItem } from "@/api/salaryRules"
import { getAttendanceEmployees, type EmployeeOption } from "@/api/attendance"
import { ElMessage, ElMessageBox } from "element-plus"

const DEPTS = [{ value: "design", label: "设计部" }, { value: "production", label: "生产部" }, { value: "installation", label: "安装部" }, { value: "sales", label: "销售部" }, { value: "finance", label: "财务部" }, { value: "admin", label: "行政部" }]

/* ====== state ====== */
const list = ref<SalaryRuleItem[]>([])
const employees = ref<EmployeeOption[]>([])
const loading = ref(false)
const fEmp = ref("")
const fDept = ref("")
const showDialog = ref(false)
const isEditing = ref(false)
const saving = ref(false)
const editId = ref("")

const initForm = {
  employee_id: "", effective_date: "", base_salary: 0, overtime_rate: null,
  bonus_standard: null, commission_rate: null, subsidy_standard: null,
  attendance_bonus: null, social_insurance: null, housing_fund: null,
  deduction_standard: null, remark: "", employee_name: "",
}
const form = ref<any>({ ...initForm })

/* batch */
const showBatchDialog = ref(false)
const batchSaving = ref(false)
const initBatchForm = {
  employee_ids: [], effective_date: "", base_salary: null, overtime_rate: null,
  commission_rate: null, subsidy_standard: null, social_insurance: null, housing_fund: null,
}
const batchForm = ref<any>({ ...initBatchForm })

/* ====== helpers ====== */
const fmt = (v: any) => v != null ? Number(v).toFixed(2) : "-"
const deptLabel = (eid: string) => {
  const emp = employees.value.find(e => e.id === eid)
  if (!emp || !emp.department) return "-"
  const d = DEPTS.find(d => d.value === emp.department)
  return d ? d.label : emp.department
}

/* ====== totals ====== */
const totalBase = computed(() => list.value.reduce((s, r) => s + (r.base_salary || 0), 0))
const totalSubsidy = computed(() => list.value.reduce((s, r) => s + (r.subsidy_standard || 0), 0))
const totalDeduction = computed(() => list.value.reduce((s, r) => s + (r.social_insurance || 0) + (r.housing_fund || 0), 0))

/* ====== data ====== */
async function fetchData() {
  loading.value = true
  try {
    const p: any = {}
    if (fEmp.value) p.employee_id = fEmp.value
    const r = await getSalaryRules({ ...p, page: 1, page_size: 200 })
    list.value = r?.items || []

    // If department filter is active, filter client-side
    if (fDept.value) {
      const deptEmps = employees.value.filter(e => e.department === fDept.value).map(e => e.id)
      list.value = list.value.filter(item => deptEmps.includes(item.employee_id))
    }
  } finally { loading.value = false }
}
async function loadEmps() { employees.value = (await getAttendanceEmployees()) || [] }

function openEdit(r: SalaryRuleItem) {
  isEditing.value = true
  editId.value = r.id
  form.value = { ...r, employee_name: r.employee_name || '' }
  showDialog.value = true
}
function openCreate(empId?: string) {
  isEditing.value = false
  editId.value = ""
  const emp = empId ? employees.value.find(e => e.id === empId) : null
  form.value = {
    ...initForm,
    employee_id: empId || "",
    employee_name: emp ? `${emp.name} (${emp.employee_no})` : "",
    effective_date: new Date().toISOString().slice(0, 10),
  }
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
  } catch (e: any) { ElMessage.error(e?.message || "保存失败") }
  finally { saving.value = false }
}

async function handleDelete(r: SalaryRuleItem) {
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
      const data: any = {
        employee_id: eid,
        effective_date: batchForm.value.effective_date,
        base_salary: batchForm.value.base_salary ?? 0,
      }
      if (batchForm.value.overtime_rate != null) data.overtime_rate = batchForm.value.overtime_rate
      if (batchForm.value.commission_rate != null) data.commission_rate = batchForm.value.commission_rate
      if (batchForm.value.subsidy_standard != null) data.subsidy_standard = batchForm.value.subsidy_standard
      if (batchForm.value.social_insurance != null) data.social_insurance = batchForm.value.social_insurance
      if (batchForm.value.housing_fund != null) data.housing_fund = batchForm.value.housing_fund
      await createSalaryRule(data)
      ok++
    } catch { fail++ }
  }
  showBatchDialog.value = false
  batchSaving.value = false
  ElMessage.success(`批量完成：成功 ${ok} 人${fail ? `，失败 ${fail} 人` : ''}`)
  await fetchData()
}

onMounted(() => { loadEmps(); fetchData() })
</script>

<style scoped>
.sheet-wrapper { overflow-x: auto; overflow-y: auto; border: 1px solid #e4e7ed; border-radius: 4px; background: #fff; padding-bottom: 14px; }
.rule-sheet { width: 100%; border-collapse: collapse; font-size: 13px; white-space: nowrap; }
.rule-sheet th, .rule-sheet td { border: 1px solid #e4e7ed; padding: 6px 8px; }
.rule-sheet thead th { background: #f5f7fa; position: sticky; top: 0; z-index: 2; font-weight: 600; color: #303133; }
.col-sm { width: 40px; text-align: center; }
.col-emp { min-width: 70px; }
.col-dept { width: 75px; text-align: center; }
.col-date { width: 100px; text-align: center; }
.col-group { text-align: center; background: #eef1f6 !important; }
.col-num { min-width: 85px; text-align: right; }
.col-op { width: 100px; text-align: center; }
.cell-center { text-align: center; }
.cell-name { font-weight: 600; color: #303133; }
.cell-date { text-align: center; font-family: "SF Mono", "Courier New", monospace; color: #606266; }
.cell-num { text-align: right; font-family: "SF Mono", "Courier New", monospace; color: #606266; }
.cell-num.deduction { color: #f56c6c; }
.cell-op { text-align: center; }
</style>
