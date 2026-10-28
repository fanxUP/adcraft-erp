import { computed, onMounted, ref } from 'vue'
import type { DepartmentItem } from '@/api/departments'

const departments = ref<DepartmentItem[]>([])
export function departmentLabel(code?: string | null): string {
  return departments.value.find(d => d.code === code)?.name || code || '—'
}
export function useDepartments() {
  const departmentOptions = computed(() => departments.value.map(d => ({
    value: d.code, label: d.name + (d.is_active ? '' : '（已停用）'), is_active: d.is_active,
  })))
  onMounted(async () => {
    try { const { getDepartments } = await import('@/api/departments'); departments.value = await getDepartments({ include_inactive: true }) }
    catch { const { ElMessage } = await import('element-plus'); ElMessage.error('部门加载失败，请刷新重试') }
  })
  return { departmentOptions, departmentLabel }
}
