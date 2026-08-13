<template>
  <el-dialog
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    title="新建产品/材质/工艺"
    width="min(560px, 92vw)"
    :close-on-click-modal="false"
  >
    <el-form :model="form" label-width="80px">
      <el-form-item label="产品">
        <el-input v-model="form.name" type="textarea" :rows="3" placeholder="如：标识牌" />
      </el-form-item>
      <el-form-item label="材质">
        <el-input v-model="form.material_name" type="textarea" :rows="3" placeholder="如：亚克力" />
      </el-form-item>
      <el-form-item label="工艺">
        <el-input v-model="form.process_name" type="textarea" :rows="3" placeholder="如：UV打印" />
      </el-form-item>
      <el-form-item label="单位">
        <el-select v-model="form.unit" style="width: 100%">
          <el-option label="项" value="项" />
          <el-option label="㎡" value="㎡" />
          <el-option label="米" value="米" />
          <el-option label="个" value="个" />
          <el-option label="套" value="套" />
          <el-option label="批" value="批" />
        </el-select>
      </el-form-item>
      <el-form-item label="计价方式">
        <el-select v-model="form.pricing_method" style="width: 100%">
          <el-option label="按面积" value="area" />
          <el-option label="按数量" value="quantity" />
          <el-option label="按长度" value="length" />
          <el-option label="按字数" value="word_count" />
        </el-select>
      </el-form-item>
      <el-form-item label="默认单价">
        <el-input-number v-model="form.default_price" :precision="2" :min="0" style="width: 100%" />
      </el-form-item>
      <el-form-item label="最低收费">
        <el-input-number v-model="form.min_charge" :precision="2" :min="0" style="width: 100%" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="form.remark" type="textarea" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">取消</el-button>
      <el-button type="danger" :loading="saving" @click="handleSave">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { createProduct } from '@/api/products'
import type { ProductResponse } from '@/types/api'

defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  created: [product: ProductResponse]
}>()

const saving = ref(false)
const form = reactive({
  name: '',
  material_name: '',
  process_name: '',
  unit: '项',
  pricing_method: 'quantity',
  default_price: 0,
  min_charge: 0,
  remark: '',
})

async function handleSave() {
  const filled = [form.name.trim(), form.material_name.trim(), form.process_name.trim()].filter(Boolean)
  if (filled.length === 0) {
    ElMessage.warning('请至少填写产品、材质、工艺中的一项')
    return
  }
  saving.value = true
  try {
    const product = await createProduct({ ...form })
    ElMessage.success('创建成功')
    emit('update:modelValue', false)
    emit('created', product)
    // Reset form
    Object.assign(form, { name: '', material_name: '', process_name: '', unit: '项', pricing_method: 'quantity', default_price: 0, min_charge: 0, remark: '' })
  } catch (e: unknown) {
    const err = e as { response?: { data?: { message?: string } } }
    const msg = e instanceof Error ? e.message : err?.response?.data?.message || '创建失败'
    ElMessage.error(msg)
  } finally {
    saving.value = false
  }
}
</script>
