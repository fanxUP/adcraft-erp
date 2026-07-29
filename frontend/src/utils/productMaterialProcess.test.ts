import { describe, expect, it } from 'vitest'

import { applyProductMaterialProcess } from './productMaterialProcess'

describe('applyProductMaterialProcess', () => {
  it('uses one master record and clears legacy material/process ids', () => {
    const result = applyProductMaterialProcess(
      {
        product_id: undefined,
        material_id: 'legacy-material',
        process_id: 'legacy-process',
        material_process: '',
        unit: '',
        unit_price: 0,
      },
      {
        id: 'pmp-1',
        name: '亚克力UV打印',
        unit: '㎡',
        default_price: 280,
      },
    )

    expect(result).toEqual({
      product_id: 'pmp-1',
      material_id: undefined,
      process_id: undefined,
      material_process: '亚克力UV打印',
      unit: '㎡',
      unit_price: 280,
    })
  })

  it('keeps the current unit price when the master price is zero', () => {
    const result = applyProductMaterialProcess(
      {
        product_id: undefined,
        material_id: undefined,
        process_id: undefined,
        material_process: '',
        unit: '项',
        unit_price: 99,
      },
      {
        id: 'pmp-2',
        name: '现场安装服务',
        unit: '项',
        default_price: 0,
      },
    )

    expect(result.unit_price).toBe(99)
  })
})
