"""Apply HR module frontend changes"""
import pathlib

FRONTEND = pathlib.Path("/opt/adcraft/frontend")

# Create directories
(FRONTEND / "src/views/attendance").mkdir(parents=True, exist_ok=True)

# ============================================================
# 1. AttendanceRuleList.vue
# ============================================================
(FRONTEND / "src/views/attendance/AttendanceRuleList.vue").write_text('''<template>
  <div class="page">
    <div class="page-header">
      <h2>考勤规则</h2>
      <el-button type="danger" @click="showDialog = true; isEditing = false; ruleForm = { name: "", check_in_time: "09:00", check_out_time: "18:00", late_threshold: 0, early_leave_threshold: 0, overtime_rate: 1.5 }">新建规则</el-button>
    </div>

    <el-table :data="rules" v-loading="loading" stripe>
      <el-table-column prop="name" label="规则名称" width="160" />
      <el-table-column label="适用部门" width="120">
        <template #default="{ row }">{{ row.department || "全局" }}</template>
      </el-table-column>
      <el-table-column prop="check_in_time" label="上班时间" width="100" />
      <el-table-column prop="check_out_time" label="下班时间" width="100" />
      <el-table-column prop="late_threshold" label="迟到阈值(min)" width="120" />
      <el-table-column prop="overtime_rate" label="加班费率" width="100" />
      <el-table-column label="启用" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? "是" : "否" }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" size="small" @click="openEdit(row)">编辑</el-button>
          <el-button text type="danger" size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showDialog" :title="isEditing ? '编辑规则' : '新建规则'" width="500px">
      <el-form :model="ruleForm" label-width="120px">
        <el-form-item label="规则名称" required><el-input v-model="ruleForm.name" /></el-form-item>
        <el-form-item label="适用部门">
          <el-select v-model="ruleForm.department" placeholder="留空=全局" clearable style="width:100%">
            <el-option label="设计部" value="design" />
            <el-option label="生产部" value="production" />
            <el-option label="安装部" value="installation" />
            <el-option label="销售部" value="sales" />
            <el-option label="财务部" value="finance" />
            <el-option label="行政部" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="上班时间" required>
          <el-time-picker v-model="ruleForm.check_in_time" format="HH:mm" value-format="HH:mm" style="width:100%" />
        </el-form-item>
        <el-form-item label="下班时间" required>
          <el-time-picker v-model="ruleForm.check_out_time" format="HH:mm" value-format="HH:mm" style="width:100%" />
        </el-form-item>
        <el-form-item label="迟到阈值(分钟)">
          <el-input-number v-model="ruleForm.late_threshold" :min="0" style="width:100%" />
        </el-form-item>
        <el-form-item label="早退阈值(分钟)">
          <el-input-number v-model="ruleForm.early_leave_threshold" :min="0" style="width:100%" />
        </el-form-item>
        <el-form-item label="加班费率">
          <el-input-number v-model="ruleForm.overtime_rate" :min="1" :max="3" :step="0.1" style="width:100%" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="ruleForm.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue"
import { getAttendanceRules, createAttendanceRule, updateAttendanceRule, deleteAttendanceRule, type AttendanceRuleItem } from "@/api/attendance"
import { ElMessage, ElMessageBox } from "element-plus"

const rules = ref<AttendanceRuleItem[]>([])
const loading = ref(false)
const showDialog = ref(false)
const isEditing = ref(false)
const saving = ref(false)
const ruleForm = ref<any>({})

async function fetchData() {
  loading.value = true
  try {
    const res = await getAttendanceRules()
    rules.value = res.data || []
  } finally {
    loading.value = false
  }
}

function openEdit(row: AttendanceRuleItem) {
  isEditing.value = true
  ruleForm.value = { ...row }
  showDialog.value = true
}

async function handleSave() {
  saving.value = true
  try {
    if (isEditing.value) {
      await updateAttendanceRule(ruleForm.value.id, ruleForm.value)
      ElMessage.success("规则已更新")
    } else {
      await createAttendanceRule(ruleForm.value)
      ElMessage.success("规则已创建")
    }
    showDialog.value = false
    await fetchData()
  } finally {
    saving.value = false
  }
}

async function handleDelete(row: AttendanceRuleItem) {
  await ElMessageBox.confirm("确定删除该规则？", "提示", { type: "warning" })
  await deleteAttendanceRule(row.id)
  ElMessage.success("已删除")
  await fetchData()
}

onMounted(fetchData)
</script>
'''.strip())

print("  AttendanceRuleList.vue created")

# ============================================================
# 2. AttendanceRecordList.vue
# ============================================================
(FRONTEND / "src/views/attendance/AttendanceRecordList.vue").write_text('''<template>
  <div class="page">
    <div class="page-header">
      <h2>打卡记录</h2>
      <div style="display: flex; gap: 8px; align-items: center">
        <el-select v-model="filterEmployee" placeholder="员工" clearable filterable style="width: 200px" @change="fetchData">
          <el-option v-for="e in employees" :key="e.id" :label="e.name + ' (' + e.employee_no + ')'" :value="e.id" />
        </el-select>
        <el-date-picker v-model="filterDate" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" @change="fetchData" />
        <el-button type="danger" @click="openCreate">录入打卡</el-button>
      </div>
    </div>

    <el-table :data="list" v-loading="loading" stripe>
      <el-table-column prop="date" label="日期" width="120" />
      <el-table-column label="员工" width="140">
        <template #default="{ row }">{{ empName(row.employee_id) }}</template>
      </el-table-column>
      <el-table-column prop="check_in_time" label="签到时间" width="170">
        <template #default="{ row }">{{ formatDT(row.check_in_time) }}</template>
      </el-table-column>
      <el-table-column label="签到" width="80">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.check_in_status)" size="small">{{ statusLabel(row.check_in_status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="check_out_time" label="签退时间" width="170">
        <template #default="{ row }">{{ formatDT(row.check_out_time) }}</template>
      </el-table-column>
      <el-table-column label="签退" width="80">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.check_out_status)" size="small">{{ statusLabel(row.check_out_status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="remark" label="备注" min-width="140" />
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" size="small" @click="openEdit(row)">编辑</el-button>
          <el-button text type="danger" size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :page-sizes="[10, 20, 50]" :total="total" layout="total, sizes, prev, pager, next" style="margin-top: 16px" @change="fetchData" />

    <el-dialog v-model="showDialog" :title="isEditing ? '编辑打卡' : '录入打卡'" width="500px">
      <el-form :model="form" label-width="110px">
        <el-form-item label="员工" v-if="!isEditing" required>
          <el-select v-model="form.employee_id" placeholder="选择员工" filterable style="width:100%">
            <el-option v-for="e in employees" :key="e.id" :label="e.name + ' (' + e.employee_no + ')'" :value="e.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期" required>
          <el-date-picker v-model="form.date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
        </el-form-item>
        <el-form-item label="签到时间">
          <el-date-picker v-model="form.check_in_time" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width:100%" />
        </el-form-item>
        <el-form-item label="签到状态">
          <el-select v-model="form.check_in_status" style="width:100%">
            <el-option label="正常" value="normal" />
            <el-option label="迟到" value="late" />
            <el-option label="缺卡" value="missed" />
          </el-select>
        </el-form-item>
        <el-form-item label="签退时间">
          <el-date-picker v-model="form.check_out_time" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width:100%" />
        </el-form-item>
        <el-form-item label="签退状态">
          <el-select v-model="form.check_out_status" style="width:100%">
            <el-option label="正常" value="normal" />
            <el-option label="早退" value="early" />
            <el-option label="缺卡" value="missed" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue"
import { getAttendanceRecords, createAttendanceRecord, updateAttendanceRecord, deleteAttendanceRecord, getAttendanceEmployees, type AttendanceRecordItem, type EmployeeOption } from "@/api/attendance"
import { ElMessage, ElMessageBox } from "element-plus"

const list = ref<AttendanceRecordItem[]>([])
const employees = ref<EmployeeOption[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const filterEmployee = ref("")
const filterDate = ref<string[]>([])
const showDialog = ref(false)
const isEditing = ref(false)
const saving = ref(false)
const form = ref<any>({ employee_id: "", date: "", check_in_time: null, check_out_time: null, check_in_status: "normal", check_out_status: "normal", remark: "" })
const editingId = ref("")

function empName(id: string) {
  return employees.value.find(e => e.id === id)?.name || id
}

function statusLabel(s: string) {
  const map: Record<string, string> = { normal: "正常", late: "迟到", early: "早退", missed: "缺卡" }
  return map[s] || s
}

function statusTagType(s: string) {
  const map: Record<string, string> = { normal: "success", late: "warning", early: "warning", missed: "danger" }
  return map[s] || "info"
}

function formatDT(dt: string | null) {
  if (!dt) return "-"
  return dt.replace("T", " ").substring(0, 19)
}

async function fetchData() {
  loading.value = true
  try {
    const params: any = { page: page.value, page_size: pageSize.value }
    if (filterEmployee.value) params.employee_id = filterEmployee.value
    if (filterDate.value?.length === 2) { params.date_from = filterDate.value[0]; params.date_to = filterDate.value[1] }
    const res = await getAttendanceRecords(params)
    list.value = res.data?.items || []
    total.value = res.data?.total || 0
  } finally {
    loading.value = false
  }
}

async function loadEmployees() {
  const res = await getAttendanceEmployees()
  employees.value = res.data || []
}

function openCreate() {
  isEditing.value = false
  editingId.value = ""
  form.value = { employee_id: "", date: "", check_in_time: null, check_out_time: null, check_in_status: "normal", check_out_status: "normal", remark: "" }
  showDialog.value = true
}

function openEdit(row: AttendanceRecordItem) {
  isEditing.value = true
  editingId.value = row.id
  form.value = { ...row }
  showDialog.value = true
}

async function handleSave() {
  saving.value = true
  try {
    if (isEditing.value) {
      await updateAttendanceRecord(editingId.value, form.value)
      ElMessage.success("已更新")
    } else {
      await createAttendanceRecord(form.value)
      ElMessage.success("已创建")
    }
    showDialog.value = false
    await fetchData()
  } finally {
    saving.value = false
  }
}

async function handleDelete(row: AttendanceRecordItem) {
  await ElMessageBox.confirm("确定删除该记录？", "提示", { type: "warning" })
  await deleteAttendanceRecord(row.id)
  ElMessage.success("已删除")
  await fetchData()
}

onMounted(() => { fetchData(); loadEmployees() })
</script>
'''.strip())

print("  AttendanceRecordList.vue created")

# ============================================================
# 3. Patch navigation.ts
# ============================================================
print("=== 修改导航配置 ===")
nav_path = FRONTEND / "src/config/navigation.ts"
nav_content = nav_path.read_text()

if "attendance/records" not in nav_content:
    nav_content = nav_content.replace(
        "children: [\n      { label: '员工管理', path: '/employees' },\n    ],",
        """children: [
      { label: '员工管理', path: '/employees' },
      {
        label: '考勤管理',
        icon: 'Clock',
        children: [
          { label: '打卡记录', path: '/attendance/records' },
          { label: '考勤规则', path: '/attendance/rules' },
        ],
      },
    ],""".replace("\n", "\n")
    )
    nav_path.write_text(nav_content)
    print("  navigation.ts - added attendance menu items")
else:
    print("  navigation.ts - already up to date")

# ============================================================
# 4. Add Clock icon to SidebarNavItem.vue
# ============================================================
print("=== 修改图标注册 ===")
sidebar_path = FRONTEND / "src/components/navigation/SidebarNavItem.vue"
sidebar_content = sidebar_path.read_text()

if "Clock" not in sidebar_content:
    sidebar_content = sidebar_content.replace(
        "import {\n  Avatar,", 
        "import {\n  Avatar,\n  Clock,"
    )
    sidebar_content = sidebar_content.replace(
        "const icons: Record<string, Component> = {\n    Avatar,", 
        "const icons: Record<string, Component> = {\n    Avatar,\n    Clock,"
    )
    sidebar_path.write_text(sidebar_content)
    print("  SidebarNavItem.vue - registered Clock icon")
else:
    print("  SidebarNavItem.vue - already up to date")

# ============================================================
# 5. Patch router/index.ts
# ============================================================
print("=== 修改路由 ===")
router_path = FRONTEND / "src/router/index.ts"
router_content = router_path.read_text()

if "attendance/records" not in router_content:
    # Add before employees route
    router_content = router_content.replace(
        "{ path: \"employees\", name: \"EmployeeList\", meta: { roles: [\"admin\"] }, component: () => import(\"@/views/employee/EmployeeList.vue\") },",
        """{ path: "employees", name: "EmployeeList", meta: { roles: ["admin"] }, component: () => import("@/views/employee/EmployeeList.vue") },
      { path: "attendance/records", name: "AttendanceRecordList", meta: { roles: ["admin"] }, component: () => import("@/views/attendance/AttendanceRecordList.vue") },
      { path: "attendance/rules", name: "AttendanceRuleList", meta: { roles: ["admin"] }, component: () => import("@/views/attendance/AttendanceRuleList.vue") },"""
    )
    router_path.write_text(router_content)
    print("  router/index.ts - added attendance routes")
else:
    print("  router/index.ts - already up to date")

print()
print("=== 前端文件创建完成 ===")
print("请运行: cd /opt/adcraft/frontend && npm run build")
