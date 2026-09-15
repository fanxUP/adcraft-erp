<template>
  <el-config-provider :locale="zhCn">
    <UpdateNotification />
    <ForceChangePasswordDialog />
    <router-view />
  </el-config-provider>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import { useAppStore } from '@/stores/app'
import UpdateNotification from '@/components/UpdateNotification.vue'
import ForceChangePasswordDialog from '@/components/ForceChangePasswordDialog.vue'
import { useBrandingStore } from '@/stores/branding'

const appStore = useAppStore()
const brandingStore = useBrandingStore()
onMounted(() => appStore.initTheme())
onMounted(() => brandingStore.fetchBranding())
</script>
