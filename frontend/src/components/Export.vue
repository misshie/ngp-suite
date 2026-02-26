<script setup lang="ts">
  import { computed, ref } from 'vue'
  import { useI18n } from 'vue-i18n'
  import * as XLSX from 'xlsx' // Import the xlsx library
  import { useStore } from '@/stores/app'

  const { t } = useI18n()

  defineProps<{
    modelValue: boolean
  }>()

  const emit = defineEmits<{
    (e: 'update:modelValue', value: boolean): void
  }>()

  const store = useStore()

  // State to manage which dataset is selected for TSV export
  const tsvExportSelection = ref<'genes' | 'syndromes' | 'patients' | 'metadata'>('genes')

  // --- NEW: Computed property to prepare metadata for export ---
  const metadataItems = computed(() => {
    if (!store.analysisResult) return []

    const items = [
      { parameter: 'Model Version', value_en: store.analysisResult.model_version, value_ja: '' },
      { parameter: 'Gallery Version', value_en: store.analysisResult.gallery_version, value_ja: '' },
    ]

    const hpoIds = store.analysisResult.queried_hpo_ids
    const hpoNames = store.analysisResult.pubcasefinder?.hpo_names

    if (hpoIds && hpoNames) {
      items.push({ parameter: '---', value_en: '---', value_ja: '---' }) // Separator
      for (const hpoId of hpoIds) {
        const names = hpoNames[hpoId]
        items.push({
          parameter: hpoId,
          value_en: names?.name_en || '',
          value_ja: names?.name_ja || '',
        })
      }
    }
    return items
  })

  /**
   * Exports all available result lists to a single XLSX file with multiple sheets.
   */
  function exportAsXLSX () {
    if (!store.analysisResult) return

    const wb = XLSX.utils.book_new()

    // --- UPDATED: Add Metadata sheet if available ---
    if (metadataItems.value.length > 0) {
      const ws = XLSX.utils.json_to_sheet(metadataItems.value)
      XLSX.utils.book_append_sheet(wb, ws, 'Metadata')
    }

    // Add other sheets as before
    if (store.analysisResult.suggested_syndromes_list) {
      const ws = XLSX.utils.json_to_sheet(store.analysisResult.suggested_syndromes_list)
      XLSX.utils.book_append_sheet(wb, ws, 'Syndromes')
    }
    if (store.analysisResult.suggested_genes_list) {
      const ws = XLSX.utils.json_to_sheet(store.analysisResult.suggested_genes_list)
      XLSX.utils.book_append_sheet(wb, ws, 'Genes')
    }
    if (store.analysisResult.suggested_patients_list) {
      const ws = XLSX.utils.json_to_sheet(store.analysisResult.suggested_patients_list)
      XLSX.utils.book_append_sheet(wb, ws, 'Patients')
    }

    XLSX.writeFile(wb, 'piNGPong_tables_results.xlsx')
    emit('update:modelValue', false)
  }

  /**
   * Converts an array of objects to a TSV string and triggers a download.
   */
  function downloadTSV (data: any[], filename: string) {
    if (data.length === 0) return

    const headers = Object.keys(data[0])
    const headerRow = headers.join('\t')
    const dataRows = data.map(row =>
      headers.map(header => row[header]).join('\t'),
    )

    const tsvContent = [headerRow, ...dataRows].join('\n')
    const blob = new Blob([tsvContent], { type: 'text/tab-separated-values;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute('download', filename)
    link.style.visibility = 'hidden'
    document.body.append(link)
    link.click()
    link.remove()
  }

  /**
   * Handles the TSV export based on the user's selection.
   */
  function exportAsTSV () {
    if (!store.analysisResult) return

    switch (tsvExportSelection.value) {
      case 'metadata': { // --- ADDED ---
        downloadTSV(metadataItems.value, 'metadata.tsv')
        break
      }
      case 'genes': {
        downloadTSV(store.analysisResult.suggested_genes_list, 'genes.tsv')
        break
      }
      case 'syndromes': {
        downloadTSV(store.analysisResult.suggested_syndromes_list, 'syndromes.tsv')
        break
      }
      case 'patients': {
        downloadTSV(store.analysisResult.suggested_patients_list, 'patients.tsv')
        break
      }
    }
    emit('update:modelValue', false)
  }

  /**
   * Exports the full analysis result as a JSON file.
   */
  function exportAsJSON () {
    if (!store.analysisResult) return

    const jsonString = JSON.stringify(store.analysisResult, null, 2)
    const blob = new Blob([jsonString], { type: 'application/json;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute('download', 'ngpsuite_analysis_result.json')
    link.style.visibility = 'hidden'
    document.body.append(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
    emit('update:modelValue', false)
  }

</script>

<template>
  <v-dialog
    max-width="500"
    :model-value="modelValue"
    persistent
    @update:model-value="emit('update:modelValue', $event)"
  >
    <v-card rounded="lg">
      <v-card-title>
        <span class="text-h5">{{ t('exportDialog.title') }}</span>
      </v-card-title>
      <v-card-subtitle>{{ t('exportDialog.subtitle') }}</v-card-subtitle>

      <v-card-text class="pt-4">
        <!-- Excel Export Section -->
        <p class="text-overline">{{ t('exportDialog.excel.title') }}</p>
        <p class="text-body-2 mb-4">{{ t('exportDialog.excel.description') }}</p>
        <v-btn
          block
          color="success"
          prepend-icon="mdi-file-excel"
          @click="exportAsXLSX"
        >
          {{ t('exportDialog.excel.button') }}
        </v-btn>

        <v-divider class="my-6" />

        <!-- TSV Export Section -->
        <p class="text-overline">{{ t('exportDialog.tsv.title') }}</p>
        <p class="text-body-2 mb-4">{{ t('exportDialog.tsv.description') }}</p>
        <v-select
          v-model="tsvExportSelection"
          density="compact"
          :items="[
            { title: 'Metadata', value: 'metadata' },
            { title: 'Genes', value: 'genes' },
            { title: 'Syndromes', value: 'syndromes' },
            { title: 'Patients', value: 'patients' }
          ]"
          :label="t('exportDialog.tsv.label')"
          variant="outlined"
        />
        <v-btn
          block
          class="mt-2"
          color="secondary"
          prepend-icon="mdi-file-delimited"
          @click="exportAsTSV"
        >
          {{ t('exportDialog.tsv.button') }}
        </v-btn>

        <v-divider class="my-6" />

        <!-- JSON Export Section -->
        <p class="text-overline">{{ t('exportDialog.json.title') }}</p>
        <p class="text-body-2 mb-4">{{ t('exportDialog.json.description') }}</p>
        <v-btn
          block
          color="primary"
          prepend-icon="mdi-code-json"
          @click="exportAsJSON"
        >
          {{ t('exportDialog.json.button') }}
        </v-btn>

      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn
          :text="t('common.cancel')"
          @click="emit('update:modelValue', false)"
        />
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
