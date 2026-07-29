import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import * as aiApi from '@/api/aiAssistant'
import { useAiAssistantStore } from './aiAssistantStore'
import type {
  AiWorkflowAction,
  AiWorkflowGuidance,
} from '@/types/aiAssistant'

vi.mock('@/api/aiAssistant', () => ({
  getSessions: vi.fn().mockResolvedValue([]),
  getWorkflowGuidance: vi.fn(),
  confirmAction: vi.fn(),
}))

const orderId = '33333333-3333-3333-3333-333333333333'
const nextOrderId = '44444444-4444-4444-4444-444444444444'

class MemoryStorage implements Storage {
  private values = new Map<string, string>()
  get length() { return this.values.size }
  clear() { this.values.clear() }
  getItem(key: string) { return this.values.get(key) ?? null }
  key(index: number) { return [...this.values.keys()][index] ?? null }
  removeItem(key: string) { this.values.delete(key) }
  setItem(key: string, value: string) { this.values.set(key, value) }
}

function guidance(businessId = orderId): AiWorkflowGuidance {
  return {
    business_type: 'order',
    business_id: businessId,
    current_status: 'designing',
    current_step: '设计阶段',
    blockers: [],
    next_action: {
      label: '进入生产阶段',
      target_page: '订单详情',
      target_path: `/orders/${businessId}`,
      target_status: 'in_production',
      target_key: 'order-status-in_production',
    },
    completion_signal: '订单状态变为“生产中”',
    allowed_next_statuses: ['in_production'],
    alerts: [],
  }
}

describe('AI assistant proactive workflow guidance', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.mocked(aiApi.getSessions).mockResolvedValue([])
  })

  it('automatically checks the current business state when the drawer opens', async () => {
    vi.mocked(aiApi.getWorkflowGuidance).mockResolvedValue(guidance())
    const store = useAiAssistantStore()
    store.resetPageContext({ business_type: 'order', business_id: orderId })

    store.openDrawer()

    await vi.waitFor(() => {
      expect(aiApi.getWorkflowGuidance).toHaveBeenCalledWith({
        business_type: 'order',
        business_id: orderId,
      })
      expect(store.activeGuidance?.business_id).toBe(orderId)
    })
  })

  it('discards an old response after the user navigates to another record', async () => {
    let resolveFirst!: (value: AiWorkflowGuidance) => void
    let resolveSecond!: (value: AiWorkflowGuidance) => void
    vi.mocked(aiApi.getWorkflowGuidance)
      .mockReturnValueOnce(new Promise(resolve => { resolveFirst = resolve }))
      .mockReturnValueOnce(new Promise(resolve => { resolveSecond = resolve }))
    const store = useAiAssistantStore()
    store.resetPageContext({ business_type: 'order', business_id: orderId })
    store.openDrawer()
    store.resetPageContext({ business_type: 'order', business_id: nextOrderId })

    resolveFirst(guidance(orderId))
    await Promise.resolve()
    expect(store.activeGuidance).toBeNull()

    resolveSecond(guidance(nextOrderId))
    await vi.waitFor(() => {
      expect(store.activeGuidance?.business_id).toBe(nextOrderId)
    })
  })

  it('rechecks the next step after a confirmed AI operation', async () => {
    vi.mocked(aiApi.getWorkflowGuidance)
      .mockResolvedValueOnce(guidance())
      .mockResolvedValueOnce({
        ...guidance(),
        current_status: 'in_production',
        current_step: '生产阶段',
      })
    vi.mocked(aiApi.confirmAction).mockResolvedValue({
      status: 'success',
      result: { status: 'in_production' },
    })
    const store = useAiAssistantStore()
    store.resetPageContext({ business_type: 'order', business_id: orderId })
    store.openDrawer()
    await vi.waitFor(() => expect(store.activeGuidance).not.toBeNull())

    await store.confirmPendingAction('action-id')

    expect(aiApi.getWorkflowGuidance).toHaveBeenCalledTimes(2)
    expect(store.activeGuidance?.current_step).toBe('生产阶段')
  })

  it('closes the drawer and marks a page action complete after business progress', async () => {
    vi.mocked(aiApi.getWorkflowGuidance)
      .mockResolvedValueOnce(guidance())
      .mockResolvedValueOnce({
        ...guidance(),
        current_status: 'in_production',
        next_action: {
          label: '开始制作',
          target_page: '制作任务详情',
          target_path: '/production-tasks/22222222-2222-2222-2222-222222222222',
          target_key: 'task-status-in_progress',
        },
      })
    const store = useAiAssistantStore()
    store.resetPageContext({ business_type: 'order', business_id: orderId })
    store.openDrawer()
    await vi.waitFor(() => expect(store.activeGuidance).not.toBeNull())

    store.startPageActionGuide(store.activeGuidance!.next_action!)
    expect(store.visible).toBe(false)
    expect(store.pageGuideState).toBe('locating')

    await store.notifyBusinessMutation()

    expect(store.pageGuideState).toBe('completed')
  })

  it('queues a cross-page continuation after a terminal task action', async () => {
    const taskId = '22222222-2222-2222-2222-222222222222'
    const taskGuidance: AiWorkflowGuidance = {
      business_type: 'design_task',
      business_id: taskId,
      current_status: 'pending_review',
      current_step: '设计阶段',
      blockers: [],
      next_action: {
        label: '确认设计稿',
        target_page: '设计任务详情',
        target_path: `/design-tasks/${taskId}`,
        target_status: 'confirmed',
        target_key: 'task-status-confirmed',
      },
      completion_signal: '设计任务状态变为“已确认”',
      allowed_next_statuses: ['confirmed'],
      alerts: [],
    }
    const parentOrderAction = {
      label: '进入生产阶段',
      target_page: '订单详情',
      target_path: `/orders/${orderId}`,
      target_status: 'in_production',
      target_key: 'order-status-in_production',
    }
    vi.mocked(aiApi.getWorkflowGuidance)
      .mockResolvedValueOnce(taskGuidance)
      .mockResolvedValueOnce({
        ...taskGuidance,
        current_status: 'confirmed',
        next_action: parentOrderAction,
      })
    const store = useAiAssistantStore()
    store.resetPageContext({ business_type: 'design_task', business_id: taskId })
    store.openDrawer()
    await vi.waitFor(() => expect(store.activeGuidance).not.toBeNull())
    store.startPageActionGuide(store.activeGuidance!.next_action!)

    await store.notifyBusinessMutation()

    expect(store.pageGuideState).toBe('completed')
    expect(store.pageGuideContinuation).toEqual(parentOrderAction)
  })

  it('restores an unfinished page guide after the store is recreated', () => {
    const storage = new MemoryStorage()
    const firstStore = useAiAssistantStore()
    firstStore.restorePageActionGuide('user-a', storage)
    firstStore.startPageActionGuide(guidance().next_action!)

    setActivePinia(createPinia())
    const restoredStore = useAiAssistantStore()

    expect(restoredStore.restorePageActionGuide('user-a', storage)).toBe(true)
    expect(restoredStore.pageGuideState).toBe('restored')
    expect(restoredStore.activePageGuide?.target_key).toBe('order-status-in_production')
    expect(restoredStore.resumePageActionGuide()).toBe(`/orders/${orderId}`)
    expect(restoredStore.pageGuideState).toBe('locating')
  })

  it('keeps a reviewable form draft when starting a page guide', () => {
    const store = useAiAssistantStore()
    const action: AiWorkflowAction = {
      label: '预览安装准备草稿',
      target_page: '安装任务详情',
      target_path: '/installation-tasks/44444444-4444-4444-4444-444444444444',
      target_key: 'installation-draft',
      draft: {
        kind: 'installation_task_update',
        title: '安装准备信息草稿',
        fields: [
          {
            key: 'address',
            label: '安装地址',
            value: '上海市静安区测试路 88 号',
            source: 'order',
            hint: '来自订单安装地址，请现场确认',
          },
        ],
      },
    }

    store.startPageActionGuide(action)

    expect(store.activePageGuide).toMatchObject({
      target_key: 'installation-draft',
      draft: {
        kind: 'installation_task_update',
        fields: [{ key: 'address' }],
      },
    })
  })

  it('does not carry an in-memory guide into another user account', () => {
    const storage = new MemoryStorage()
    const store = useAiAssistantStore()
    store.restorePageActionGuide('user-a', storage)
    store.startPageActionGuide(guidance().next_action!)

    expect(store.restorePageActionGuide('user-b', storage)).toBe(false)
    expect(store.activePageGuide).toBeNull()
    expect(store.pageGuideState).toBe('idle')
  })

  it('persists the cross-page continuation as the next guide to resume', async () => {
    const storage = new MemoryStorage()
    const taskId = '22222222-2222-2222-2222-222222222222'
    const taskGuidance: AiWorkflowGuidance = {
      business_type: 'design_task',
      business_id: taskId,
      current_status: 'pending_review',
      current_step: '设计阶段',
      blockers: [],
      next_action: {
        label: '确认设计稿',
        target_page: '设计任务详情',
        target_path: `/design-tasks/${taskId}`,
        target_status: 'confirmed',
        target_key: 'task-status-confirmed',
      },
      completion_signal: '设计任务状态变为“已确认”',
      allowed_next_statuses: ['confirmed'],
      alerts: [],
    }
    const parentOrderAction = guidance().next_action!
    vi.mocked(aiApi.getWorkflowGuidance)
      .mockResolvedValueOnce(taskGuidance)
      .mockResolvedValueOnce({
        ...taskGuidance,
        current_status: 'confirmed',
        next_action: parentOrderAction,
      })
    const store = useAiAssistantStore()
    store.restorePageActionGuide('user-a', storage)
    store.resetPageContext({ business_type: 'design_task', business_id: taskId })
    store.openDrawer()
    await vi.waitFor(() => expect(store.activeGuidance).not.toBeNull())
    store.startPageActionGuide(store.activeGuidance!.next_action!)

    await store.notifyBusinessMutation()
    setActivePinia(createPinia())
    const restoredStore = useAiAssistantStore()
    restoredStore.restorePageActionGuide('user-a', storage)

    expect(restoredStore.activePageGuide?.target_key).toBe('order-status-in_production')
    expect(restoredStore.activePageGuide?.target_path).toBe(`/orders/${orderId}`)
  })

  it('verifies and completes a persisted order action from a finance page', async () => {
    vi.mocked(aiApi.getWorkflowGuidance).mockResolvedValue({
      ...guidance(),
      current_status: 'completed',
      current_step: '流程已完成',
      next_action: null,
      completion_signal: '订单已完工且款项已结清',
      allowed_next_statuses: [],
    })
    const store = useAiAssistantStore()
    store.startPageActionGuide({
      label: '登记该订单收款',
      target_page: '应收管理',
      target_path: `/receivables?order_id=${orderId}`,
      target_key: 'receivable-register-payment',
    })
    store.resetPageContext({ business_type: 'finance' })

    await store.requestWorkflowGuidance('order', orderId, true)

    expect(store.pageGuideState).toBe('completed')
    expect(store.activeGuidance).toBeNull()
  })
})
