import type {
  AiPageContext,
  AiToolCallResult,
  AiWorkflowAction,
  AiWorkflowGuidance,
} from '@/types/aiAssistant'

const UUID_SEGMENT = '[0-9a-fA-F-]{36}'
const GUIDED_BUSINESS_TYPES = new Set([
  'quote',
  'order',
  'design_task',
  'production_task',
  'installation_task',
  'acceptance',
])
const SAFE_TARGETS = [
  /^\/orders$/,
  new RegExp(`^/orders/${UUID_SEGMENT}$`),
  /^\/quotes$/,
  new RegExp(`^/quotes/${UUID_SEGMENT}/edit$`),
  /^\/design-tasks$/,
  new RegExp(`^/design-tasks/${UUID_SEGMENT}$`),
  /^\/production-tasks$/,
  new RegExp(`^/production-tasks/${UUID_SEGMENT}$`),
  /^\/installation-tasks$/,
  new RegExp(`^/installation-tasks/${UUID_SEGMENT}$`),
  /^\/acceptances$/,
  new RegExp(`^/acceptances/${UUID_SEGMENT}$`),
  /^\/receivables$/,
]

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function parseAction(value: unknown): AiWorkflowAction | null {
  if (value === null) return null
  if (!isRecord(value)) return null
  if (
    typeof value.label !== 'string'
    || typeof value.target_page !== 'string'
    || typeof value.target_path !== 'string'
  ) {
    return null
  }
  return {
    label: value.label,
    target_page: value.target_page,
    target_path: value.target_path,
    ...(typeof value.target_status === 'string'
      ? { target_status: value.target_status }
      : {}),
  }
}

export function parseWorkflowGuidance(value: unknown): AiWorkflowGuidance | null {
  if (!isRecord(value)) return null
  const requiredStrings = [
    'business_type',
    'business_id',
    'current_status',
    'current_step',
    'completion_signal',
  ] as const
  if (requiredStrings.some(key => typeof value[key] !== 'string')) return null
  if (!Array.isArray(value.blockers) || !value.blockers.every(item => typeof item === 'string')) return null
  if (
    !Array.isArray(value.allowed_next_statuses)
    || !value.allowed_next_statuses.every(item => typeof item === 'string')
  ) return null

  const nextAction = parseAction(value.next_action)
  if (value.next_action !== null && !nextAction) return null
  return {
    business_type: value.business_type as string,
    business_id: value.business_id as string,
    current_status: value.current_status as string,
    current_step: value.current_step as string,
    blockers: value.blockers as string[],
    next_action: nextAction,
    completion_signal: value.completion_signal as string,
    allowed_next_statuses: value.allowed_next_statuses as string[],
  }
}

export function extractWorkflowGuidance(
  toolResults: AiToolCallResult[],
): AiWorkflowGuidance | null {
  const result = [...toolResults].reverse().find(item =>
    item.tool_name === 'get_workflow_guidance' && item.status === 'success',
  )
  return parseWorkflowGuidance(result?.result)
}

export function isSafeWorkflowTarget(path: string): boolean {
  return SAFE_TARGETS.some(pattern => pattern.test(path))
}

export function getGuidanceContextKey(
  context: Pick<AiPageContext, 'business_type' | 'business_id'>,
): string | null {
  const businessType = context.business_type
  const businessId = context.business_id
  if (!businessType || !businessId || !GUIDED_BUSINESS_TYPES.has(businessType)) {
    return null
  }
  return `${businessType}:${businessId}`
}

export function matchesGuidanceContext(
  guidance: unknown,
  context: Pick<AiPageContext, 'business_type' | 'business_id'>,
): boolean {
  if (!isRecord(guidance)) return false
  const guidanceKey = getGuidanceContextKey({
    business_type: typeof guidance.business_type === 'string'
      ? guidance.business_type
      : undefined,
    business_id: typeof guidance.business_id === 'string'
      ? guidance.business_id
      : undefined,
  })
  return Boolean(guidanceKey && guidanceKey === getGuidanceContextKey(context))
}
