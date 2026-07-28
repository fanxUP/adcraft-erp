import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import * as aiApi from '@/api/aiAssistant'
import { useAiAssistantStore } from './aiAssistantStore'
import type { AiWorkflowGuidance } from '@/types/aiAssistant'

vi.mock('@/api/aiAssistant', () => ({
  getSessions: vi.fn().mockResolvedValue([]),
  getWorkflowGuidance: vi.fn(),
  confirmAction: vi.fn(),
}))

const orderId = '33333333-3333-3333-3333-333333333333'
const nextOrderId = '44444444-4444-4444-4444-444444444444'

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
    },
    completion_signal: '订单状态变为“生产中”',
    allowed_next_statuses: ['in_production'],
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
})
