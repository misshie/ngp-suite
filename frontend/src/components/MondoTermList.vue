<script setup lang="ts">
  import type { MondoTerm } from '@/stores/app'

  defineProps<{ terms?: MondoTerm[] }>()
</script>

<template>
  <div v-if="terms?.length" class="mondo-term-list">
    <div v-for="term in terms" :key="term.id">
      <a
        class="text-decoration-none"
        :href="`https://monarchinitiative.org/${term.id}`"
        rel="noopener noreferrer"
        target="_blank"
      >{{ term.id }}</a>
      <span v-if="term.name" class="ml-1">{{ term.name }}</span>
    </div>
  </div>
  <span v-else>-</span>
</template>

<style scoped>
.mondo-term-list {
  white-space: nowrap;
  line-height: 1.4;
  padding-block: 2px;
}
</style>
