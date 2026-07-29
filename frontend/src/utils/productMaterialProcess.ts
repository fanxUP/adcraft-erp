export interface ProductMaterialProcessSelection {
  id: string
  name: string
  unit: string
  default_price: number
}

export interface QuoteProductMaterialProcessFields {
  product_id?: string
  material_id?: string
  process_id?: string
  material_process?: string
  unit?: string
  unit_price: number
}

export function applyProductMaterialProcess(
  current: QuoteProductMaterialProcessFields,
  selected: ProductMaterialProcessSelection,
): QuoteProductMaterialProcessFields {
  return {
    ...current,
    product_id: selected.id,
    material_id: undefined,
    process_id: undefined,
    material_process: selected.name,
    unit: selected.unit || current.unit,
    unit_price: selected.default_price > 0 ? selected.default_price : current.unit_price,
  }
}
