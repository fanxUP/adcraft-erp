<template>
  <el-menu :default-active="activePath" router :collapse="collapsed">
    <SidebarNavItem
      v-for="(item, index) in visibleItems"
      :key="item.path || index"
      :item="item"
      :group-index="`nav-${index}`"
    />
  </el-menu>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import SidebarNavItem from './SidebarNavItem.vue'
import { filterNavigation, navigationItems } from '@/config/navigation'

const props = defineProps<{
  activePath: string
  collapsed: boolean
  roles: string[]
}>()

const visibleItems = computed(() =>
  filterNavigation(navigationItems, props.roles),
)
</script>
