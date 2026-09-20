<script setup lang="ts">
  import { computed } from 'vue'
  import { useI18n } from 'vue-i18n'
  import { useStore } from '@/stores/app'
  import pcfIcon from '@/assets/PCFpanelsearch-icon.svg'

  const props = defineProps<{
    mondoId?: string | null
  }>()

  const store = useStore()
  const { t } = useI18n()

  const isMondoId = computed(() => /^MONDO:\d+$/.test(props.mondoId || ''))

  const href = computed(() => {
    if (!isMondoId.value || !props.mondoId) return ''
    const params = new URLSearchParams({
      lang: store.locale,
      panel_id: props.mondoId,
    })
    return `https://pubcasefinder.dbcls.jp/panelsearch_panel_detail?${params.toString()}`
  })
</script>

<template>
  <a
    v-if="isMondoId"
    class="pcf-panel-link"
    :href="href"
    rel="noopener noreferrer"
    target="_blank"
    :title="t('resultsPage.mondo.panelSearch')"
  >
    <img
      :alt="t('resultsPage.mondo.panelSearch')"
      class="pcf-panel-link__icon"
      height="14"
      :src="pcfIcon"
      width="14"
    >
  </a>
</template>

<style scoped>
.pcf-panel-link {
  display: inline-flex;
  vertical-align: middle;
  margin-left: 4px;
  line-height: 0;
}

.pcf-panel-link__icon {
  display: block;
  width: 14px;
  height: 14px;
}
</style>
