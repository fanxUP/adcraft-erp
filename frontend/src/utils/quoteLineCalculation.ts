export interface QuoteLineCalculationFields {
  length?: number
  length_unit?: string
  width?: number
  width_unit?: string
  height?: number
  height_unit?: string
  pieces?: number
  quantity?: number
  unit?: string
  use_area?: boolean
  unit_price?: number
  process_fee?: number
  installation_fee?: number
  design_fee?: number
  transport_fee?: number
  other_fee?: number
}

function toMeters(value: number, unit?: string): number {
  if (unit === 'cm') return value / 100
  if (unit === 'mm') return value / 1000
  return value
}

export function dimensionToMillimeters(value: number, unit?: string): number {
  if (unit === 'm') return value * 1000
  if (unit === 'cm') return value * 10
  return value
}

export function calcQuoteLineArea(line: QuoteLineCalculationFields): number {
  const width = toMeters(Number(line.width || 0), line.width_unit)
  const height = toMeters(Number(line.height || 0), line.height_unit)
  const area = width * height * Number(line.pieces || 1)
  return Math.round(area * 100) / 100
}

export function calcQuoteLineSubtotal(line: QuoteLineCalculationFields): number {
  const base = line.use_area
    ? calcQuoteLineArea(line)
    : Number(line.quantity || 0)
  return base * Number(line.unit_price || 0)
    + Number(line.process_fee || 0)
    + Number(line.installation_fee || 0)
    + Number(line.design_fee || 0)
    + Number(line.transport_fee || 0)
    + Number(line.other_fee || 0)
}

export function syncQuoteLineAreaQuantity(line: QuoteLineCalculationFields): void {
  if (!line.use_area) return
  line.quantity = Math.max(0.01, calcQuoteLineArea(line))
  line.unit = '㎡'
}

export function migrateLegacyQuoteDimensions<T extends QuoteLineCalculationFields>(line: T): T {
  if (line.length !== undefined && line.length !== null) {
    return {
      ...line,
      length: undefined,
      length_unit: undefined,
      width: line.length,
      width_unit: line.length_unit,
      height: line.width,
      height_unit: line.width_unit,
    }
  }
  return {
    ...line,
    length: undefined,
    length_unit: undefined,
  }
}
