import { describe, expect, it } from 'vitest'
import { canUndertakeOutsource, choiceLabels, supplierTypeOptions } from './supplierCapabilities'
import type { VendorResponse } from '@/types/api'

describe('supplier capabilities', () => {
  const vendor: VendorResponse = {
    id: 'shared', vendor_no: 'V001', name: '多业务公司', is_active: true,
    supplier_types: ['material', 'outsource'], service_types: ['production', 'installation'],
  }
  it('allows a material supplier to undertake its declared external work', () => {
    expect(canUndertakeOutsource(vendor, 'production')).toBe(true)
    expect(canUndertakeOutsource(vendor, 'installation')).toBe(true)
    expect(canUndertakeOutsource(vendor, 'design')).toBe(false)
    expect(choiceLabels(vendor.supplier_types!, supplierTypeOptions)).toBe('材料供应、外协服务')
  })
  it('excludes inactive vendors and vendors that no longer undertake external work', () => {
    expect(canUndertakeOutsource({ ...vendor, is_active: false }, 'production')).toBe(false)
    expect(canUndertakeOutsource({ ...vendor, supplier_types: ['material'] }, 'production')).toBe(false)
  })
})
