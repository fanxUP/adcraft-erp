<template>
  <div class="page">
    <div class="page-header">
      <h2><el-icon><Money /></el-icon> 工资表</h2>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
        <el-date-picker v-model="curMonth" type="month" value-format="YYYY-MM" placeholder="选择月份" style="width:160px" @change="fetchGrid" />
        <el-button @click="fetchGrid">刷新</el-button>
        <el-button type="primary" :loading="computing" @click="computeAll"><el-icon><Cpu /></el-icon> 计算</el-button>
        <el-button type="warning" @click="openItems"><el-icon><Setting /></el-icon> 指标设置</el-button>
        <el-button type="success" plain @click="openParams"><el-icon><Tools /></el-icon> 参数</el-button>
      </div>
    </div>

    <!-- 汇总 -->
    <el-row :gutter="16" style="margin-bottom:16px">
      <el-col :span="8"><el-card shadow="never" body-style="padding:16px"><div style="text-align:center"><div style="font-size:28px;font-weight:700;color:var(--el-color-primary)">{{ rows.length }}</div><div style="font-size:13px;color:var(--el-text-color-secondary);margin-top:4px">员工数</div></div></el-card></el-col>
      <el-col :span="8"><el-card shadow="never" body-style="padding:16px"><div style="text-align:center"><div style="font-size:28px;font-weight:700;color:var(--el-color-warning)">{{ fmtVal(totals.gross) }}</div><div style="font-size:13px;color:var(--el-text-color-secondary);margin-top:4px">应发合计</div></div></el-card></el-col>
      <el-col :span="8"><el-card shadow="never" body-style="padding:16px"><div style="text-align:center"><div style="font-size:28px;font-weight:700;color:var(--el-color-danger)">{{ fmtVal(totals.net) }}</div><div style="font-size:13px;color:var(--el-text-color-secondary);margin-top:4px">实发合计</div></div></el-card></el-col>
    </el-row>

    <!-- 工资网格 -->
    <div class="sheet-wrapper" v-loading="loading">
      <table class="sal-sheet" v-if="rows.length">
        <thead>
          <tr v-for="(hrow, ri) in headerRows" :key="ri" :class="'sal-hdr-' + (ri + 1)">
            <th v-for="(h, hi) in hrow" :key="ri + '-' + hi"
                :colspan="h.colspan" :rowspan="h.rowspan"
                :class="h.key === 'no' || h.key === 'dept' || h.key === 'name' ? 'col-fixed' : 'col-item'"
                :style="hdrStyle(h, ri)"
                :title="h.formula ? (h.is_manual ? '手工填写（计算不覆盖）' : h.formula) : ''">
              {{ h.label }}<span v-if="h.is_manual" class="manual-badge" title="手工填写">手</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.employee_id">
            <template v-for="c in cols" :key="c.key">
              <td v-if="c.type === 'fixed'" :class="c.key === 'name' ? 'cell-name' : 'cell-center'">
                {{ c.key === 'no' ? (row.employee_no || '') : c.key === 'dept' ? deptLabel(row.department) : row.employee_name }}
              </td>
              <td v-else-if="c.type === 'item'" class="cell-num" @click="startEdit(row, c.key)">
                <el-input-number v-if="isEditing(row, c.key)" v-model="editVal" :controls="false" :precision="2"
                  size="small" autofocus style="width:112px" @change="commitEdit(row, c.key)" @blur="clearEdit" />
                <span v-else :class="{ 'cell-strong': isStrong(c.key) }">{{ fmtVal(row.values[c.key]) }}</span>
              </td>
              <td v-else-if="c.type === 'remark'" class="cell-center">
                <el-input v-model="row.remark" size="small" style="width:120px" placeholder="备注" @change="commitRemark(row)" />
              </td>
              <td v-else-if="c.type === 'payment'" class="cell-center">
                <el-select :model-value="row.payment_status || 'pending'" size="small" style="width:96px" @change="savePayment(row, $event)">
                  <el-option label="待核算" value="pending" /><el-option label="已核算" value="calculated" /><el-option label="已发放" value="paid" />
                </el-select>
              </td>
            </template>
          </tr>
        </tbody>
        <tfoot>
          <tr class="sal-footer">
            <template v-for="c in cols" :key="c.key">
              <td v-if="c.type === 'fixed' && c.key === 'no'" class="cell-footer-label">合计</td>
              <td v-else-if="c.type === 'item'" class="cell-num">{{ fmtVal(totals[c.key]) }}</td>
              <td v-else class="cell-num"></td>
            </template>
          </tr>
        </tfoot>
      </table>
      <el-empty v-else description="暂无员工" :image-size="80" />
    </div>

    <!-- 指标设置 Dialog -->
    <el-dialog v-model="showItems" title="工资指标设置（每列一个公式）" width="820px" top="4vh" :close-on-click-modal="false">
      <div class="items-help">
        <div style="font-weight:700;margin-bottom:6px">可用变量</div>
        <div class="help-grid">
          <span v-for="v in varHints" :key="v.name" class="help-item"><code>{{ v.name }}</code> = {{ v.label }}</span>
        </div>
        <template v-if="paramHints.length">
          <div style="font-weight:700;margin:10px 0 6px">本月参数（在「参数」中填值，未填按 0）</div>
          <div class="help-grid">
            <span v-for="p in paramHints" :key="p.name" class="help-item"><code>{{ p.name }}</code> = {{ p.label }}</span>
          </div>
        </template>
        <div style="font-weight:700;margin:10px 0 6px">函数与示例</div>
        <div class="help-examples">
          <div v-for="(ex, i) in examples" :key="i" class="help-ex"><code>{{ ex.split('→')[0] }}</code> → {{ ex.split('→')[1] }}</div>
        </div>
        <div style="color:var(--el-text-color-secondary);font-size:12px;margin-top:6px">
          语法为 Python 风格；支持 + - * / % 、比较、and/or/not、<code>A if 条件 else B</code>、max/min/round/abs。
          「组1/组2」决定列在表头第几层分组里（组1 = 应发金额/应扣金额/代缴部分，组2 = 基本部分/绩效部分/未出勤；留空为独立列）。
          勾选「手」的指标为手工填写列：无需公式，计算不会覆盖它的值。改完点「保存」，再回到页面点「 计算」重新生成数值。
        </div>
      </div>

      <div class="tpl-bar">
        <span style="font-size:13px;font-weight:700">模板</span>
        <el-select v-model="curTemplateId" size="small" clearable filterable placeholder="选择模板" style="width:220px">
          <el-option v-for="t in templates" :key="t.id" :label="t.name + '（' + t.item_count + ' 列）'" :value="t.id" />
        </el-select>
        <el-button size="small" type="primary" plain :disabled="!curTemplateId" @click="applyTemplate">应用</el-button>
        <el-button size="small" :disabled="!curTemplateId" @click="renameTemplate">重命名</el-button>
        <el-button size="small" type="danger" plain :disabled="!curTemplateId" @click="deleteTemplate">删除</el-button>
        <el-button size="small" type="warning" plain @click="saveAsTemplate">💾 存为模板</el-button>
      </div>

      <div class="items-list">
        <div v-for="(it, idx) in itemsDraft" :key="idx" class="item-row">
          <el-input v-model="it.label" placeholder="指标名称" style="width:104px" />
          <code class="item-key">{{ it.key }}</code>
          <el-select v-model="it.group1" clearable allow-create size="small" style="width:96px" placeholder="组1" title="一级分组：应发金额/应扣金额/代缴部分，留空为独立列">
            <el-option v-for="g in group1Options" :key="g" :label="g" :value="g" />
          </el-select>
          <el-select v-model="it.group2" clearable allow-create size="small" style="width:92px" placeholder="组2" title="二级分组：基本部分/绩效部分/未出勤">
            <el-option v-for="g in group2Options" :key="g" :label="g" :value="g" />
          </el-select>
          <el-input v-model="it.formula" :disabled="it.is_manual" :placeholder="it.is_manual ? '手工填写，无需公式' : '公式'" style="flex:1" />
          <el-input-number v-model="it.sort_order" :controls="false" size="small" style="width:58px" title="排序" />
          <span style="font-size:12px;color:var(--el-text-color-secondary)">手</span>
          <el-switch v-model="it.is_manual" size="small" title="手工填写（计算不覆盖）" />
          <el-switch v-model="it.is_active" size="small" title="启用" />
          <el-button text type="danger" size="small" :disabled="it.is_builtin" :title="it.is_builtin ? '内置指标不可删除' : '删除'" @click="removeItem(it)">删</el-button>
        </div>
      </div>

      <el-divider content-position="left">新增指标</el-divider>
      <div class="item-row new-item">
        <el-input v-model="newItem.label" placeholder="名称，如：高温补贴" style="width:104px" />
        <el-input v-model="newItem.key" placeholder="key，如：hot_subsidy" style="width:128px" />
        <el-select v-model="newItem.group1" clearable allow-create size="small" style="width:96px" placeholder="组1">
          <el-option v-for="g in group1Options" :key="g" :label="g" :value="g" />
        </el-select>
        <el-select v-model="newItem.group2" clearable allow-create size="small" style="width:92px" placeholder="组2">
          <el-option v-for="g in group2Options" :key="g" :label="g" :value="g" />
        </el-select>
        <el-input v-model="newItem.formula" :disabled="newItem.is_manual" :placeholder="newItem.is_manual ? '手工填写，无需公式' : '公式，如：200'" style="flex:1" />
        <span style="font-size:12px;color:var(--el-text-color-secondary)">手</span>
        <el-switch v-model="newItem.is_manual" size="small" title="手工填写" />
        <el-button type="primary" plain @click="addNewItem">＋ 添加</el-button>
      </div>

      <template #footer>
        <el-button @click="showItems = false">取消</el-button>
        <el-button type="primary" :loading="itemsSaving" @click="saveItems">保存</el-button>
      </template>
    </el-dialog>

    <!-- 工资参数 Dialog：每月填一个值，公式可引用 -->
    <el-dialog v-model="showParams" title="工资参数设置（每月填一个值，公式可引用）" width="640px" top="6vh" :close-on-click-modal="false">
      <div style="color:var(--el-text-color-secondary);font-size:12px;margin-bottom:10px">
        参数是每月填一个数的变量，指标公式里可以直接引用它的 key（如提成系数 <code>commission_rate</code>）。当月所有员工的公式都使用这个月的参数值；未填的参数按 0 处理。
      </div>
      <div class="items-list">
        <div v-for="(p, idx) in paramsDraft" :key="idx" class="item-row">
          <el-input v-model="p.label" placeholder="参数名称" style="width:120px" />
          <code class="item-key">{{ p.key }}</code>
          <el-input-number v-model="p.value" :controls="false" :precision="4" :placeholder="'本月值'" style="flex:1" />
          <el-input-number v-model="p.sort_order" :controls="false" size="small" style="width:64px" title="排序" />
          <el-button text type="danger" size="small" @click="removeParam(p)">删</el-button>
        </div>
      </div>

      <el-divider content-position="left">新增参数</el-divider>
      <div class="item-row new-item">
        <el-input v-model="newParam.label" placeholder="名称，如：提成系数" style="width:120px" />
        <el-input v-model="newParam.key" placeholder="key，如：commission_rate" style="width:170px" />
        <el-button type="primary" plain @click="addNewParam">＋ 添加</el-button>
      </div>

      <template #footer>
        <el-button @click="showParams = false">取消</el-button>
        <el-button type="primary" :loading="paramsSaving" @click="saveParams">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { Money, Cpu, Setting, Tools } from '@element-plus/icons-vue'
import { ref, computed, onMounted } from "vue"
import {
  getSalaryItems, getSalaryGrid, computeSalaryGrid, saveSalaryGrid,
  updateSalaryItem, createSalaryItem, deleteSalaryItem,
  getSalaryTemplates, createSalaryTemplate, updateSalaryTemplate, deleteSalaryTemplate, applySalaryTemplate,
  getSalaryParams, createSalaryParam, updateSalaryParam, deleteSalaryParam, saveSalaryParamValues,
  type SalaryItem, type SalaryItemTemplate, type SalaryItemSnapshot, type SalaryGridRow, type SalaryParam,
} from "@/api/salaries"
import { ElMessage, ElMessageBox } from "element-plus"
import { buildCols, buildHeaderRows, gridTotals, hdrStyle, fmtVal, deptLabel, isStrong, type Col, type HCell } from "@/composables/useSalaryGrid"

/* ====== state ====== */
const curMonth = ref("")
const items = ref<SalaryItem[]>([])
const rows = ref<SalaryGridRow[]>([])
const loading = ref(false)
const computing = ref(false)

/* ====== 列结构 / 三层表头 / 合计：渲染逻辑在 composables/useSalaryGrid.ts（与工资报表页共用同一套） ====== */
const cols = computed<Col[]>(() => buildCols(items.value))
const headerRows = computed<HCell[][]>(() => buildHeaderRows(cols.value))
const totals = computed<Record<string, number>>(() => gridTotals(items.value, rows.value))

/* ====== 单元格编辑 ====== */
const editingCell = ref<{ rowId: string; key: string } | null>(null)
const editVal = ref<number | null>(null)

function startEdit(row: SalaryGridRow, key: string) {
  editingCell.value = { rowId: row.employee_id, key }
  editVal.value = row.values[key] ?? null
}
function isEditing(row: SalaryGridRow, key: string) {
  return editingCell.value?.rowId === row.employee_id && editingCell.value?.key === key
}
function clearEdit() {
  editingCell.value = null
}
async function commitEdit(row: SalaryGridRow, key: string) {
  const old = row.values[key] ?? null
  const v = editVal.value
  editingCell.value = null
  if (v === old) return
  try {
    await saveSalaryGrid(curMonth.value, [{ employee_id: row.employee_id, item_key: key, value: v }])
    row.values[key] = v
  } catch { /* interceptor 已提示 */ }
}

/* ====== 支付状态 ====== */
async function savePayment(row: SalaryGridRow, status: string) {
  try {
    await saveSalaryGrid(curMonth.value, undefined, [{ employee_id: row.employee_id, payment_status: status }])
    row.payment_status = status
    row.paid_at = status === "paid" ? new Date().toISOString() : null
  } catch { /* interceptor 已提示 */ }
}

/* ====== 备注 ====== */
async function commitRemark(row: SalaryGridRow) {
  try {
    await saveSalaryGrid(curMonth.value, undefined, undefined, [{ employee_id: row.employee_id, remark: row.remark || null }])
  } catch { /* interceptor 已提示 */ }
}

/* ====== 数据 ====== */
async function fetchGrid() {
  if (!curMonth.value) curMonth.value = new Date().toISOString().slice(0, 7)
  loading.value = true
  try {
    const [it, g] = await Promise.all([getSalaryItems(), getSalaryGrid(curMonth.value)])
    items.value = (it || []).filter(i => i.is_active).sort((a, b) => a.sort_order - b.sort_order)
    rows.value = g?.rows || []
  } catch { /* interceptor 已提示 */ }
  finally { loading.value = false }
}

async function computeAll() {
  if (!curMonth.value) curMonth.value = new Date().toISOString().slice(0, 7)
  try {
    await ElMessageBox.confirm("重新计算会更新公式列；手工填写或手动改过的格子会保留（想恢复计算，把该格清空后重新计算即可），确定继续吗？", "计算工资", { type: "warning" })
  } catch { return }
  computing.value = true
  try {
    const r = await computeSalaryGrid(curMonth.value)
    ElMessage.success(`已计算 ${r.computed} 人${r.errors?.length ? `，失败 ${r.errors.length} 人` : ""}`)
    if (r.errors?.length) ElMessage.warning(r.errors.join("；"))
    await fetchGrid()
  } catch { /* interceptor 已提示 */ }
  finally { computing.value = false }
}

/* ====== 指标设置 ====== */
const showItems = ref(false)
const itemsDraft = ref<SalaryItem[]>([])
const newItem = ref({ key: "", label: "", formula: "", sort_order: 0, is_manual: false, group1: null as string | null, group2: null as string | null })
const itemsSaving = ref(false)
const templates = ref<SalaryItemTemplate[]>([])
const curTemplateId = ref<string>("")
const paramHints = ref<{ name: string; label: string }[]>([])
const group1Options = ["应发金额", "应扣金额"]
const group2Options = ["基本部分", "绩效部分", "考勤栏", "代缴费用"]

const varHints = [
  { name: "base", label: "月工资标准(规则)" }, { name: "ot_rate", label: "加班费率(规则已删,恒0)" },
  { name: "bonus_std", label: "绩效标准(规则已删,恒0)" }, { name: "subsidy_std", label: "伙食补助标准(规则已删,恒0)" },
  { name: "att_bonus", label: "全勤奖标准(规则已删,恒0)" }, { name: "social", label: "社保金额(规则)" },
  { name: "housing", label: "公积金(规则已删,恒0)" }, { name: "ded_std", label: "其他扣款(规则已删,恒0)" },
  { name: "ot_hours", label: "当月加班工时" }, { name: "attend_days", label: "出勤天数" },
  { name: "half_days", label: "半天数" }, { name: "missed_days", label: "旷工天数" },
  { name: "absent_days", label: "未出勤天数" }, { name: "records", label: "有考勤记录天数" },
  { name: "work_days", label: "月内非周末天数" },
]
const examples = [
  "ot_hours * (base / 21.75 / 8) * (ot_rate or 1.5) → 加班费",
  "att_bonus if (missed_days == 0 and absent_days == 0) else 0 → 全勤奖",
  "max(0, gross - deduction) → 实发工资",
  "200 if attend_days >= work_days else 100 → 出勤满勤的阶梯补贴",
]

async function openItems() {
  const [its, pr, tpls] = await Promise.all([getSalaryItems(), getSalaryParams(curMonth.value), getSalaryTemplates()])
  itemsDraft.value = its || []
  templates.value = tpls || []
  paramHints.value = (pr?.params || []).map(p => ({
    name: p.key,
    label: `${p.label}${p.value != null ? " = " + p.value : ""}`,
  }))
  const maxOrder = itemsDraft.value.reduce((m, i) => Math.max(m, i.sort_order), 0)
  newItem.value = { key: "", label: "", formula: "", sort_order: maxOrder + 1, is_manual: false, group1: null, group2: null }
  showItems.value = true
}
function addNewItem() {
  if (!newItem.value.label || !newItem.value.key) {
    ElMessage.warning("请填写名称和 key")
    return
  }
  if (!newItem.value.is_manual && !newItem.value.formula) {
    ElMessage.warning("请填写公式，或勾选「手」改为手工填写")
    return
  }
  itemsDraft.value.push({ id: "", key: newItem.value.key, label: newItem.value.label,
    formula: newItem.value.formula, sort_order: newItem.value.sort_order,
    is_active: true, is_builtin: false, is_manual: newItem.value.is_manual,
    group1: newItem.value.group1 || null, group2: newItem.value.group2 || null })
  newItem.value = { key: "", label: "", formula: "", sort_order: newItem.value.sort_order + 1, is_manual: false, group1: null, group2: null }
}
async function removeItem(it: SalaryItem) {
  if (it.is_builtin) return
  if (!it.id) { itemsDraft.value = itemsDraft.value.filter(x => x !== it); return }
  try {
    await ElMessageBox.confirm(`删除指标「${it.label}」？该指标的历史单元格值也会一并删除。`, "删除指标", { type: "warning" })
  } catch { return }
  await deleteSalaryItem(it.id)
  itemsDraft.value = itemsDraft.value.filter(x => x.id !== it.id)
}
async function saveItems() {
  itemsSaving.value = true
  try {
    for (const it of itemsDraft.value) {
      if (it.id) {
        await updateSalaryItem(it.id, {
          label: it.label, formula: it.formula, sort_order: it.sort_order,
          is_active: it.is_active, is_manual: it.is_manual,
          group1: it.group1 || null, group2: it.group2 || null,
        })
      } else if (it.key) {
        await createSalaryItem({ key: it.key, label: it.label, formula: it.formula, sort_order: it.sort_order, is_manual: it.is_manual, group1: it.group1 || null, group2: it.group2 || null })
      }
    }
    ElMessage.success("指标已保存")
    showItems.value = false
    await fetchGrid()
  } catch { /* 公式校验错误由 interceptor 提示 */ }
  finally { itemsSaving.value = false }
}

/* ====== 指标设置模板 ====== */

function snapshotDraft(): SalaryItemSnapshot[] {
  // 模板 = 当前启用的列布局；停用列不入模板（应用时模板外的列统一停用）
  return itemsDraft.value.filter(it => it.is_active).map(it => ({
    key: it.key, label: it.label, formula: it.formula, sort_order: it.sort_order,
    is_active: it.is_active, is_manual: it.is_manual,
    group1: it.group1 || null, group2: it.group2 || null,
  }))
}

async function saveAsTemplate() {
  const snap = snapshotDraft()
  if (!snap.length) { ElMessage.warning("当前没有可保存的指标"); return }
  let name: string
  try {
    const r = await ElMessageBox.prompt("模板名称", "存为模板", { inputValidator: (v: string) => (v || "").trim() ? true : "名称不能为空" })
    name = (r.value || "").trim()
  } catch { return }
  const exist = templates.value.find(t => t.name === name)
  try {
    if (exist) {
      const ok = await ElMessageBox.confirm(`模板「${name}」已存在，覆盖？`, "提示", { type: "warning" }).catch(() => false)
      if (!ok) return
      await updateSalaryTemplate(exist.id, { items: snap })
      ElMessage.success("模板已更新")
    } else {
      await createSalaryTemplate(name, snap)
      ElMessage.success("模板已保存")
    }
  } catch { return }
  templates.value = (await getSalaryTemplates()) || []
  curTemplateId.value = exist ? exist.id : ""
}

async function applyTemplate() {
  if (!curTemplateId.value) return
  const t = templates.value.find(x => x.id === curTemplateId.value)
  const ok = await ElMessageBox.confirm(
    `应用模板「${t?.name}」会用模板里的指标替换当前配置；当前有但模板里没有的列会停用隐藏（历史数值保留）。应用后请重新计算。`,
    "应用模板", { type: "warning" }).catch(() => false)
  if (!ok) return
  try {
    await applySalaryTemplate(curTemplateId.value)
    ElMessage.success("模板已应用")
    showItems.value = false
    await fetchGrid()
  } catch { /* 后端错误由 interceptor 提示 */ }
}

async function renameTemplate() {
  if (!curTemplateId.value) return
  const t = templates.value.find(x => x.id === curTemplateId.value)
  let name: string
  try {
    const r = await ElMessageBox.prompt("新名称", "重命名模板", { inputValue: t?.name, inputValidator: (v: string) => (v || "").trim() ? true : "名称不能为空" })
    name = (r.value || "").trim()
  } catch { return }
  try {
    await updateSalaryTemplate(curTemplateId.value, { name })
    ElMessage.success("已重命名")
  } catch { return }
  templates.value = (await getSalaryTemplates()) || []
}

async function deleteTemplate() {
  if (!curTemplateId.value) return
  const t = templates.value.find(x => x.id === curTemplateId.value)
  const ok = await ElMessageBox.confirm(`删除模板「${t?.name}」？`, "删除模板", { type: "warning" }).catch(() => false)
  if (!ok) return
  try {
    await deleteSalaryTemplate(curTemplateId.value)
    ElMessage.success("模板已删除")
  } catch { return }
  curTemplateId.value = ""
  templates.value = (await getSalaryTemplates()) || []
}

/* ====== 工资参数 ====== */
const showParams = ref(false)
const paramsDraft = ref<SalaryParam[]>([])
const newParam = ref({ key: "", label: "", sort_order: 0 })
const paramsSaving = ref(false)

async function openParams() {
  if (!curMonth.value) curMonth.value = new Date().toISOString().slice(0, 7)
  const pr = await getSalaryParams(curMonth.value)
  paramsDraft.value = pr?.params || []
  const maxOrder = paramsDraft.value.reduce((m, p) => Math.max(m, p.sort_order), 0)
  newParam.value = { key: "", label: "", sort_order: maxOrder + 1 }
  showParams.value = true
}
function addNewParam() {
  if (!newParam.value.key || !newParam.value.label) {
    ElMessage.warning("请填写参数名称和 key")
    return
  }
  paramsDraft.value.push({ id: "", key: newParam.value.key, label: newParam.value.label,
    sort_order: newParam.value.sort_order, value: null })
  newParam.value = { key: "", label: "", sort_order: newParam.value.sort_order + 1 }
}
async function removeParam(p: SalaryParam) {
  if (p.id) {
    try {
      await ElMessageBox.confirm(`删除参数「${p.label}」？所有月份的取值一并删除。`, "删除参数", { type: "warning" })
    } catch { return }
    await deleteSalaryParam(p.id)
  }
  paramsDraft.value = paramsDraft.value.filter(x => x !== p)
}
async function saveParams() {
  paramsSaving.value = true
  try {
    const values: { key: string; value: number | null }[] = []
    for (const p of paramsDraft.value) {
      if (p.id) {
        await updateSalaryParam(p.id, { label: p.label, sort_order: p.sort_order })
      } else {
        const created = await createSalaryParam({ key: p.key, label: p.label, sort_order: p.sort_order })
        p.id = created.id
      }
      values.push({ key: p.key, value: p.value })
    }
    await saveSalaryParamValues(curMonth.value, values)
    ElMessage.success("参数已保存")
    showParams.value = false
  } catch { /* interceptor 已提示 */ }
  finally { paramsSaving.value = false }
}

onMounted(() => fetchGrid())
</script>

<style scoped>
.sheet-wrapper { overflow-x: auto; overflow-y: auto; max-height: calc(100vh - 300px); border: 1px solid #e4e7ed; border-radius: 4px; background: #fff; padding-bottom: 14px; }
.sal-sheet { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 15px; white-space: nowrap; }
.sal-sheet th, .sal-sheet td { border: 2px solid #666; padding: 5px 6px; }
.sal-sheet thead { position: sticky; top: 0; z-index: 2; }
.sal-sheet thead th { font-weight: 700; text-align: center; color: #000; border-color: #333; }
.col-fixed { min-width: 72px; }
.col-item { min-width: 100px; text-align: center; }
.manual-badge { display: inline-block; margin-left: 3px; padding: 0 3px; border-radius: 3px; font-size: 10px; line-height: 14px; color: var(--el-color-warning); background: #fdf6ec; border: 1px solid #f3d19e; }
.cell-center { text-align: center; }
.cell-name { font-weight: 600; color: #303133; min-width: 96px; }
.cell-num { text-align: right; font-family: "SF Mono", "Courier New", monospace; font-weight: 700; color: #000; min-width: 100px; cursor: cell; }
.cell-num:hover { background: #f5f7fa; }
.cell-strong { font-weight: 700; color: #000; }
.sal-footer td { background: #E0E0E0; font-weight: 700; color: #000; }
.cell-footer-label { text-align: right; font-weight: 700; padding-right: 10px; }
.items-help { background: #f5f7fa; border: 1px solid #e4e7ed; border-radius: 4px; padding: 10px 12px; margin-bottom: 12px; }
.help-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px 12px; }
.help-item { font-size: 12px; color: #606266; }
.help-item code, .help-ex code { background: #fff; border: 1px solid #dcdfe6; border-radius: 3px; padding: 0 4px; font-size: 12px; color: var(--el-color-primary); }
.help-examples { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 12px; }
.help-ex { font-size: 12px; color: #606266; }
.tpl-bar { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.items-list { max-height: 40vh; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; }
.item-row { display: flex; align-items: center; gap: 8px; }
.item-key { min-width: 80px; font-size: 12px; color: var(--el-text-color-secondary); }
.new-item { margin-top: 4px; }
</style>
