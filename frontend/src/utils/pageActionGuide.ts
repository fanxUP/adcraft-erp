import type { AiPageActionGuide, AiWorkflowGuidance } from '@/types/aiAssistant'

const TARGET_KEY_PATTERN = /^[a-z0-9_-]+$/

export function isSameWorkflowPath(currentPath: string, targetPath: string): boolean {
  const normalize = (path: string) => path.length > 1 ? path.replace(/\/+$/, '') : path
  return normalize(currentPath) === normalize(targetPath)
}

export function hasPageActionCompleted(
  guide: AiPageActionGuide,
  guidance: AiWorkflowGuidance,
): boolean {
  if (guide.target_status && guidance.current_status === guide.target_status) {
    return true
  }
  const nextTargetKey = guidance.next_action?.target_key
  return !guidance.next_action || Boolean(nextTargetKey && nextTargetKey !== guide.target_key)
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
