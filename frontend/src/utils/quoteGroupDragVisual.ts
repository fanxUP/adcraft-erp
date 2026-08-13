export interface QuoteGroupDragPreviewRow {
  type: 'group-header' | 'item' | 'group-total'
  label: string
  amount?: string
}

export interface QuoteGroupDragVisual {
  move(clientX: number, clientY: number): void
  showBoundary(element: HTMLElement | null, edge?: 'before' | 'after'): void
  dispose(): void
}

/** 创建挂载在 body 上的整组拖影，避免 Sortable 原生快照只呈现单个表头 tr。 */
export function createQuoteGroupDragVisual(options: {
  colorIndex: number
  rows: QuoteGroupDragPreviewRow[]
  sourceElements: HTMLElement[]
  clientX: number
  clientY: number
}): QuoteGroupDragVisual {
  document.body.classList.add('ad-group-drag')
  options.sourceElements.forEach(element => element.classList.add('ad-drag-lifted'))

  const card = document.createElement('div')
  card.className = 'ad-drag-card'
  card.style.setProperty('--ad-g', `var(--ad-group-${options.colorIndex})`)
  for (const row of options.rows) {
    const previewRow = document.createElement('div')
    previewRow.className = `ad-drag-card__row ad-drag-card__row--${row.type}`
    previewRow.textContent = row.label
    if (row.amount) {
      const amount = document.createElement('span')
      amount.textContent = row.amount
      previewRow.appendChild(amount)
    }
    card.appendChild(previewRow)
  }
  document.body.appendChild(card)

  let boundaryElement: HTMLElement | null = null
  const move = (clientX: number, clientY: number) => {
    const left = Math.min(clientX + 14, window.innerWidth - card.offsetWidth - 12)
    const top = Math.min(clientY + 14, window.innerHeight - card.offsetHeight - 12)
    card.style.transform = `translate3d(${Math.max(12, left)}px, ${Math.max(12, top)}px, 0)`
  }
  const showBoundary = (element: HTMLElement | null, edge: 'before' | 'after' = 'before') => {
    boundaryElement?.classList.remove('ad-group-drop-before', 'ad-group-drop-after')
    boundaryElement = element
    boundaryElement?.classList.add(edge === 'before' ? 'ad-group-drop-before' : 'ad-group-drop-after')
  }
  const dispose = () => {
    document.body.classList.remove('ad-group-drag')
    options.sourceElements.forEach(element => element.classList.remove('ad-drag-lifted'))
    showBoundary(null)
    card.remove()
  }

  move(options.clientX, options.clientY)
  return { move, showBoundary, dispose }
}
