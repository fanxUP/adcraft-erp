import type {
  AiPageActionGuide,
  AiWorkflowAction,
  AiWorkflowGuidance,
} from '@/types/aiAssistant'
import { isSafeWorkflowTarget } from '@/utils/workflowGuidance'

const TARGET_KEY_PATTERN = /^[a-z0-9_-]+$/

export function isSameWorkflowPath(currentPath: string, targetPath: string): boolean {
  const normalize = (path: string) => path.length > 1 ? path.replace(/\/+$/, '') : path
  return normalize(currentPath) === normalize(targetPath)
}

export function hasPageActionCompleted(
  guide: AiPageActionGuide,
  guidance: AiWorkflowGuidance,
): boolean {
  const checklist = guidance.checklist
  if (checklist && guide.target_key === 'installation-draft') {
    return (
      checklist.total_items > 0
      && checklist.completed_items === checklist.total_items
    )
  }
  if (checklist) {
    const targetByItemKey = {
      assigned_to: 'task-assignee',
      address: 'installation-address',
      scheduled_at: 'installation-schedule',
    } as const
    const matchingItem = checklist.items.find(item =>
      item.action?.target_key === guide.target_key
      || targetByItemKey[item.key] === guide.target_key,
    )
    if (matchingItem) return matchingItem.state === 'completed'
  }
  if (guide.target_status && guidance.current_status === guide.target_status) {
    return true
  }
  const nextTargetKey = guidance.next_action?.target_key
  return !guidance.next_action || Boolean(nextTargetKey && nextTargetKey !== guide.target_key)
}

export function getPageGuideContinuation(
  guide: AiPageActionGuide,
  guidance: AiWorkflowGuidance,
): AiWorkflowAction | null {
  const nextAction = guidance.next_action
  if (
    !nextAction?.target_key
    || !isSafeWorkflowTarget(nextAction.target_path)
    || isSameWorkflowPath(guide.target_path, nextAction.target_path)
  ) {
    return null
  }
  return nextAction
}

export function getPageGuideCalloutPosition(
  target: Pick<DOMRect, 'top' | 'bottom' | 'left'>,
  viewport: { width: number; height: number },
) {
  const width = Math.min(320, Math.max(0, viewport.width - 24))
  const left = Math.max(12, Math.min(target.left, viewport.width - width - 12))
  const spaceBelow = viewport.height - target.bottom
  const preferredTop = spaceBelow >= 130
    ? target.bottom + 14
    : target.top - 116
  const top = Math.max(12, Math.min(preferredTop, viewport.height - 112))
  return { left, top, width }
}

export interface LocatedPageActionTarget {
  element: HTMLElement
  revealControl: HTMLElement | null
}

export function locatePageActionTarget(
  targetKey: string,
  root: ParentNode = document,
): LocatedPageActionTarget | null {
  if (!TARGET_KEY_PATTERN.test(targetKey)) return null
  const selector = [
    `[data-ai-target="${targetKey}"]`,
    `[data-ai-targets~="${targetKey}"]`,
  ].join(',')
  const element = root.querySelector<HTMLElement>(selector)
  if (!element) return null

  const panel = element.closest<HTMLElement>('[role="tabpanel"]')
  const labelledBy = panel?.getAttribute('aria-labelledby')
  const revealControl = labelledBy
    ? root.querySelector<HTMLElement>(`[id="${labelledBy}"]`)
    : null
  return { element, revealControl }
}
