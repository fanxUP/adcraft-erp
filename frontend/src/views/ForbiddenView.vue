<template>
  <main class="forbidden-page">
    <StatePanel
      state="permission"
      title="暂时无法访问"
      description="当前账号没有查看这个页面的权限。请返回工作台，或联系管理员确认角色和业务权限。"
    >
      <template #actions>
        <button type="button" class="home-button" @click="goHome">返回工作台</button>
      </template>
    </StatePanel>
  </main>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { StatePanel } from '@/components/ui'

const router = useRouter()

function goHome() {
  router.replace('/')
}
</script>

<style scoped>
.forbidden-page {
  width: min(100%, 720px);
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: var(--ui-space-6);
  background: var(--ui-bg);
  color: var(--ui-text);
}

.home-button {
  min-height: var(--ui-control-height);
  padding: 0 var(--ui-space-4);
  border: 1px solid var(--ui-brand);
  border-radius: var(--ui-radius-sm);
  background: var(--ui-brand);
  color: var(--ui-on-brand);
  cursor: pointer;
  font: inherit;
  font-weight: var(--ui-font-weight-medium);
}

.home-button:hover {
  background: var(--ui-brand-hover);
}
</style>
