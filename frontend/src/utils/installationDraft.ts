import type { AiFormDraft } from '@/types/aiAssistant'

export interface InstallationDraftForm {
  assigned_to: string
  address: string
  scheduled_at: string
}

function normalizeScheduledAt(value: string) {
  return value.trim().replace(' ', 'T').slice(0, 19)
}

export function applyInstallationDraft(
  form: InstallationDraftForm,
  draft: AiFormDraft,
) {
  const applied: Array<keyof InstallationDraftForm> = []
  for (const field of draft.fields) {
    if (typeof field.value !== 'string' || !field.value.trim()) continue
    if (field.key === 'scheduled_at') {
      form.scheduled_at = normalizeScheduledAt(field.value)
    } else {
      form[field.key] = field.value.trim()
    }
    applied.push(field.key)
  }
  return applied
}
