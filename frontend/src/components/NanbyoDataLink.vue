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

  const nandoId = computed(() => {
    if (!props.mondoId) return null
    return store.analysisResult?.nando_ids?.[props.mondoId] || null
  })

  const href = computed(() => {
    if (!nandoId.value) return ''
    const params = new URLSearchParams({ lang: store.locale })
    return `https://nanbyodata.jp/disease/${nandoId.value}?${params.toString()}`
  })
</script>

<template>
  <a
    v-if="nandoId"
    class="nanbyo-data-link"
    :href="href"
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
