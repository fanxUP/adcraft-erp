import type {
  AiPageContext,
  AiToolCallResult,
  AiWorkflowAction,
  AiWorkflowAlert,
  AiWorkflowGuidance,
  AiWorkflowProgress,
  AiWorkflowProgressStep,
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
    ...(typeof value.target_key === 'string'
      ? { target_key: value.target_key }
      : {}),
  }
}

const WORKFLOW_STEP_STATES = new Set(['completed', 'current', 'pending', 'blocked'])
const ALERT_SEVERITIES = new Set(['info', 'warning', 'danger'])

function parseProgressStep(value: unknown): AiWorkflowProgressStep | null {
  if (!isRecord(value)) return null
  if (
    typeof value.key !== 'string'
    || typeof value.label !== 'string'
    || typeof value.detail !== 'string'
    || typeof value.state !== 'string'
    || !WORKFLOW_STEP_STATES.has(value.state)
  ) {
    return null
  }
  return {
    key: value.key,
    label: value.label,
    state: value.state as AiWorkflowProgressStep['state'],
    detail: value.detail,
  }
}

function parseProgress(value: unknown): AiWorkflowProgress | undefined {
  if (!isRecord(value) || !Array.isArray(value.steps)) return undefined
  const steps = value.steps.map(parseProgressStep)
  if (
    steps.some(step => !step)
    || typeof value.completed_steps !== 'number'
    || typeof value.total_steps !== 'number'
    || typeof value.percent !== 'number'
    || typeof value.current_stage_key !== 'string'
  ) {
    return undefined
  }
  return {
    completed_steps: value.completed_steps,
    total_steps: value.total_steps,
    percent: value.percent,
    current_stage_key: value.current_stage_key,
    steps: steps as AiWorkflowProgressStep[],
  }
}

function parseAlerts(value: unknown): AiWorkflowAlert[] {
  if (!Array.isArray(value)) return []
  const alerts: AiWorkflowAlert[] = []
  for (const item of value) {
    if (
      !isRecord(item)
      || typeof item.code !== 'string'
      || typeof item.severity !== 'string'
      || !ALERT_SEVERITIES.has(item.severity)
      || typeof item.title !== 'string'
      || typeof item.detail !== 'string'
    ) {
      continue
    }
    alerts.push({
      code: item.code,
      severity: item.severity as AiWorkflowAlert['severity'],
      title: item.title,
      detail: item.detail,
    })
  }
  return alerts
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
  const progress = parseProgress(value.progress)
  return {
    business_type: value.business_type as string,
    business_id: value.business_id as string,
    current_status: value.current_status as string,
    current_step: value.current_step as string,
    blockers: value.blockers as string[],
    next_action: nextAction,
    completion_signal: value.completion_signal as string,
    allowed_next_statuses: value.allowed_next_statuses as string[],
    ...(progress ? { progress } : {}),
    alerts: parseAlerts(value.alerts),
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
