import { describe, expect, it } from 'vitest'

import {
  calcQuoteLineArea,
  calcQuoteLineSubtotal,
  dimensionToMillimeters,
  migrateLegacyQuoteDimensions,
  syncQuoteLineAreaQuantity,
} from './quoteLineCalculation'

describe('quoteLineCalculation', () => {
  const line = {
    width: 3,
    width_unit: 'm',
    height: 120,
    height_unit: 'cm',
    pieces: 2,
    quantity: 1,
    unit: '',
    use_area: true,
    unit_price: 100,
    process_fee: 20,
    installation_fee: 30,
    design_fee: 10,
    transport_fee: 40,
    other_fee: 5,
  }

  it('counts other_fee but ignores process/installation/design/transport fees', () => {
    expect(calcQuoteLineArea(line)).toBe(7.2)
    expect(calcQuoteLineSubtotal(line)).toBe(725)
  })

  it('rounds every line subtotal to cents like the backend', () => {
    expect(calcQuoteLineSubtotal({
      quantity: 3,
      unit_price: 0.335,
    })).toBe(1.01)
  })

  it('synchronizes area quantity and unit', () => {
    const changed = { ...line, quantity: 1, unit: '' }

    syncQuoteLineAreaQuantity(changed)

    expect(changed.quantity).toBe(7.2)
    expect(changed.unit).toBe('㎡')
  })

  it('converts display dimensions for the CDR pricing engine', () => {
    expect(dimensionToMillimeters(3, 'm')).toBe(3000)
    expect(dimensionToMillimeters(120, 'cm')).toBe(1200)
    expect(dimensionToMillimeters(50, 'mm')).toBe(50)
  })

  it('moves legacy length and width into width and height and drops old height', () => {
    const legacy = {
      length: 3,
      length_unit: 'm',
      width: 120,
      width_unit: 'cm',
      height: 5,
      height_unit: 'cm',
    }

    expect(migrateLegacyQuoteDimensions(legacy)).toEqual({
      ...legacy,
      length: undefined,
      length_unit: undefined,
      width: 3,
      width_unit: 'm',
      height: 120,
      height_unit: 'cm',
    })
  })
})
