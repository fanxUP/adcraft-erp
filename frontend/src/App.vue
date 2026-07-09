<template>
  <UpdateNotification />
  <router-view />
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useAppStore } from '@/stores/app'
import UpdateNotification from '@/components/UpdateNotification.vue'

const appStore = useAppStore()
onMounted(() => appStore.initTheme())
</script>
