<script setup lang="ts">
  import type { MondoTerm } from '@/stores/app'
  import { computed } from 'vue'
  import { useStore } from '@/stores/app'
  import { mondoLabel } from '@/utils/mondoLabel'

  const props = defineProps<{ terms?: MondoTerm[], ids?: string[] }>()
  const store = useStore()

  const items = computed(() => {
    if (props.terms?.length) {
      return props.terms.map(term => ({
        id: term.id,
        label: mondoLabel(term, store.locale),
      }))
    }
    return (props.ids || []).map(id => ({ id, label: '' }))
  })
</script>

<template>
  <div v-if="items.length > 0" class="mondo-term-list">
    <div v-for="term in items" :key="term.id">
      <a
        class="text-decoration-none"
        :href="`https://monarchinitiative.org/${term.id}`"
        rel="noopener noreferrer"
        target="_blank"
      >{{ term.id }}</a>
      <span v-if="term.label" class="ml-1">{{ term.label }}</span>
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
