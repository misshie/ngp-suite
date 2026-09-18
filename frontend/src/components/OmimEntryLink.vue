<script setup lang="ts">
  import { computed } from 'vue'
  import { useI18n } from 'vue-i18n'
  import { useStore } from '@/stores/app'
  import omimIcon from '@/assets/OMIM50-icon.png'

  const props = defineProps<{
    mondoId?: string | null
  }>()

  const store = useStore()
  const { t } = useI18n()

  const omimId = computed(() => {
    if (!props.mondoId) return null
    return store.analysisResult?.omim_ids?.[props.mondoId] || null
  })

  const href = computed(() => (omimId.value ? `https://www.omim.org/entry/${omimId.value}` : ''))
</script>

<template>
  <a
    v-if="omimId"
    class="omim-entry-link"
    :href="href"
    rel="noopener noreferrer"
    target="_blank"
    :title="t('resultsPage.mondo.omimEntry', { id: omimId })"
  >
    <img
      :alt="t('resultsPage.mondo.omimEntry', { id: omimId })"
      class="omim-entry-link__icon"
      height="14"
      :src="omimIcon"
      width="22"
    >
  </a>
</template>

<style scoped>
.omim-entry-link {
  display: inline-flex;
  vertical-align: middle;
  margin-left: 4px;
  line-height: 0;
}

.omim-entry-link__icon {
  display: block;
  width: 22px;
  height: 14px;
}
</style>
