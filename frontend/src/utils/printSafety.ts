/** Escape dynamic text before it is inserted into a print HTML document. */
export function escapePrintText(value: unknown, fallback = '-'): string {
  const text = value == null || value === '' ? fallback : String(value)
  return text.replace(/[&<>"']/g, character => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  })[character] || character)
}
