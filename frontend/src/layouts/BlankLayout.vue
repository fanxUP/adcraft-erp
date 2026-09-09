<template>
  <div class="blank-layout">
    <router-view />
  </div>
</template>

<style scoped>
.blank-layout {
  min-height: 100vh;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--ui-space-4);
  background: var(--ui-bg);
  color: var(--ui-text);
}
</style>
