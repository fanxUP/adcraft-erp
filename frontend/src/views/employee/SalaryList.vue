<template>
  <div class="page">
    <div class="page-header">
      <h2>💰 工资表</h2>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
        <el-input v-model="fMonth" placeholder="月份 YYYY-MM" style="width:150px" clearable @change="fetchData" />
        <el-select v-model="fEmp" placeholder="全部员工" clearable filterable style="width:200px" @change="fetchData">
          <el-option v-for="e in employees" :key="e.id" :label="e.name+' ('+e.employee_no+')'" :value="e.id" />
        </el-select>
        <el-select v-model="fStatus" placeholder="支付状态" clearable style="width:120px" @change="fetchData">
          <el-option label="待核算" value="pending" /><el-option label="已核算" value="calculated" /><el-option label="已发放" value="paid" />
        </el-select>
        <el-button @click="fetchData">刷新</el-button>
        <el-button type="danger" @click="openCreate">录入工资</el-button>
      </div>
    </div>

    <!-- 汇总 -->
    <el-row :gutter="16" style="margin-bottom:16px">
      <el-col :span="6"><el-card shadow="never" body-style="padding:16px"><div style="text-align:center"><div style="font-size:28px;font-weight:700;color:#409eff">{{list.length}}</div><div style="font-size:13px;color:#909399;margin-top:4px">记录数</div></div></el-card></el-col>
      <el-col :span="6"><el-card shadow="never" body-style="padding:16px"><div style="text-align:center"><div style="font-size:28px;font-weight:700;color:#67c23a">{{totalBase.toFixed(2)}}</div><div style="font-size:13px;color:#909399;margin-top:4px">基本工资合计</div></div></el-card></el-col>
      <el-col :span="6"><el-card shadow="never" body-style="padding:16px"><div style="text-align:center"><div style="font-size:28px;font-weight:700;color:#e6a23c">{{totalGross.toFixed(2)}}</div><div style="font-size:13px;color:#909399;margin-top:4px">应发合计</div></div></el-card></el-col>
      <el-col :span="6"><el-card shadow="never" body-style="padding:16px"><div style="text-align:center"><div style="font-size:28px;font-weight:700;color:#f56c6c">{{totalNet.toFixed(2)}}</div><div style="font-size:13px;color:#909399;margin-top:4px">实发合计</div></div></el-card></el-col>
    </el-row>

    <!-- 工资表 -->
    <div class="sheet-wrapper" :style="{ maxHeight: 'calc(100vh - 320px)' }">
      <table class="sal-sheet" v-if="list.length">
        <thead>
          <tr class="sal-header-top">
            <th rowspan="2" class="sal-col-sm">#</th>
            <th rowspan="2" class="sal-col-emp">工号</th>
            <th rowspan="2" class="sal-col-emp">姓名</th>
            <th rowspan="2" class="sal-col-month">月份</th>
            <th colspan="5" class="sal-col-group">应发工资</th>
            <th rowspan="2" class="sal-col-num">扣款</th>
            <th rowspan="2" class="sal-col-num">实发工资</th>
            <th rowspan="2" class="sal-col-status">支付状态</th>
            <th rowspan="2" class="sal-col-op">操作</th>
          </tr>
          <tr class="sal-header-bottom">
            <th class="sal-col-num">基本工资</th>
            <th class="sal-col-num">加班费</th>
            <th class="sal-col-num">奖金</th>
            <th class="sal-col-num">提成</th>
            <th class="sal-col-num">补贴</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, i) in list" :key="row.id" :class="getRowClass(row)">
            <td class="cell-center">{{ i + 1 }}</td>
            <td>{{ row.employee_no || '-' }}</td>
            <td class="cell-name">{{ row.employee_name || '-' }}</td>
            <td class="cell-month">{{ row.month }}</td>
            <td class="cell-num">{{ fmt(row.base_salary) }}</td>
            <td class="cell-num">{{ fmt(row.overtime_pay) }}</td>
            <td class="cell-num">{{ fmt(row.bonus) }}</td>
            <td class="cell-num">{{ fmt(row.commission) }}</td>
            <td class="cell-num">{{ fmt(row.subsidy) }}</td>
            <td class="cell-num deduction">{{ fmt(row.deduction) }}</td>
            <td class="cell-num net"><strong>{{ fmt(row.net_salary) }}</strong></td>
            <td class="cell-center">
              <el-tag :type="payColor(row.payment_status)" size="small">{{ payLabel(row.payment_status) }}</el-tag>
            </td>
            <td class="cell-op">
              <el-button text type="primary" size="small" @click="openEdit(row)">编辑</el-button>
              <el-button text type="danger" size="small" @click="handleDelete(row)">删除</el-button>
            </td>
          </tr>
        </tbody>
        <tfoot>
          <tr class="sal-footer">
            <td colspan="4" class="cell-footer-label">本页合计</td>
            <td class="cell-num">{{ fmt(pageTotal.base_salary) }}</td>
            <td class="cell-num">{{ fmt(pageTotal.overtime_pay) }}</td>
            <td class="cell-num">{{ fmt(pageTotal.bonus) }}</td>
            <td class="cell-num">{{ fmt(pageTotal.commission) }}</td>
            <td class="cell-num">{{ fmt(pageTotal.subsidy) }}</td>
            <td class="cell-num deduction">{{ fmt(pageTotal.deduction) }}</td>
            <td class="cell-num net"><strong>{{ fmt(pageTotal.net_salary) }}</strong></td>
            <td colspan="2"></td>
          </tr>
        </tfoot>
      </table>
      <el-empty v-else description="暂无数据" :image-size="80" />
    </div>

    <!-- Dialog -->
    <el-dialog v-model="showDialog" :title="isEditing?'编辑工资':'录入工资'" width="640px">
      <el-form :model="form" label-width="100px" label-position="top" style="display:grid;grid-template-columns:1fr 1fr;gap:0 16px">
        <el-form-item label="员工" v-if="!isEditing" required><el-select v-model="form.employee_id" filterable style="width:100%"><el-option v-for="e in employees" :key="e.id" :label="e.name+' ('+e.employee_no+')'" :value="e.id" /></el-select></el-form-item>
        <el-form-item label="月份" required><el-input v-model="form.month" placeholder="YYYY-MM" style="width:100%" /></el-form-item>
        <el-form-item label="基本工资"><el-input-number v-model="form.base_salary" :min="0" :precision="2" style="width:100%" /></el-form-item>
        <el-form-item label="加班费"><el-input-number v-model="form.overtime_pay" :min="0" :precision="2" style="width:100%" /></el-form-item>
        <el-form-item label="奖金"><el-input-number v-model="form.bonus" :min="0" :precision="2" style="width:100%" /></el-form-item>
        <el-form-item label="提成"><el-input-number v-model="form.commission" :min="0" :precision="2" style="width:100%" /></el-form-item>
        <el-form-item label="补贴"><el-input-number v-model="form.subsidy" :min="0" :precision="2" style="width:100%" /></el-form-item>
        <el-form-item label="扣款"><el-input-number v-model="form.deduction" :min="0" :precision="2" style="width:100%" /></el-form-item>
        <el-form-item label="实发工资" required><el-input-number v-model="form.net_salary" :min="0" :precision="2" style="width:100%" /></el-form-item>
        <el-form-item label="支付状态"><el-select v-model="form.payment_status" style="width:100%"><el-option label="待核算" value="pending" /><el-option label="已核算" value="calculated" /><el-option label="已发放" value="paid" /></el-select></el-form-item>
        <el-form-item label="备注" style="grid-column:1/3"><el-input v-model="form.remark" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showDialog=false">取消</el-button><el-button type="primary" @click="handleSave" :loading="saving">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue"
import { getSalaries, createSalary, updateSalary, deleteSalary, type SalaryRecordItem } from "@/api/salaries"
import { getAttendanceEmployees, type EmployeeOption } from "@/api/attendance"
import { ElMessage, ElMessageBox } from "element-plus"

/* ====== state ====== */
const list = ref<SalaryRecordItem[]>([])
const employees = ref<EmployeeOption[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(50)
const total = ref(0)
const fEmp = ref("")
const fMonth = ref("")
const fStatus = ref("")
const showDialog = ref(false)
const isEditing = ref(false)
const saving = ref(false)
const editId = ref("")
const initForm = { employee_id: "", month: "", base_salary: 0, overtime_pay: null, bonus: null, commission: null, subsidy: null, deduction: null, net_salary: 0, payment_status: "pending", remark: "" }
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const form = ref<any>({ ...initForm })

/* ====== helpers ====== */
const fmt = (v: unknown) => v != null ? Number(v).toFixed(2) : "-"
const payLabel = (s: string) => ({ pending: "待核算", calculated: "已核算", paid: "已发放" })[s] || s
const payColor = (s: string) => ({ pending: "info", calculated: "warning", paid: "success" })[s] || "info"
const getRowClass = (r: SalaryRecordItem) => r.payment_status === "paid" ? "row-paid" : r.payment_status === "calculated" ? "row-calc" : ""

/* ====== totals ====== */
const totalBase = computed(() => list.value.reduce((s, r) => s + (r.base_salary || 0), 0))
const totalGross = computed(() => list.value.reduce((s, r) => s + (r.base_salary || 0) + (r.overtime_pay || 0) + (r.bonus || 0) + (r.commission || 0) + (r.subsidy || 0), 0))
const totalNet = computed(() => list.value.reduce((s, r) => s + (r.net_salary || 0), 0))
const pageTotal = computed(() => {
  const t = { base_salary: 0, overtime_pay: 0, bonus: 0, commission: 0, subsidy: 0, deduction: 0, net_salary: 0 }
  for (const r of list.value) {
    t.base_salary += r.base_salary || 0
    t.overtime_pay += r.overtime_pay || 0
    t.bonus += r.bonus || 0
    t.commission += r.commission || 0
    t.subsidy += r.subsidy || 0
    t.deduction += r.deduction || 0
    t.net_salary += r.net_salary || 0
  }
  return t
})

/* ====== data ====== */
async function fetchData() {
  loading.value = true
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const p: any = { page: page.value, page_size: pageSize.value }
    if (fEmp.value) p.employee_id = fEmp.value
    if (fMonth.value) p.month = fMonth.value
    if (fStatus.value) p.payment_status = fStatus.value
    const r = await getSalaries(p)
    list.value = r?.items || []
    total.value = r?.total || 0
  } finally { loading.value = false }
}
async function loadEmps() { employees.value = (await getAttendanceEmployees()) || [] }
function openCreate() { isEditing.value = false; editId.value = ""; form.value = { ...initForm }; showDialog.value = true }
function openEdit(r: SalaryRecordItem) { isEditing.value = true; editId.value = r.id; form.value = { ...r }; showDialog.value = true }
async function handleSave() {
  saving.value = true
  try {
    if (isEditing.value) { await updateSalary(editId.value, form.value); ElMessage.success("已更新") }
    else { await createSalary(form.value); ElMessage.success("已创建") }
    showDialog.value = false
    await fetchData()
  } catch (e: unknown) { ElMessage.error((e as { message?: string })?.message || "保存失败") }
  finally { saving.value = false }
}
async function handleDelete(r: SalaryRecordItem) {
  await ElMessageBox.confirm("确定删除此工资记录？", "提示", { type: "warning" })
  await deleteSalary(r.id)
  ElMessage.success("已删除")
  await fetchData()
}

onMounted(() => { fetchData(); loadEmps() })
</script>

<style scoped>
.sheet-wrapper { overflow-x: auto; overflow-y: auto; border: 1px solid #e4e7ed; border-radius: 4px; background: #fff; padding-bottom: 14px; }
.sal-sheet { width: 100%; border-collapse: collapse; font-size: 13px; white-space: nowrap; }
.sal-sheet th, .sal-sheet td { border: 1px solid #e4e7ed; padding: 6px 8px; }
.sal-sheet thead th { background: #f5f7fa; position: sticky; top: 0; z-index: 2; font-weight: 600; color: #303133; }
.sal-col-sm { width: 40px; text-align: center; }
.sal-col-emp { min-width: 70px; }
.sal-col-month { width: 80px; text-align: center; }
.sal-col-group { text-align: center; background: #eef1f6 !important; }
.sal-col-num { min-width: 85px; text-align: right; }
.sal-col-status { width: 80px; text-align: center; }
.sal-col-op { width: 100px; text-align: center; }
.cell-center { text-align: center; }
.cell-name { font-weight: 600; color: #303133; }
.cell-month { text-align: center; font-family: "SF Mono", "Courier New", monospace; color: #606266; }
.cell-num { text-align: right; font-family: "SF Mono", "Courier New", monospace; color: #606266; }
.cell-num.deduction { color: #f56c6c; }
.cell-num.net { color: #67c23a; font-size: 14px; }
.cell-op { text-align: center; }
.row-paid { background: #f0f9eb; }
.row-calc { background: #fdf6ec; }
.sal-footer td { background: #eef1f6; font-weight: 700; color: #303133; }
.cell-footer-label { text-align: right; font-weight: 700; padding-right: 12px; }
</style>
