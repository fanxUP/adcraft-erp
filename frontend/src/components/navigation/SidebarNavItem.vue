<template>
  <el-sub-menu v-if="item.children?.length" :index="item.path || groupIndex">
    <template #title>
      <el-icon v-if="iconComponent"><component :is="iconComponent" /></el-icon>
      <span>{{ item.label }}</span>
    </template>
    <SidebarNavItem
      v-for="(child, index) in item.children"
      :key="child.path || `${groupIndex}-${index}`"
      :item="child"
      :group-index="`${groupIndex}-${index}`"
    />
  </el-sub-menu>
  <el-menu-item v-else-if="item.path" :index="item.path">
    <el-icon v-if="iconComponent"><component :is="iconComponent" /></el-icon>
    <span>{{ item.label }}</span>
  </el-menu-item>
</template>

<script setup lang="ts">
import { computed, type Component } from "vue"
import {
  Avatar,
  Clock,
  DataAnalysis,
  List,
  Money,
  Platform,
  Tools,
  TrendCharts,
  User,
  UserFilled,
  Van,
} from "@element-plus/icons-vue"
import type { NavigationItem } from "@/config/navigation"

defineOptions({ name: "SidebarNavItem" })

const props = defineProps<{
  item: NavigationItem
  groupIndex: string
}>()

const icons: Record<string, Component> = {
  Avatar,
  Clock,
  DataAnalysis,
  List,
  Money,
  Platform,
  Tools,
  TrendCharts,
  User,
  UserFilled,
  Van,
}

const iconComponent = computed(() => {
  if (!props.item.icon) return null
  return icons[props.item.icon] || null
})
</script>
