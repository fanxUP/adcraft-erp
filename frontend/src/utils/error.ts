import { formatApiError, toApiRequestError } from '@/api/requestContract'

/**
 * Safely extract a human-readable error message from an unknown caught value.
 * Handles Axios errors, standard Errors, and plain strings.
 */
export function getErrorMessage(e: unknown, fallback = '操作失败'): string {
  if (typeof e === 'string') return e
  const normalized = toApiRequestError(e)
  return formatApiError(normalized, fallback)
}
