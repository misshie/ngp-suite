<script setup lang="ts">
  import { computed } from 'vue'
  import { useI18n } from 'vue-i18n'
  import { useStore } from '@/stores/app'
  import nanbyoIcon from '@/assets/NanbyoData-icon.png'

  const props = defineProps<{
    mondoId?: string | null
  }>()

  const store = useStore()
  const { t } = useI18n()

  const nandoIds = computed(() => {
    if (!props.mondoId) return []
    return store.analysisResult?.nando_ids?.[props.mondoId] || []
  })

  function href (nandoId: string) {
    const params = new URLSearchParams({ lang: store.locale })
    return `https://nanbyodata.jp/disease/${nandoId}?${params.toString()}`
  }
</script>

<template>
  <template v-if="nandoIds.length > 0">
    <a
      v-for="nandoId in nandoIds"
      :key="nandoId"
      class="nanbyo-data-link"
      :href="href(nandoId)"
      rel="noopener noreferrer"
      target="_blank"
      :title="t('resultsPage.mondo.nanbyoData', { id: nandoId })"
    >
      <img
        :alt="t('resultsPage.mondo.nanbyoData', { id: nandoId })"
        class="nanbyo-data-link__icon"
        height="14"
        :src="nanbyoIcon"
        width="21"
      >
    </a>
  </template>
</template>

<style scoped>
.nanbyo-data-link {
  display: inline-flex;
  vertical-align: middle;
  margin-left: 4px;
  line-height: 0;
}

.nanbyo-data-link__icon {
  display: block;
  width: 21px;
  height: 14px;
}
</style>
