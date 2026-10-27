import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as Vue from 'vue'
import { createRenderer, h, nextTick, reactive, ssrContextKey } from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { transpileModule, ScriptTarget } from 'typescript'
import * as ElementComponents from 'element-plus/es'
import type { Component, VNode } from 'vue'
import type { OutsourceOrderItemSummary, OutsourceOrderItemSummaryResponse, TaskOrderItemOption } from '@/types/api'
import { buildTaskItemSections, filterTaskItems, taskCompletionSummary } from './taskDetailPresentation'

const api = vi.hoisted(() => ({ options: vi.fn(), assignees: vi.fn(), confirm: vi.fn(), reassign: vi.fn(), activity: vi.fn(), summary: vi.fn(), records: vi.fn(), vendors: vi.fn(), send: vi.fn(), push: vi.fn(), permission: vi.fn<(permission: string) => boolean>(() => true) }))
vi.mock('@/api/outsource', () => ({ getOutsourceOrderItemsSummary: api.summary, getOutsourceTasks: api.records, getOutsourceVendors: api.vendors, sendOutsourceOrderItem: api.send }))
vi.mock('vue-router', () => ({ useRouter: () => ({ push: api.push }) }))
vi.mock('@/api/tasks', () => ({
  getTaskOrderItemOptions: api.options, getTaskAssigneeOptions: api.assignees,
  linkHistoricalDesignTaskItems: vi.fn(), linkHistoricalProductionTaskItems: vi.fn(), linkHistoricalInstallationTaskItems: vi.fn(),
  reassignDesignTaskItems: api.reassign, reassignProductionTaskItems: api.reassign, reassignInstallationTaskItems: api.reassign,
  getTaskActivity: api.activity,
}))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => ({ user: { id: 'me' }, hasPermission: api.permission }) }))
vi.mock('@/components/ui', async () => {
  const { h } = await import('vue')
  return { StatusTag: (props: Record<string, unknown>) => h('status-tag', props) }
})
vi.mock('element-plus', () => ({ ElMessage: { info: vi.fn(), success: vi.fn(), error: vi.fn(), warning: vi.fn() }, ElMessageBox: { confirm: api.confirm, prompt: vi.fn() } }))
vi.mock('element-plus/es/components/base/style/css', () => ({}))
vi.mock('element-plus/es/components/loading/style/css', () => ({}))
vi.mock('element-plus/es/components/button/style/css', () => ({}))
vi.mock('element-plus/es/components/card/style/css', () => ({}))
vi.mock('element-plus/es/components/tag/style/css', () => ({}))
vi.mock('element-plus/es/components/input/style/css', () => ({}))
vi.mock('element-plus/es/components/select/style/css', () => ({}))
vi.mock('element-plus/es/components/option/style/css', () => ({}))
vi.mock('element-plus/es/components/checkbox/style/css', () => ({}))
vi.mock('element-plus/es/components/empty/style/css', () => ({}))
vi.mock('element-plus/es/components/icon/style/css', () => ({}))
vi.mock('element-plus/es/components/dialog/style/css', () => ({}))
vi.mock('element-plus/es/components/alert/style/css', () => ({}))
vi.mock('element-plus/es/components/radio-group/style/css', () => ({}))
vi.mock('element-plus/es/components/radio-button/style/css', () => ({}))
vi.mock('element-plus/es/components/pagination/style/css', () => ({}))
vi.mock('element-plus/es/components/form/style/css', () => ({}))
vi.mock('element-plus/es/components/form-item/style/css', () => ({}))
vi.mock('element-plus/es/components/input-number/style/css', () => ({}))
vi.mock('element-plus/es/components/date-picker/style/css', () => ({}))
vi.mock('element-plus/es', async () => {
  const { defineComponent, h } = await import('vue')
  const stub = (name: string) => defineComponent({ name, inheritAttrs: false, setup(_, { attrs, slots }) {
    return () => h(name, attrs, [slots.header?.(), slots.title?.(), slots.default?.(), slots.footer?.()])
  } })
  const form = defineComponent({ props: ['model', 'rules'], setup(props, { expose, slots }) {
    expose({ clearValidate: () => undefined, validate: async () => {
      for (const [key, rules] of Object.entries(props.rules as Record<string, { required?: boolean; validator?: (...args: unknown[]) => void }[]>)) {
        for (const rule of rules) {
          const value = props.model[key]
          if (rule.required && !value) throw new Error('required')
          if (rule.validator) await new Promise<void>((resolve, reject) => rule.validator!(rule, value, (error?: Error) => error ? reject(error) : resolve()))
        }
      }
      return true
    } })
    return () => h('el-form', {}, slots.default?.())
  } })
  return { ElLoadingDirective: {}, ElForm: form, ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() }, ...Object.fromEntries(['Button', 'Card', 'Tag', 'Input', 'Select', 'Option', 'Checkbox', 'Empty', 'Icon', 'Dialog', 'Alert', 'RadioGroup', 'RadioButton', 'Pagination', 'FormItem', 'InputNumber', 'DatePicker']
    .map(name => [`El${name}`, stub(`el-${name.toLowerCase()}`)])) }
})
import TaskOrderItemLinkCard from '@/components/tasks/TaskOrderItemLinkCard.vue'
import TaskCompletionAttachmentDialog from '@/components/tasks/TaskCompletionAttachmentDialog.vue'
import TaskActivityCard from '@/components/tasks/TaskActivityCard.vue'
import ProgressBar from '@/components/ui/ProgressBar.vue'
import TaskOutsourceDialogs from '@/components/outsource/TaskOutsourceDialogs.vue'

function item(id: string, fields: Partial<TaskOrderItemOption> = {}): TaskOrderItemOption {
  return {
    id, item_name: `明细${id}`, quantity: 1, sort_order: 0, stage: 'designing', stage_label: '设计中',
    stage_view: { code: 'designing', label: '设计中', tone: 'brand', terminal: false },
    is_linked: true, can_select: true, task_status: 'pending', assignee_state: 'unassigned',
    outsource_blocked: false, outsource_task_count: 0, outsource_task_nos: [], ...fields,
  }
}

describe('任务明细分项与筛选', () => {
  it('同名但不同 ID 的分项保持独立，旧名称分项和未分项仍保留', () => {
    const sections = buildTaskItemSections([
      item('a', { group_id: 'g1', group_name: '展板', sort_order: 2 }),
      item('b', { group_id: 'g2', group_name: '展板', sort_order: 1 }),
      item('c', { group_name: '旧分项', sort_order: 3 }), item('d', { group_name: '旧分项', sort_order: 4 }),
      item('e', { sort_order: 5 }),
    ])
    expect(sections.map(section => section.items.map(value => value.id))).toEqual([['b'], ['a'], ['c', 'd'], ['e']])
    expect(sections[3]?.name).toBe('未分项明细')
  })
  it('完成计数只统计本任务，保留已完成、未关联和退回明细', () => {
    const sections = buildTaskItemSections([item('a', { task_status: 'confirmed' }), item('b', { is_linked: false, task_status: null, can_select: false })])
    expect(sections[0]).toMatchObject({ completed: 1 })
    expect(sections[0]?.items.map(row => row.id)).toEqual(['a', 'b'])
    expect(buildTaskItemSections([item('c', { task_status: 'rolled_back', can_select: false })])[0]?.items[0]?.id).toBe('c')
  })
  it('任务范围、状态、执行人与关键词同时筛选，且不修改原数组', () => {
    const rows = [item('a', { assignee_user_id: 'me', material_process: '铝板', task_status: 'designing' }), item('b', { assignee_user_id: 'other' }), item('c', { is_linked: false })]
    const before = structuredClone(rows)
    expect(filterTaskItems(rows, 'linked', 'mine', ' 铝板 ', 'me').map(row => row.id)).toEqual(['a'])
    expect(filterTaskItems(rows, 'all', 'pending', '', 'me').map(row => row.id)).toEqual(['b', 'c'])
    expect(filterTaskItems(rows, 'all', 'mine', '', undefined)).toEqual([])
    expect(rows).toEqual(before)
  })
  it('进行中不混入完成、退回或未关联明细', () => {
    const rows = [item('a', { task_status: 'designing' }), item('b', { task_status: 'confirmed' }), item('c', { task_status: 'rolled_back' }), item('d', { task_status: 'cancelled' }), item('e', { task_status: 'designing', is_linked: false })]
    expect(filterTaskItems(rows, 'all', 'in_progress', '').map(row => row.id)).toEqual(['a'])
    expect(filterTaskItems(rows, 'all', 'completed', '').map(row => row.id)).toEqual(['b'])
  })
  it('概览完成条数排除已取消、已退回的工作，不冒充数量完成率', () => {
    const state = (status: string) => ({ status, progress_pct: 0, capabilities: {}, assignee_state: 'unassigned' as const })
    expect(taskCompletionSummary({ a: state('confirmed'), b: state('designing'), c: state('cancelled'), d: state('rolled_back') })).toEqual({ total: 2, completed: 1 })
    expect(taskCompletionSummary()).toEqual({ total: 0, completed: 0 })
  })
})

// Vite compiles node-side SFC imports for SSR; give this in-memory host their
// client render functions while retaining the actual setup/watch/event logic.
for (const [component, filename] of [
  [TaskOrderItemLinkCard, '../components/tasks/TaskOrderItemLinkCard.vue'],
  [TaskCompletionAttachmentDialog, '../components/tasks/TaskCompletionAttachmentDialog.vue'],
  [TaskActivityCard, '../components/tasks/TaskActivityCard.vue'],
  [ProgressBar, '../components/ui/ProgressBar.vue'],
  [TaskOutsourceDialogs, '../components/outsource/TaskOutsourceDialogs.vue'],
] as const) {
  const { descriptor } = parse(readFileSync(fileURLToPath(new URL(filename, import.meta.url)), 'utf8'))
  const script = compileScript(descriptor, { id: filename })
  const compiled = compileTemplate({ source: descriptor.template!.content, filename, id: filename, compilerOptions: { bindingMetadata: script.bindings } })
  if (compiled.errors.length) throw compiled.errors[0]
  const code = compiled.code.replace(/import \{([^}]+)\} from "vue"/g, (_line, names: string) => `const {${names.replace(/ as /g, ': ')}} = Vue`)
    .replace('export function render', 'return function render')
  ;(component as { render?: unknown }).render = new Function('Vue', transpileModule(code, { compilerOptions: { target: ScriptTarget.ES2020 } }).outputText)(Vue)
}

// Mount the actual Vue component with a tiny in-memory host. No DOM package or business server is needed.
interface HostNode { type: string; props: Record<string, unknown>; children: HostNode[]; parent: HostNode | null; text: string; addEventListener: (name: string, listener: unknown) => void; removeEventListener: () => void }
function hostNode(type: string, text = ''): HostNode {
  const node: HostNode = { type, text, props: {}, children: [], parent: null, addEventListener: (name, listener) => { node.props[`native:${name}`] = listener }, removeEventListener: () => undefined }
  return node
}
const renderer = createRenderer<HostNode, HostNode>({
  createElement: type => hostNode(type), createText: text => hostNode('#text', text), createComment: text => hostNode('#comment', text),
  setText: (node, text) => { node.text = text }, setElementText: (node, text) => { node.text = text; node.children = [] },
  parentNode: node => node.parent, nextSibling: node => { const siblings = node.parent?.children || []; return siblings[siblings.indexOf(node) + 1] || null },
  patchProp: (node, key, _before, value) => { node.props[key] = value },
  insert(node, parent, anchor) { if (node.parent) { const i = node.parent.children.indexOf(node); if (i >= 0) node.parent.children.splice(i, 1) }; node.parent = parent; const i = anchor ? parent.children.indexOf(anchor) : -1; parent.children.splice(i < 0 ? parent.children.length : i, 0, node) },
  remove(node) { if (node.parent) { const i = node.parent.children.indexOf(node); if (i >= 0) node.parent.children.splice(i, 1) }; node.parent = null },
})
function nodes(root: HostNode): HostNode[] { return [root, ...root.children.flatMap(nodes)] }
function content(node: HostNode): string { return node.text + node.children.map(content).join('') }
async function settle() { for (let i = 0; i < 12; i++) { await Promise.resolve(); await nextTick() } }
function mount(props: Record<string, unknown>, component: Component = TaskOrderItemLinkCard) {
  const root = hostNode('root')
  const app = renderer.createApp({ render: () => h(component, props) as VNode })
  app.provide(ssrContextKey, { modules: new Set() })
  for (const [name, component] of Object.entries(ElementComponents)) {
    if (name !== 'ElLoadingDirective') app.component(name, component as Component)
  }
  app.directive('loading', {})
  app.mount(root)
  return { root, unmount: () => app.unmount() }
}
function click(root: HostNode, label: string) {
  const button = nodes(root).find(node => node.type === 'el-button' && content(node).trim() === label)
  expect(button, `button ${label}`).toBeTruthy()
  ;(button!.props.onClick as (event: unknown) => void)({ stopPropagation: () => undefined })
}

describe('任务详情完成与刷新交互回归', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.permission.mockReturnValue(true)
    api.options.mockResolvedValue([item('a', { task_status: 'designing', actions: [{ key: 'complete', to_status: 'confirmed', label: '完成设计', allowed: true, kind: 'primary' }] })])
    api.assignees.mockResolvedValue([])
    api.confirm.mockResolvedValue(true)
    api.summary.mockResolvedValue({ items: [], order_level_task_count: 0 })
  })
  it('完成只打开一次资料确认；失败保留文件，成功后才关闭清空', async () => {
    const complete = vi.fn()
    const props = reactive({ taskType: 'design', taskId: 'task', orderId: 'order', currentItemIds: ['a'], currentStatus: 'designing', workflow: {}, changing: false, completionSuccessKey: 0, onComplete: complete })
    const view = mount(props)
    await settle()
    click(view.root, '完成设计')
    await settle()
    expect(api.confirm).not.toHaveBeenCalled()
    const input = nodes(view.root).find(node => node.type === 'input' && node.props.type === 'file')!
    const file = new File(['document'], 'design-proof.pdf', { type: 'application/pdf' })
    ;(input.props.onChange as (event: unknown) => void)({ target: { files: [file], value: '' } })
    await settle()
    click(view.root, '上传资料并完成')
    expect(complete).toHaveBeenCalledWith('a', [file], false)
    props.changing = true
    await settle()
    props.changing = false // failed request
    await settle()
    expect(content(view.root)).toContain('design-proof.pdf')
    const dialog = nodes(view.root).find(node => node.type === 'el-dialog')!
    expect(dialog.props.modelValue ?? dialog.props['model-value']).toBe(true)
    props.changing = true
    await settle()
    props.completionSuccessKey++ // successful request
    props.changing = false
    await settle()
    const closedDialog = nodes(view.root).find(node => node.type === 'el-dialog')!
    expect(closedDialog.props.modelValue ?? closedDialog.props['model-value']).toBe(false)
    expect(content(view.root)).not.toContain('design-proof.pdf')
    view.unmount()
  })
  it('关联刷新不依赖 task.updated_at 是否变化，会重新获取操作能力', async () => {
    const props = reactive({ taskType: 'design', taskId: 'task', orderId: 'order', currentStatus: 'designing', workflow: {}, changing: false, refreshKey: 0 })
    const view = mount(props)
    await settle()
    expect(api.options).toHaveBeenCalledTimes(1)
    props.refreshKey++
    await settle()
    expect(api.options).toHaveBeenCalledTimes(2)
    view.unmount()
  })
  it.each(['design', 'production', 'installation'])('%s 明细直接展示进度条，已完成分项也可见，未知进度不冒充零', async taskType => {
    api.options.mockResolvedValue([
      item('a', { group_id: 'done', group_name: '已完成分项', task_status: 'completed', task_progress_pct: 100 }),
      item('b', { group_id: 'active', group_name: '执行中分项', task_status: 'designing', task_progress_pct: 55 }),
      item('c', { task_progress_pct: 0 }),
      item('d', { task_progress_pct: null }),
      item('e', { is_linked: false, task_progress_pct: 35 }),
    ])
    const view = mount({ taskType, taskId: 'task', orderId: 'order', currentStatus: 'pending', workflow: {}, changing: false })
    await settle()
    const bars = nodes(view.root).filter(node => node.props.role === 'progressbar')
    expect(bars.map(node => node.props['aria-valuenow'])).toEqual([100, 55, 0])
    expect(bars[1]?.props['aria-label']).toBe('明细b本任务进度')
    expect(content(view.root)).toContain('55%')
    expect(content(view.root)).toContain('已完成分项')
    expect(content(view.root)).toContain('进度待核实')
    expect(content(view.root)).toContain('未关联')
    expect(nodes(view.root).some(node => ['details', 'el-collapse', 'el-collapse-item'].includes(node.type))).toBe(false)
    expect(content(view.root)).not.toContain('全部收起')
    expect(content(view.root)).toContain('销售单价')
    expect(nodes(view.root).some(node => node.props.role === 'columnheader' && content(node) === '金额')).toBe(true)
    view.unmount()
  })
  it('直接展示信息仍遵守明细价格权限', async () => {
    api.permission.mockImplementation(permission => !['order_item:view_price', 'finance:view_cost'].includes(permission))
    const view = mount({ taskType: 'design', taskId: 'task', orderId: 'order', currentStatus: 'pending', workflow: {}, changing: false })
    await settle()
    expect(content(view.root)).not.toContain('销售单价')
    expect(nodes(view.root).some(node => node.props.role === 'columnheader' && content(node) === '金额')).toBe(false)
    view.unmount()
  })
})

describe('任务活动加载交互', () => {
  beforeEach(() => { vi.clearAllMocks() })
  const event = (title: string) => ({ items: [{ id: title, kind: 'operation', title, actor: null, occurred_at: null, detail: null, changes: [] }], total: 1 })
  it('进入页面即加载，失败后可以重试，缺失时间和操作人明确显示', async () => {
    api.activity.mockRejectedValueOnce(new Error('load failed')).mockResolvedValueOnce(event('创建任务'))
    const view = mount({ taskType: 'design', taskId: 'task' }, TaskActivityCard)
    await settle()
    expect(api.activity).toHaveBeenCalledTimes(1)
    click(view.root, '重试')
    await settle()
    expect(content(view.root)).toContain('创建任务')
    expect(content(view.root)).toContain('时间未记录')
    expect(content(view.root)).toContain('操作人未记录')
    view.unmount()
  })
  it('切换任务后旧请求不会覆盖新任务记录', async () => {
    let resolveOld!: (value: unknown) => void
    api.activity.mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve }))
      .mockResolvedValueOnce(event('新任务记录'))
    const props = reactive({ taskType: 'design', taskId: 'old', refreshKey: 0 })
    const view = mount(props, TaskActivityCard)
    await settle()
    props.taskId = 'new'
    await settle()
    resolveOld(event('旧任务记录'))
    await settle()
    expect(content(view.root)).toContain('新任务记录')
    expect(content(view.root)).not.toContain('旧任务记录')
    view.unmount()
  })
  it.each(['design', 'production', 'installation'])('%s 日志直接展示操作人、版本与前后值，无需展开', async taskType => {
    api.activity.mockResolvedValueOnce({ items: [{
      id: 'change', kind: 'change', title: '订单变更', actor: '管理员', occurred_at: '2026-10-27T02:30:00+00:00', detail: '调整制作数量', version_no: 3,
      changes: [{ field: 'quantity', label: '数量', before: 6, after: 10, item: '展板' }],
    }], total: 1 })
    const view = mount({ taskType, taskId: 'task' }, TaskActivityCard)
    await settle()
    expect(content(view.root)).toContain('修改前')
    expect(content(view.root)).toContain('修改后')
    expect(content(view.root)).toContain('展板')
    expect(content(view.root)).toContain('操作人：管理员')
    expect(content(view.root)).toContain('订单版本 3')
    expect(content(view.root)).toContain('调整制作数量')
    const change = nodes(view.root).find(node => node.props.class === 'activity-change')!
    expect(content(change)).toBe('展板 / 数量：修改前：6→修改后：10')
    expect(nodes(view.root).find(node => node.type === 'time')?.props.datetime).toBe('2026-10-27T02:30:00+00:00')
    expect(nodes(view.root).some(node => ['details', 'table'].includes(node.type))).toBe(false)
    view.unmount()
  })
})

function allocation(id: string, fields: Partial<OutsourceOrderItemSummary> = {}): OutsourceOrderItemSummary {
  return { id, item_name: '同名明细', sort_order: 0, quantity: 10, allocated_quantity: 4, remaining_quantity: 6,
    planned_amount: 200, recognized_cost: 100, active_task_count: 1, status: '部分外协', can_send: true, requires_reason: false, ...fields }
}
function summary(items = [allocation('a')], fields: Partial<OutsourceOrderItemSummaryResponse> = {}): OutsourceOrderItemSummaryResponse {
  return { order_id: 'order', order_no: 'O-test', project_name: '测试项目', items, order_level_task_count: 0,
    order_level_planned_amount: 0, order_level_recognized_cost: 0, ...fields }
}
function edit(root: HostNode, type: string, value: unknown, predicate: (node: HostNode) => boolean = () => true) {
  const control = nodes(root).find(node => node.type === type && predicate(node))!
  expect(control, `control ${type}`).toBeTruthy()
  ;(control.props['onUpdate:modelValue'] as (value: unknown) => void)(value)
}
const taskProps = { taskType: 'design', taskId: 'task', orderId: 'order', projectName: '测试项目', currentStatus: 'designing', workflow: {}, changing: false }

describe('单张明细表中的外协分配', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.permission.mockReturnValue(true)
    api.options.mockResolvedValue([item('a')])
    api.summary.mockResolvedValue(summary())
    api.records.mockResolvedValue({ items: [], total: 0 })
    api.vendors.mockResolvedValue({ items: [{ id: 'vendor', name: '外协商', supplier_types: ['outsource'], service_types: ['design', 'production', 'installation'], is_active: true }], total: 1 })
    api.send.mockResolvedValue({ id: 'new' })
  })
  it.each(['design', 'production', 'installation'])('%s 在原明细行展示分配且不会预加载记录，数据按明细 ID 对应', async taskType => {
    api.options.mockResolvedValue([item('a', { item_name: '同名明细' }), item('b', { item_name: '同名明细' })])
    api.summary.mockResolvedValue(summary([allocation('b', { allocated_quantity: 8, remaining_quantity: 2 }), allocation('a')]))
    const view = mount({ ...taskProps, taskType })
    await settle()
    expect(nodes(view.root).filter(node => node.props.role === 'table')).toHaveLength(1)
    const rows = nodes(view.root).filter(node => node.props.role === 'row' && String(node.props.class).includes('item-table-row'))
    expect(content(rows[0]!)).toContain('已分配 4')
    expect(content(rows[1]!)).toContain('已分配 8')
    expect(api.summary).toHaveBeenCalledWith('order', { task_type: taskType, source_task_type: taskType, source_task_id: 'task' })
    expect(api.records).not.toHaveBeenCalled()
    expect(api.vendors).not.toHaveBeenCalled()
    expect(nodes(view.root).some(node => node.type === 'el-table')).toBe(false)
    view.unmount()
  })
  it.each(['outsource_task:read', 'outsource_center:read'])('缺少 %s 时不展示或加载外协，订单价格仍按自身权限显示', async permission => {
    api.permission.mockImplementation(value => value !== permission)
    const view = mount(taskProps)
    await settle()
    expect(api.summary).not.toHaveBeenCalled()
    expect(api.records).not.toHaveBeenCalled()
    expect(content(view.root)).not.toContain('查看外协')
    expect(content(view.root)).not.toContain('外协计划')
    expect(content(view.root)).toContain('销售小计')
    view.unmount()
  })
  it('只有外协读取权限时允许查看，但不显示发送按钮或加载供应商', async () => {
    api.permission.mockImplementation(value => value !== 'outsource_task:create')
    const view = mount(taskProps)
    await settle()
    expect(content(view.root)).not.toContain('追加外协')
    click(view.root, '查看外协')
    await settle()
    expect(api.records).toHaveBeenCalledWith(expect.objectContaining({ order_item_id: 'a', task_type: 'design', source_task_id: 'task' }))
    expect(api.vendors).not.toHaveBeenCalled()
    view.unmount()
  })
  it('没有供应商读取权限时仍可查看分配，不能打开发送表单', async () => {
    api.permission.mockImplementation(value => value !== 'outsource_vendor:read')
    const view = mount(taskProps)
    await settle()
    const send = nodes(view.root).find(node => node.type === 'el-button' && content(node).trim() === '追加外协')!
    expect(send.props.disabled).toBe(true)
    click(view.root, '追加外协')
    await settle()
    expect(api.vendors).not.toHaveBeenCalled()
    expect(content(view.root)).toContain('已分配 4')
    view.unmount()
  })
  it('外协摘要失败清除旧数量、禁止发送，重试成功后恢复', async () => {
    api.summary.mockRejectedValueOnce(new Error('摘要失败')).mockResolvedValueOnce(summary())
    const view = mount(taskProps)
    await settle()
    expect(content(view.root)).toContain('外协加载失败')
    expect(content(view.root)).not.toContain('已分配 0')
    const send = nodes(view.root).find(node => node.type === 'el-button' && content(node).trim() === '发送外协')!
    expect(send.props.disabled).toBe(true)
    click(view.root, '重试外协加载')
    await settle()
    expect(content(view.root)).toContain('已分配 4')
    expect(content(view.root)).not.toContain('外协加载失败')
    view.unmount()
  })
  it('切换任务后旧摘要不会覆盖新分配', async () => {
    let resolveOld!: (value: unknown) => void
    api.summary.mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve })).mockResolvedValueOnce(summary([allocation('a', { allocated_quantity: 7 })]))
    const props = reactive({ ...taskProps })
    const view = mount(props)
    await settle()
    props.taskId = 'new'
    await settle()
    resolveOld(summary([allocation('a', { allocated_quantity: 99 })]))
    await settle()
    expect(content(view.root)).toContain('已分配 7')
    expect(content(view.root)).not.toContain('已分配 99')
    view.unmount()
  })
  it('历史整单外协只显示提示和入口，不制造明细分配', async () => {
    api.summary.mockResolvedValue(summary([allocation('a', { allocated_quantity: 0, active_task_count: 0, planned_amount: 0 })], { order_level_task_count: 2, order_level_planned_amount: 500 }))
    const view = mount(taskProps)
    await settle()
    expect(content(view.root)).toContain('历史整单外协，未分摊到明细')
    expect(content(view.root)).toContain('已分配 0')
    click(view.root, '查看本任务外协记录')
    await settle()
    expect(api.records).toHaveBeenLastCalledWith(expect.objectContaining({ source_task_id: 'task', order_item_id: undefined }))
    view.unmount()
  })
  it('超量必须填写原因，发送只绑定当前明细，重复点击只提交一次并刷新关联区域', async () => {
    const changed = vi.fn()
    let resolveSend!: (value: unknown) => void
    api.send.mockImplementationOnce(() => new Promise(resolve => { resolveSend = resolve }))
    const view = mount({ ...taskProps, onOutsourceChanged: changed })
    await settle()
    click(view.root, '追加外协')
    await settle()
    edit(view.root, 'el-select', 'vendor', node => node.props.placeholder === '选择外协商')
    edit(view.root, 'el-inputnumber', 7)
    click(view.root, '确认发送')
    await settle()
    expect(api.send).not.toHaveBeenCalled()
    edit(view.root, 'el-input', '返工追加', node => node.props.rows === 3)
    click(view.root, '确认发送')
    click(view.root, '确认发送')
    await settle()
    expect(api.send).toHaveBeenCalledTimes(1)
    expect(api.send).toHaveBeenCalledWith('order', 'a', expect.objectContaining({ quantity: 7, remark: '返工追加', task_type: 'design', source_task_type: 'design', source_task_id: 'task' }))
    resolveSend({ id: 'new' })
    await settle()
    expect(nodes(view.root).filter(node => node.type === 'el-alert' && node.props.type === 'error').map(node => node.props.title)).toEqual([])
    expect(changed).toHaveBeenCalledOnce()
    expect(api.options).toHaveBeenCalledTimes(2)
    expect(api.summary).toHaveBeenCalledTimes(2)
    view.unmount()
  })
  it('发送失败保留数量、备注和供应商供重试', async () => {
    api.send.mockRejectedValueOnce(new Error('发送失败'))
    const view = mount(taskProps)
    await settle()
    click(view.root, '追加外协')
    await settle()
    edit(view.root, 'el-select', 'vendor', node => node.props.placeholder === '选择外协商')
    edit(view.root, 'el-input', '保留此备注', node => node.props.rows === 3)
    click(view.root, '确认发送')
    await settle()
    expect(nodes(view.root).some(node => node.type === 'el-alert' && String(node.props.title).includes('发送失败'))).toBe(true)
    expect(nodes(view.root).find(node => node.type === 'el-input' && node.props.rows === 3)?.props.modelValue).toBe('保留此备注')
    expect(nodes(view.root).find(node => node.type === 'el-select' && node.props.placeholder === '选择外协商')?.props.modelValue).toBe('vendor')
    click(view.root, '确认发送')
    await settle()
    expect(api.send).toHaveBeenCalledTimes(2)
    view.unmount()
  })
  it('财务成本与订单销售价格分别授权，隐藏后也不出现在记录弹窗中', async () => {
    api.permission.mockImplementation(value => value !== 'finance:view_cost')
    api.records.mockResolvedValue({ items: [{ id: 'ot', task_no: 'OT-test', quantity: 4, paid_amount: 999, source_task_id: 'task', source_task_type: 'design', status: 'pending' }], total: 1 })
    const view = mount(taskProps)
    await settle()
    expect(content(view.root)).toContain('销售小计')
    expect(content(view.root)).not.toContain('外协计划')
    click(view.root, '查看外协')
    await settle()
    expect(content(view.root)).toContain('OT-test')
    expect(content(view.root)).not.toContain('累计已付')
    expect(content(view.root)).not.toContain('999')
    view.unmount()
  })
  it('被同阶段外协阻塞时默认查看全部来源，范围切换及旧记录响应隔离正确', async () => {
    api.options.mockResolvedValue([item('a', { outsource_blocked: true })])
    let resolveOld!: (value: unknown) => void
    api.records.mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve })).mockResolvedValueOnce({ items: [{ id: 'current', task_no: 'OT-current', quantity: 2, status: 'pending', source_task_id: 'task', source_task_type: 'design' }], total: 1 })
    const view = mount(taskProps)
    await settle()
    click(view.root, '查看外协')
    await settle()
    expect(api.records).toHaveBeenLastCalledWith({ page: 1, page_size: 20, order_id: 'order', order_item_id: 'a', task_type: 'design' })
    edit(view.root, 'el-radiogroup', 'current')
    await settle()
    expect(api.records).toHaveBeenLastCalledWith(expect.objectContaining({ source_task_id: 'task', source_task_type: 'design' }))
    resolveOld({ items: [{ id: 'old', task_no: 'OT-old', quantity: 99 }], total: 1 })
    await settle()
    expect(content(view.root)).toContain('OT-current')
    expect(content(view.root)).not.toContain('OT-old')
    view.unmount()
  })
  it('供应商分页加载并过滤承接类型，失败时可重试', async () => {
    api.vendors.mockRejectedValueOnce(new Error('目录失败')).mockResolvedValueOnce({ items: [{ id: 'other', name: '仅安装', supplier_types: ['outsource'], service_types: ['installation'], is_active: true }], total: 2 })
      .mockResolvedValueOnce({ items: [{ id: 'vendor', name: '设计外协', supplier_types: ['outsource'], service_types: ['design'], is_active: true }], total: 2 })
    const view = mount(taskProps)
    await settle()
    click(view.root, '追加外协')
    await settle()
    expect(content(view.root)).toContain('目录失败')
    click(view.root, '重试供应商加载')
    await settle()
    expect(api.vendors).toHaveBeenLastCalledWith({ page: 2, page_size: 100, is_active: true })
    const supplierNames = nodes(view.root).filter(node => node.type === 'el-option').map(node => node.props.label)
    expect(supplierNames).toContain('设计外协')
    expect(supplierNames).not.toContain('仅安装')
    view.unmount()
  })
  it('记录超过一页可以翻页，切换统计范围重置到第一页', async () => {
    api.options.mockResolvedValue([item('a', { outsource_blocked: true })])
    api.records.mockResolvedValue({ items: [{ id: 'ot', task_no: 'OT-page', quantity: 1, status: 'pending' }], total: 25 })
    const view = mount(taskProps)
    await settle()
    click(view.root, '查看外协')
    await settle()
    const pagination = nodes(view.root).find(node => node.type === 'el-pagination')!
    const update = pagination.props['onUpdate:currentPage'] || pagination.props['onUpdate:current-page']
    ;(update as (page: number) => void)(2)
    await settle()
    expect(api.records).toHaveBeenLastCalledWith(expect.objectContaining({ page: 2, order_item_id: 'a' }))
    edit(view.root, 'el-radiogroup', 'current')
    await settle()
    expect(api.records).toHaveBeenLastCalledWith(expect.objectContaining({ page: 1, source_task_id: 'task' }))
    click(view.root, '管理外协')
    expect(api.push).toHaveBeenLastCalledWith({ path: '/outsource/tasks', query: { order_id: 'order', task_type: 'design', source_task_type: 'design', source_task_id: 'task', order_item_id: 'a' } })
    view.unmount()
  })
  it('切换任务时旧发送结果不会关闭新任务弹窗或刷新新任务', async () => {
    let resolveSend!: (value: unknown) => void
    api.send.mockImplementationOnce(() => new Promise(resolve => { resolveSend = resolve }))
    const changed = vi.fn()
    const props = reactive({ ...taskProps, onOutsourceChanged: changed })
    const view = mount(props)
    await settle()
    click(view.root, '追加外协')
    await settle()
    edit(view.root, 'el-select', 'vendor', node => node.props.placeholder === '选择外协商')
    click(view.root, '确认发送')
    await settle()
    expect(api.send).toHaveBeenCalledOnce()
    props.taskId = 'new-task'
    await settle()
    const summaryCalls = api.summary.mock.calls.length
    resolveSend({ id: 'old-task-send' })
    await settle()
    expect(changed).not.toHaveBeenCalled()
    expect(api.summary).toHaveBeenCalledTimes(summaryCalls)
    view.unmount()
  })
  it('记录加载失败可以重试，缺失的财务字段显示未知', async () => {
    api.records.mockRejectedValueOnce(new Error('记录失败')).mockResolvedValueOnce({ items: [{ id: 'ot', task_no: 'OT-retry', quantity: 1, status: 'cancelled' }], total: 1 })
    const view = mount(taskProps)
    await settle()
    click(view.root, '查看外协')
    await settle()
    expect(content(view.root)).toContain('记录失败')
    click(view.root, '重试记录加载')
    await settle()
    expect(content(view.root)).toContain('OT-retry')
    const definitions = nodes(view.root).filter(node => node.type === 'dd').map(content)
    expect(definitions.slice(-3)).toEqual(['-', '-', '-'])
    view.unmount()
  })
})
