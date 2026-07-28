import { financeReportCapabilities } from './financeReports'
import { resourceCapabilities } from './resources'
import { salesDeliveryCapabilities } from './salesDelivery'
import { systemAiCapabilities } from './systemAi'
import type { PageCapability, PageQuickAction } from './types'

const pageCapabilities: Record<string, PageCapability> = {
  ...salesDeliveryCapabilities,
  ...financeReportCapabilities,
  ...resourceCapabilities,
  ...systemAiCapabilities,
}

export function getPageCapability(page: string): PageCapability | undefined {
  return pageCapabilities[page]
}

export function getPageQuickActions(page: string): PageQuickAction[] {
  const capability = getPageCapability(page)
  if (!capability) return []
  return capability.quickActions
    || capability.availableActions.slice(0, 3).map(label => ({ label, prompt: label }))
}

export type { PageCapability, PageQuickAction } from './types'
