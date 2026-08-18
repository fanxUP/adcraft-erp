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

const appStore = useAppStore()
onMounted(() => appStore.initTheme())
</script>
