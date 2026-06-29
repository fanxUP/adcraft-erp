<template>
  <div class="mobile-layout">
    <router-view />
  </div>
</template>

<style scoped>
.mobile-layout {
  min-height: 100vh;
  background: var(--ad-dark, #1a1a2e);
  max-width: 100vw;
  overflow-x: hidden;
}
</style>
