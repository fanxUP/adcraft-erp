/**
 * Safely extract a human-readable error message from an unknown caught value.
 * Handles Axios errors, standard Errors, and plain strings.
 */
export function getErrorMessage(e: unknown, fallback = '操作失败'): string {
  if (typeof e === 'string') return e
  // Prefer backend error message from Axios response body
  const axiosErr = e as { response?: { data?: { message?: string } } }
  if (axiosErr.response?.data?.message) return axiosErr.response.data.message
  if (e instanceof Error) return e.message
  return fallback
}
