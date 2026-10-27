import { describe, it, expect, vi, beforeEach } from 'vitest'
import * as Vue from 'vue'
import { createRenderer, h, nextTick, reactive, ssrContextKey } from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { transpileModule, ScriptTarget } from 'typescript'
import * as ElementComponents from 'element-plus/es'
import type { Component, VNode } from 'vue'
import type { TaskOrderItemOption } from '@/types/api'
import { buildTaskItemSections, filterTaskItems, taskCompletionSummary } from './taskDetailPresentation'

const api = vi.hoisted(() => ({ options: vi.fn(), assignees: vi.fn(), confirm: vi.fn(), reassign: vi.fn(), activity: vi.fn(), permission: vi.fn<(permission: string) => boolean>(() => true) }))
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
vi.mock('element-plus/es', async () => {
  const { defineComponent, h } = await import('vue')
  const stub = (name: string) => defineComponent({ name, inheritAttrs: false, setup(_, { attrs, slots }) {
    return () => h(name, attrs, [slots.header?.(), slots.title?.(), slots.default?.(), slots.footer?.()])
  } })
  return { ElLoadingDirective: {}, ...Object.fromEntries(['Button', 'Card', 'Tag', 'Input', 'Select', 'Option', 'Checkbox', 'Empty', 'Icon', 'Dialog', 'Alert', 'RadioGroup', 'RadioButton', 'Pagination']
    .map(name => [`El${name}`, stub(`el-${name.toLowerCase()}`)])) }
})
import TaskOrderItemLinkCard from '@/components/tasks/TaskOrderItemLinkCard.vue'
import TaskCompletionAttachmentDialog from '@/components/tasks/TaskCompletionAttachmentDialog.vue'
import TaskActivityCard from '@/components/tasks/TaskActivityCard.vue'
import ProgressBar from '@/components/ui/ProgressBar.vue'

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
async function settle() { await Promise.resolve(); await nextTick(); await Promise.resolve(); await nextTick() }
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
    expect(nodes(view.root).some(node => node.props.role === 'columnheader' && content(node) === '单价')).toBe(true)
    view.unmount()
  })
  it('直接展示信息仍遵守明细价格权限', async () => {
    api.permission.mockImplementation(permission => permission !== 'order_item:view_price')
    const view = mount({ taskType: 'design', taskId: 'task', orderId: 'order', currentStatus: 'pending', workflow: {}, changing: false })
    await settle()
    expect(nodes(view.root).some(node => node.props.role === 'columnheader' && ['单价', '小计'].includes(content(node)))).toBe(false)
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
  it('全部记录中也直接显示修改前后字段，无需展开', async () => {
    api.activity.mockResolvedValueOnce({ items: [{
      id: 'change', kind: 'change', title: '订单变更', actor: '管理员', occurred_at: null, detail: null,
      changes: [{ field: 'quantity', label: '数量', before: 6, after: 10, item: '展板' }],
    }], total: 1 })
    const view = mount({ taskType: 'design', taskId: 'task' }, TaskActivityCard)
    await settle()
    expect(content(view.root)).toContain('修改前')
    expect(content(view.root)).toContain('修改后')
    expect(content(view.root)).toContain('展板')
    const cells = nodes(view.root).filter(node => node.type === 'td').map(content)
    expect(cells).toEqual(['6', '10'])
    expect(nodes(view.root).some(node => node.type === 'details')).toBe(false)
    view.unmount()
  })
})
