import type { AiPageActionGuide } from '@/types/aiAssistant'
import {
  isSafeWorkflowTarget,
  parseWorkflowDraft,
} from '@/utils/workflowGuidance'

const STORAGE_PREFIX = 'adcraft-ai-page-guide:v1:'
const DEFAULT_TTL_MS = 24 * 60 * 60 * 1_000
const TARGET_KEY_PATTERN = /^[a-z0-9_-]+$/

interface PersistedPageGuide {
  version: 1
  expires_at: number
  guide: AiPageActionGuide
}

function storageKey(ownerId: string) {
  return `${STORAGE_PREFIX}${encodeURIComponent(ownerId)}`
}

function safeRemove(storage: Storage, key: string) {
  try {
    storage.removeItem(key)
  } catch {
    // Persistence is optional and must never block the active guidance.
  }
}

function parseGuide(value: unknown): AiPageActionGuide | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  const guide = value as Record<string, unknown>
  if (
    typeof guide.label !== 'string'
    || typeof guide.target_path !== 'string'
    || typeof guide.target_key !== 'string'
    || !guide.label.trim()
    || !isSafeWorkflowTarget(guide.target_path)
    || !TARGET_KEY_PATTERN.test(guide.target_key)
  ) {
    return null
  }
  const draft = parseWorkflowDraft(guide.draft)
  return {
    label: guide.label,
    target_path: guide.target_path,
    target_key: guide.target_key,
    ...(typeof guide.target_status === 'string'
      ? { target_status: guide.target_status }
      : {}),
    ...(draft ? { draft } : {}),
  }
}

export function persistPageGuide(
  storage: Storage,
  ownerId: string,
  guide: AiPageActionGuide,
  now = Date.now(),
  ttlMs = DEFAULT_TTL_MS,
) {
  const payload: PersistedPageGuide = {
    version: 1,
    expires_at: now + ttlMs,
    guide,
  }
  try {
    storage.setItem(storageKey(ownerId), JSON.stringify(payload))
  } catch {
    // Storage can be disabled by browser privacy settings or quota limits.
  }
}

export function loadPersistedPageGuide(
  storage: Storage,
  ownerId: string,
  now = Date.now(),
): AiPageActionGuide | null {
  const key = storageKey(ownerId)
  try {
    const raw = storage.getItem(key)
    if (!raw) return null
    const payload = JSON.parse(raw) as Partial<PersistedPageGuide>
    const guide = parseGuide(payload.guide)
    if (payload.version !== 1 || !guide || !payload.expires_at || payload.expires_at <= now) {
      safeRemove(storage, key)
      return null
    }
    return guide
  } catch {
    safeRemove(storage, key)
    return null
  }
}

export function clearPersistedPageGuide(storage: Storage, ownerId: string) {
  safeRemove(storage, storageKey(ownerId))
}
