<template>
  <img
    v-if="branding.logoUrl && !imageFailed"
    class="brand-logo__image"
    :style="logoStyle"
    :src="branding.logoUrl"
    :alt="branding.appName"
    @error="imageFailed = true"
  />
  <span
    v-else
    class="brand-logo__mark"
    :style="logoStyle"
    aria-hidden="true"
  >{{ branding.fallbackMark }}</span>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useBrandingStore } from '@/stores/branding'

const props = withDefaults(defineProps<{ size?: number }>(), { size: 32 })
const branding = useBrandingStore()
const imageFailed = ref(false)

const logoStyle = computed(() => ({
  width: `${props.size}px`,
  height: `${props.size}px`,
}))

watch(() => branding.logoUrl, () => {
  imageFailed.value = false
})
</script>

<style scoped>
.brand-logo__image,
.brand-logo__mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  flex: 0 0 auto;
}

.brand-logo__image {
  object-fit: contain;
  background: var(--ui-surface, #fff);
  border: 1px solid var(--ui-border, #e5e7eb);
}

.brand-logo__mark {
  background: linear-gradient(135deg, var(--ui-brand, #2563eb), var(--ui-brand-hover, #1d4ed8));
  color: #fff;
  font-size: 18px;
  font-weight: 800;
}
</style>
