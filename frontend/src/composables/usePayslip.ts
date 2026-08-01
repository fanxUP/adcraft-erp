import type { SalaryItem, SalaryGridRow } from "@/api/salaries"
import { deptLabel } from "./useSalaryGrid"

/* ====== 工资条生成（纯函数，无组件依赖）======
   单张与批量共用 buildPayslipSection/buildPayslipDocument，
   弹窗预览与打印是同一份输出，杜绝漂移。
   数据全部来自工资报表页已加载的 getSalaryGrid 的 items + rows，后端零改动。 */

export interface PayslipMeta {
  month: string            // "2026-08"
  company: string          // 公司名（打印标题用）
  employee: SalaryGridRow  // 按 employee_id 过滤后的单行
  items: SalaryItem[]      // 该月指标列（含 group1/group2 分区信息）
  position?: string        // 岗位（grid 无此字段，默认显示 "—"）
}

export const DEFAULT_COMPANY = "XX建设工程有限公司" // 占位，待用户提供真实公司名

const PAYMENT_LABEL: Record<string, string> = { pending: "待核算", calculated: "已核算", paid: "已发放" }
const GROUP_ORDER = ["应发金额", "应扣金额", "代缴部分"]
const AGGREGATE_KEYS = new Set(["gross", "deduction", "net"]) // 合计键只进合计区，不重复出现在明细表

const fmtPs = (v: number | null | undefined): string => (v == null ? "—" : Number(v).toFixed(2))

function esc(s: string): string {
  return String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]!))
}

export function payslipMonthLabel(month: string): string {
  if (!month) return ""
  const [y, m] = month.split("-")
  return `${y}年${Number(m)}月`
}

/** 明细分区：过滤停用列/合计键/_total 汇总列，按 group1 归桶，桶序白名单 + 首次出现顺序 */
function groupBuckets(items: SalaryItem[]): { group: string; items: SalaryItem[] }[] {
  const byGroup = new Map<string, SalaryItem[]>()
  for (const it of items) {
    if (it.is_active === false || !it.group1) continue
    if (AGGREGATE_KEYS.has(it.key) || it.key.endsWith("_total")) continue
    const arr = byGroup.get(it.group1) || []
    arr.push(it)
    byGroup.set(it.group1, arr)
  }
  const known = GROUP_ORDER.filter(g => byGroup.has(g))
  const extra = [...byGroup.keys()].filter(g => !GROUP_ORDER.includes(g))
  return [...known, ...extra].map(g => ({ group: g, items: byGroup.get(g)! }))
}

/** 取合计值；对应键无值时回退为该组内各项求和（避免伪造未计算的数据） */
function pickValue(values: Record<string, number | null>, items: SalaryItem[], key: string, groups: string[]): number | null {
  const v = values[key]
  if (v != null) return v
  let sum = 0
  let has = false
  for (const it of items) {
    if (it.is_active === false || !it.group1 || !groups.includes(it.group1)) continue
    if (AGGREGATE_KEYS.has(it.key) || it.key.endsWith("_total")) continue
    const x = values[it.key]
    if (x != null) { sum += x; has = true }
  }
  return has ? sum : null
}

/** 单张工资条正文（不含 html/head/style），批量时逐张拼接 */
export function buildPayslipSection(meta: PayslipMeta): string {
  const { company, employee, position } = meta
  const label = payslipMonthLabel(meta.month)
  const dept = deptLabel(employee.department) || "—"
  const pay = PAYMENT_LABEL[employee.payment_status || "pending"] || "待核算"
  const buckets = groupBuckets(meta.items)
  const gross = pickValue(employee.values, meta.items, "gross", ["应发金额"])
  const deduction = pickValue(employee.values, meta.items, "deduction", ["应扣金额", "代缴部分"])
  const net = employee.values["net"] ?? null

  const detail = buckets.map(b =>
    `<thead><tr class="ps-group"><th colspan="2">${esc(b.group)}</th></tr>` +
    `<tr class="ps-hdr"><th style="width:60%">项目</th><th>金额（元）</th></tr></thead>` +
    `<tbody>${b.items.map(it =>
      `<tr><td class="ps-item">${esc(it.label)}</td><td class="ps-amt">${fmtPs(employee.values[it.key])}</td></tr>`
    ).join("")}</tbody>`
  ).join("")

  return `<div class="payslip">` +
    `<div class="ps-title">${esc(company)} ${label}工资条</div>` +
    `<div class="ps-sub">（工资确认单）</div>` +
    `<div class="ps-info">` +
      `<span>工号：<b>${esc(employee.employee_no || "—")}</b></span>` +
      `<span>姓名：<b>${esc(employee.employee_name)}</b></span>` +
      `<span>部门：${esc(dept)}</span>` +
      `<span>岗位：${esc(position || "—")}</span>` +
      `<span>支付状态：${esc(pay)}</span>` +
    `</div>` +
    `<table class="ps-detail">${detail}</table>` +
    `<table class="ps-summary">` +
      `<tr><td class="label">应发合计</td><td class="ps-amt">${fmtPs(gross)}</td></tr>` +
      `<tr><td class="label">应扣合计</td><td class="ps-amt">${fmtPs(deduction)}</td></tr>` +
      `<tr class="ps-net"><td class="label">实发工资</td><td class="ps-amt">${fmtPs(net)}</td></tr>` +
    `</table>` +
    `<div class="ps-remark">备注：<span>${esc(employee.remark || "—")}</span></div>` +
    `<div class="ps-sign">` +
      `<div class="ps-line">员工签字：<span class="ps-blank"></span>日期：<span class="ps-blank ps-date"></span></div>` +
      `<div class="ps-line">财务审核：<span class="ps-blank"></span>日期：<span class="ps-blank ps-date"></span></div>` +
      `<div class="ps-note">本人确认上述工资明细准确无误，如有异议请在签收之日起 3 个工作日内向财务提出。</div>` +
    `</div>` +
  `</div>`
}

/** 完整打印文档。autoPrint=true 时加载后自动打印并关闭（批量用）；弹窗预览传 false */
export function buildPayslipDocument(metas: PayslipMeta[], opts?: { autoPrint?: boolean }): string {
  const auto = opts?.autoPrint ?? false
  const body = metas.map(m => buildPayslipSection(m)).join("")
  const script = auto
    ? '<script>window.onload=function(){setTimeout(function(){window.print();window.close()},500)}</scr' + 'ipt>'
    : ""
  return '<!DOCTYPE html><html><head><meta charset="utf-8"><title>工资条</title>'
    + '<style>' + PAYSLIP_STYLE + '</style>'
    + '</head><body>' + body + script + '</body></html>'
}

/** 唯一 CSS 数据源：A4 竖版 + 单条一页 + 签名栏（预览 iframe 与打印共用，避免漂移） */
export const PAYSLIP_STYLE = `
@page { size: A4 portrait; margin: 12mm 10mm; }
* { -webkit-print-color-adjust: exact; print-color-adjust: exact; box-sizing: border-box; }
body { margin: 0; font-family: "Songti SC", SimSun, "PingFang SC", "Microsoft YaHei", serif; color: #000; }
.payslip { width: 190mm; margin: 0 auto; font-size: 12px; page-break-after: always; break-inside: avoid; }
.payslip:last-child { page-break-after: auto; }
.ps-title { text-align: center; font-size: 22px; font-weight: 700; letter-spacing: 3px; padding: 4px 0 2px; }
.ps-sub { text-align: center; font-size: 12px; color: #555; padding-bottom: 8px; }
.ps-info { display: flex; flex-wrap: wrap; gap: 4px 24px; border: 1px solid #333; border-bottom: none; padding: 6px 10px; font-size: 12px; }
.ps-detail { width: 100%; border-collapse: collapse; }
.ps-detail th, .ps-detail td { border: 1px solid #333; padding: 4px 8px; font-size: 12px; }
.ps-group th { background: #e8eef5; font-weight: 700; text-align: left; padding: 4px 10px; }
.ps-hdr th { background: #f5f5f5; }
.ps-item { text-align: left; }
.ps-amt { text-align: right; font-family: "Courier New", monospace; font-weight: 700; white-space: nowrap; }
.ps-summary { width: 100%; border-collapse: collapse; margin-top: 8px; }
.ps-summary td { border: 1px solid #333; padding: 4px 10px; font-size: 13px; }
.ps-summary td.label { text-align: right; background: #f5f5f5; font-weight: 700; width: 50%; }
.ps-net td { background: #e2f0e2; font-weight: 700; font-size: 14px; }
.ps-remark { margin-top: 8px; border: 1px solid #333; padding: 4px 8px; min-height: 22px; font-size: 12px; }
.ps-sign .ps-line { margin-top: 8px; font-size: 12px; }
.ps-blank { display: inline-block; width: 64mm; height: 7mm; vertical-align: bottom; border-bottom: 1px solid #333; margin: 0 4px; }
.ps-date { width: 30mm; }
.ps-note { margin-top: 10px; font-size: 11px; color: #666; }
`
