import type { SalaryItem, SalaryGridRow } from "@/api/salaries"

/* ====== 工资网格渲染共用逻辑 ======
   工资表页（可编辑）与工资报表页（只读打印）共用同一份列/表头/合计计算，
   保证两个页面永远渲染同一套列，不再漂移。 */

export interface Col {
  type: "fixed" | "item" | "remark" | "payment"
  key: string
  label: string
  group1: string | null
  group2: string | null
  sort_order: number
  formula?: string
  is_manual?: boolean
}

export interface HCell {
  label: string
  colspan: number
  rowspan: number
  key?: string
  formula?: string
  is_manual?: boolean
}

export function buildCols(items: SalaryItem[]): Col[] {
  const itemCols: Col[] = items.map(it => ({
    type: "item", key: it.key, label: it.label, group1: it.group1, group2: it.group2,
    sort_order: it.sort_order, formula: it.formula, is_manual: it.is_manual,
  }))
  // 备注/支付状态是文本/选择列，不作为数值指标，但参与表头分组渲染
  const virtuals: Col[] = [
    { type: "remark", key: "__remark", label: "备注", group1: null, group2: null, sort_order: 21 },
    { type: "payment", key: "__payment", label: "支付状态", group1: null, group2: null, sort_order: 21.5 },
  ]
  const sorted = [...itemCols, ...virtuals].sort((a, b) => a.sort_order - b.sort_order)
  return [
    { type: "fixed", key: "no", label: "工号", group1: null, group2: null, sort_order: -3 },
    { type: "fixed", key: "dept", label: "部门", group1: null, group2: null, sort_order: -2 },
    { type: "fixed", key: "name", label: "姓名", group1: null, group2: null, sort_order: -1 },
    ...sorted,
  ]
}

// 顶层每组一种语义色，用 color-mix 与主题表面混合，深浅模式都柔和可读
const tint = (c: string) => `color-mix(in srgb, ${c} 30%, var(--ad-card))`

export const HDR_BG: Record<string, string> = {
  no: tint("#90caf9"), dept: tint("#90caf9"), name: tint("#90caf9"),   // 工号/部门/姓名 蓝
  missed_days: tint("#f48fb1"),                                        // 旷工 粉
  att_std: tint("#ffcc80"),                                            // 全勤300 琥珀
  perf_std: tint("#fff59d"),                                           // 绩效300 黄
  basic: tint("#a5d6a7"),                                              // 月工资标准 绿
  "g:应发金额": tint("#81d4fa"),                                        // 应发金额 浅蓝
  "g:应扣金额": tint("#ce93d8"),                                        // 应扣金额 紫
  net: tint("#80cbc4"),                                                // 实发工资 青
  __remark: tint("#bcaaa4"),                                           // 备注 棕
  __payment: tint("#9fa8da"),                                          // 支付状态 靛
  last_net: tint("#ffab91"),                                           // 上月实发工资 深橙
}

export function hdrBg(h: HCell, ri: number): string {
  if (ri === 0) return HDR_BG[h.key || ""] ?? tint("#90a4ae")  // 顶层：每组独立色
  return ri === 1 ? tint("#90a4ae") : "var(--ad-card)"         // 二级浅灰 / 叶子卡片色
}

export function hdrStyle(h: HCell, ri: number) {
  const st: Record<string, string> = { background: hdrBg(h, ri), color: "var(--ad-text)" }
  if (ri === 0) st.borderRight = "3px solid var(--ad-border)" // 顶层每组右侧加粗分隔线
  return st
}

export function buildHeaderRows(cols: Col[]): HCell[][] {
  const row1: HCell[] = []
  const row2: HCell[] = []
  const row3: HCell[] = []
  // 固定身份列占满三层
  for (const c of cols) {
    if (c.type === "fixed") row1.push({ label: c.label, colspan: 1, rowspan: 3, key: c.key })
  }
  const dataCols = cols.filter(c => c.type !== "fixed")
  // 按 group1 连续切段；独立列（group1 为空）各自成段，不合并
  const segments: { cols: Col[] }[] = []
  for (const c of dataCols) {
    const last = segments[segments.length - 1]
    if (c.group1 && last && last.cols[0].group1 === c.group1) last.cols.push(c)
    else segments.push({ cols: [c] })
  }
  for (const seg of segments) {
    const g1 = seg.cols[0].group1
    if (!g1) {
      // 独立列：跨三层
      const c = seg.cols[0]
      row1.push({ label: c.label, colspan: 1, rowspan: 3, key: c.key, formula: c.formula, is_manual: c.is_manual })
      continue
    }
    const hasSub = seg.cols.some(c => c.group2)
    if (hasSub) {
      // 有二级组：row1 大组 colspan，row2 二级组，row3 叶子
      row1.push({ label: g1, colspan: seg.cols.length, rowspan: 1, key: "g:" + g1 })
      let i = 0
      while (i < seg.cols.length) {
        const c = seg.cols[i]
        if (!c.group2) {
          row2.push({ label: c.label, colspan: 1, rowspan: 2, key: c.key, formula: c.formula, is_manual: c.is_manual })
          i++
        } else {
          const g2 = c.group2
          let j = i
          while (j < seg.cols.length && (seg.cols[j].group2 ?? null) === g2) j++
          row2.push({ label: g2, colspan: j - i, rowspan: 1, key: "g:" + g2 })
          i = j
        }
      }
      for (const c of seg.cols) {
        if (c.group2) row3.push({ label: c.label, colspan: 1, rowspan: 1, key: c.key, formula: c.formula, is_manual: c.is_manual })
      }
    } else {
      // 无二级组：row1 大组 rowspan=2，row3 叶子
      row1.push({ label: g1, colspan: seg.cols.length, rowspan: 2, key: "g:" + g1 })
      for (const c of seg.cols) {
        row3.push({ label: c.label, colspan: 1, rowspan: 1, key: c.key, formula: c.formula, is_manual: c.is_manual })
      }
    }
  }
  return [row1, row2, row3]
}

export function gridTotals(items: SalaryItem[], rows: SalaryGridRow[]): Record<string, number> {
  const t: Record<string, number> = {}
  for (const it of items) {
    let sum = 0
    for (const r of rows) {
      const v = r.values[it.key]
      if (v != null) sum += v
    }
    t[it.key] = sum
  }
  return t
}

export const fmtVal = (v: number | null | undefined) => (v == null ? "" : Number(v).toFixed(2))

export function deptLabel(v?: string | null) {
  if (!v) return ""
  const m: Record<string, string> = { design: "设计部", production: "生产部", installation: "安装部", sales: "销售部", finance: "财务部", admin: "行政部" }
  return m[v] || v
}

export const isStrong = (key: string) => key === "gross" || key === "net" || key === "deduction" || key.endsWith("_total")
