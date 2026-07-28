export interface PageQuickAction {
  label: string
  prompt: string
}

export interface PageCapability {
  title: string
  purpose: string
  workflowStage?: string
  availableActions: string[]
  quickActions?: PageQuickAction[]
}

export type PageCapabilityMap = Record<string, PageCapability>
