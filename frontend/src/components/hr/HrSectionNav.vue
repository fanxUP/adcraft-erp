<template>
  <nav class="hr-section-nav" aria-label="人事业务导航">
    <router-link v-for="item in visible" :key="item.path" :to="item.path" :class="{ active: route.path === item.path }" :aria-current="route.path === item.path ? 'page' : undefined">{{ item.label }}</router-link>
  </nav>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
const props = defineProps<{ group: 'employee' | 'attendance' | 'salary' }>()
const route = useRoute()
const auth = useAuthStore()
const groups = {
  employee: [{ path: '/employees', label: '员工档案', permission: 'employee:read' }, { path: '/employment-histories', label: '变动履历', permission: 'employee:read' }],
  attendance: [{ path: '/attendance/records', label: '月度考勤', permission: 'attendance:read' }, { path: '/leaves', label: '请假审批', permission: 'leave:read' }, { path: '/attendance/rules', label: '考勤规则', permission: 'attendance:read' }],
  salary: [{ path: '/salaries', label: '月度工资', permission: 'salary:read' }, { path: '/salary-rules', label: '工资标准', permission: 'salary:read' }, { path: '/salary-report', label: '报表与工资条', permission: 'salary:read' }],
}
const visible = computed(() => groups[props.group].filter(item => auth.can(item.permission)))
</script>
<style scoped>
.hr-section-nav { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; border-bottom: 1px solid var(--ad-border); }
a { display: inline-flex; align-items: center; min-height: 44px; padding: 0 16px; color: var(--ad-text-secondary); text-decoration: none; border-bottom: 2px solid transparent; }
a:hover, a.active { color: var(--el-color-primary); }
a.active { border-color: var(--el-color-primary); font-weight: 600; }
a:focus-visible { outline: 2px solid var(--el-color-primary); outline-offset: -2px; }
</style>
