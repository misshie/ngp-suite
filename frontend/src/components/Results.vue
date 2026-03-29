<script setup lang="ts">
  import type { VDataTable } from 'vuetify/components'
  import { computed, ref, watch } from 'vue'
  import { useI18n } from 'vue-i18n'
  import { useStore } from '@/stores/app'

  const { t } = useI18n()
  const store = useStore()

  const tab = ref('Syndromes')
  const geneSearch = ref('')
  const syndromeSearch = ref('')
  const patientSearch = ref('')

  type ReadonlyHeaders = VDataTable['$props']['headers']

  const tabs = computed(() => {
    if (!store.analysisResult) return []
    const availableTabs: { key: string, labelKey: string, count: number }[] = []
    if (store.analysisResult.suggested_syndromes_list?.length) {
      availableTabs.push({ key: 'Syndromes', labelKey: 'resultsPage.tabs.syndromes', count: store.analysisResult.suggested_syndromes_list.length })
    }
    if (store.analysisResult.suggested_genes_list?.length) {
      availableTabs.push({ key: 'Genes', labelKey: 'resultsPage.tabs.genes', count: store.analysisResult.suggested_genes_list.length })
    }
    if (store.analysisResult.suggested_patients_list?.length) {
      availableTabs.push({ key: 'Patients', labelKey: 'resultsPage.tabs.patients', count: store.analysisResult.suggested_patients_list.length })
    }
    return availableTabs
  })

  const geneHeaders = computed((): ReadonlyHeaders => [
    { title: 'Meta Rank', key: 'meta_rank', align: 'end' },
    { title: 'GM Rank', key: 'gm_rank', align: 'end' },
    { title: 'PCF Rank', key: 'pubcasefinder_rank', align: 'end' },
    { title: 'Gene Symbol', key: 'gene_name', align: 'start' },
    { title: 'Entrez ID', key: 'gene_entrez_id', align: 'start' },
    { title: 'GM Distance', key: 'distance', align: 'end' },
    { title: 'GM Match', key: 'score', align: 'center', sortable: false },
    { title: 'PCF Score', key: 'pubcasefinder_score', align: 'end' },
    { title: 'PCF Match', key: 'pcf_match_visual', align: 'center', sortable: false },
  ])

  const syndromeHeaders = computed((): ReadonlyHeaders => [
    { title: 'Meta Rank', key: 'meta_rank', align: 'end' },
    { title: 'GM Rank', key: 'gm_rank', align: 'end' },
    { title: 'PCF Rank', key: 'pubcasefinder_rank', align: 'end' },
    { title: 'Syndrome Name', key: 'syndrome_name', align: 'start' },
    { title: 'OMIM ID', key: 'omim_id', align: 'start' },
    { title: 'GM Score', key: 'gm_score', align: 'end' },
    { title: 'ACMG PP4', key: 'ACMG_PP4', align: 'start' },
    { title: 'GM Distance', key: 'distance', align: 'end' },
    { title: 'GM Match', key: 'score', align: 'center', sortable: false },
    { title: 'PCF Score', key: 'pubcasefinder_score', align: 'end' },
    { title: 'PCF Match', key: 'pcf_match_visual', align: 'center', sortable: false },
  ])

  const patientHeaders = computed((): ReadonlyHeaders => [
    { title: 'Meta Rank', key: 'meta_rank', align: 'end' },
    { title: 'GM Rank', key: 'gm_rank', align: 'end' },
    { title: 'PCF Rank', key: 'pubcasefinder_rank', align: 'end' },
    { title: 'GM Patient ID', key: 'subject_id', align: 'start' },
    { title: 'Syndrome Name', key: 'syndrome_name', align: 'start' },
    { title: 'OMIM ID', key: 'numeric_omim_id', align: 'start' },
    { title: 'Phenotypic Series', key: 'phenotypic_series_id', align: 'start' },
    { title: 'GM Distance', key: 'distance', align: 'end' },
    { title: 'GM Match', key: 'score', align: 'center', sortable: false },
    { title: 'PCF Score', key: 'pubcasefinder_score', align: 'end' },
    { title: 'PCF Match', key: 'pcf_match_visual', align: 'center', sortable: false },
  ])

  const hpoQueryList = computed(() => {
    const result = store.analysisResult
    if (!result?.queried_hpo_ids?.length || !result.pubcasefinder?.hpo_names) {
      return []
    }

    // Determine which language name to use based on the current locale
    const nameKey = store.locale === 'ja' ? 'name_ja' : 'name_en'

    return result.queried_hpo_ids.map(hpoId => {
      const hpoData = result.pubcasefinder?.hpo_names[hpoId]
      return {
        id: hpoId,
        name: hpoData ? hpoData[nameKey] ?? hpoData.name_en : 'Name not found',
      }
    })
  })

  const GM_SCORE_OFFSET = 1.3

  const geneItems = computed(() => store.analysisResult?.suggested_genes_list || [])
  const syndromeItems = computed(() => store.analysisResult?.suggested_syndromes_list || [])
  const syndromeTableItems = computed(() =>
    syndromeItems.value.map(item => ({
      ...item,
      gm_score: typeof item.distance === 'number' ? GM_SCORE_OFFSET - item.distance : undefined,
    })),
  )
  const patientItems = computed(() => store.analysisResult?.suggested_patients_list || [])

  watch(
    () => store.analysisResult,
    newResult => {
      if (newResult && tabs.value.length > 0) {
        const currentTabExists = tabs.value.some(t => t.key === tab.value)
        if (!tab.value || !currentTabExists) {
          tab.value = tabs.value[0].key
        }
      }
    },
    { immediate: true },
  )

  function formatScore (score: number | undefined | null) {
    return typeof score === 'number' ? score.toFixed(4) : '-'
  }

  function rankSort (a: number | null | undefined, b: number | null | undefined) {
    const aIsNull = a === null || a === undefined
    const bIsNull = b === null || b === undefined
    if (aIsNull && bIsNull) return 0
    if (aIsNull) return 1
    if (bIsNull) return -1
    return a - b
  }

  const customRankSorters = {
    meta_rank: rankSort,
    gm_rank: rankSort,
    pubcasefinder_rank: rankSort,
    gm_score: rankSort,
  }
</script>

<template>
  <v-container v-if="store.analysisResult" fluid>
    <!-- ROW: Displays image and HPO list side-by-side -->
    <v-row class="mb-4" :justify="hpoQueryList.length > 0 ? 'start' : 'center'">
      <!-- Image Column -->
      <v-col v-if="store.uploadedImage" cols="auto">
        <v-card elevation="2" width="180">
          <v-img alt="Uploaded analysis image" aspect-ratio="1" cover :src="store.uploadedImage" />
        </v-card>
      </v-col>

      <!-- HPO List Column (only if HPO data exists) -->
      <v-col v-if="hpoQueryList.length > 0">
        <v-card elevation="2">
          <v-card-title class="text-subtitle-2 py-2">
            {{ t('resultsPage.queriedHpo') }}
          </v-card-title>
          <v-divider />
          <v-table density="compact" fixed-header height="150px">
            <thead>
              <tr>
                <th class="text-left">HPO ID</th>
                <th class="text-left">Name</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="hpo in hpoQueryList" :key="hpo.id">
                <td>{{ hpo.id }}</td>
                <td>{{ hpo.name }}</td>
              </tr>
            </tbody>
          </v-table>
        </v-card>
      </v-col>
    </v-row>

    <!-- Main Results Card -->
    <v-card>
      <v-card-text class="d-flex justify-space-between text-caption py-2">
        <span>Model Version: {{ store.analysisResult?.model_version }}</span>
        <span>Gallery Version: {{ store.analysisResult?.gallery_version }}</span>
      </v-card-text>
      <v-divider />

      <v-tabs v-model="tab" bg-color="tertiary">
        <v-tab v-for="item in tabs" :key="item.key" :value="item.key">
          {{ t(item.labelKey) }} ({{ item.count }})
        </v-tab>
      </v-tabs>

      <v-card-text>
        <v-window v-model="tab">
          <!-- Syndromes Tab -->
          <v-window-item value="Syndromes">
            <v-text-field
              v-model="syndromeSearch"
              class="mb-4"
              density="compact"
              flat
              hide-details
              :label="t('resultsPage.search.syndromes')"
              prepend-inner-icon="mdi-magnify"
              single-line
              variant="solo-filled"
            />
            <v-data-table
              :custom-key-sort="customRankSorters"
              density="compact"
              :headers="syndromeHeaders"
              item-value="syndrome_name"
              :items="syndromeTableItems"
              :search="syndromeSearch"
              :sort-by="[{ key: 'gm_rank', order: 'asc' }]"
            >
              <template #item.gm_score="{ item }">{{ formatScore(item.gm_score) }}</template>
              <template #item.ACMG_PP4="{ item }">{{ item.ACMG_PP4 ?? '-' }}</template>
              <template #item.distance="{ item }">{{ formatScore(item.distance) }}</template>
              <template #item.score="{ item }"><v-progress-linear color="blue-grey" height="10" :model-value="(item.score || 0) * 100" rounded /></template>
              <template #item.omim_id="{ item }"><a
                v-if="item.omim_id"
                class="text-decoration-none"
                :href="`https://www.omim.org/entry/${item.omim_id}`"
                rel="noopener noreferrer"
                target="_blank"
              >{{ item.omim_id }} <v-icon class="ml-1" icon="mdi-open-in-new" size="x-small" /></a></template>
              <template #item.pubcasefinder_rank="{ item }">{{ item.pubcasefinder_rank ?? '-' }}</template>
              <template #item.pubcasefinder_score="{ item }">{{ formatScore(item.pubcasefinder_score) }}</template>
              <template #item.pcf_match_visual="{ item }"><v-progress-linear
                v-if="item.pubcasefinder_score !== null && item.pubcasefinder_score !== undefined"
                color="teal"
                height="10"
                :model-value="item.pubcasefinder_score * 100"
                rounded
              /><span v-else>-</span></template>
            </v-data-table>
          </v-window-item>

          <!-- Genes Tab -->
          <v-window-item value="Genes">
            <v-text-field
              v-model="geneSearch"
              class="mb-4"
              density="compact"
              flat
              hide-details
              :label="t('resultsPage.search.genes')"
              prepend-inner-icon="mdi-magnify"
              single-line
              variant="solo-filled"
            />
            <v-data-table
              :custom-key-sort="customRankSorters"
              density="compact"
              :headers="geneHeaders"
              item-value="gene_name"
              :items="geneItems"
              :search="geneSearch"
              :sort-by="[{ key: 'gm_rank', order: 'asc' }]"
            >
              <template #item.distance="{ item }">{{ formatScore(item.distance) }}</template>
              <template #item.score="{ item }"><v-progress-linear color="blue-grey" height="10" :model-value="(item.score || 0) * 100" rounded /></template>
              <template #item.gene_entrez_id="{ item }"><a
                v-if="item.gene_entrez_id"
                class="text-decoration-none"
                :href="`https://www.ncbi.nlm.nih.gov/gene/${item.gene_entrez_id}`"
                rel="noopener noreferrer"
                target="_blank"
              >{{ item.gene_entrez_id }} <v-icon class="ml-1" icon="mdi-open-in-new" size="x-small" /></a></template>
              <template #item.pubcasefinder_rank="{ item }">{{ item.pubcasefinder_rank ?? '-' }}</template>
              <template #item.pubcasefinder_score="{ item }">{{ formatScore(item.pubcasefinder_score) }}</template>
              <template #item.pcf_match_visual="{ item }"><v-progress-linear
                v-if="item.pubcasefinder_score !== null && item.pubcasefinder_score !== undefined"
                color="teal"
                height="10"
                :model-value="item.pubcasefinder_score * 100"
                rounded
              /><span v-else>-</span></template>
            </v-data-table>
          </v-window-item>

          <!-- Patients Tab -->
          <v-window-item value="Patients">
            <v-text-field
              v-model="patientSearch"
              class="mb-4"
              density="compact"
              flat
              hide-details
              :label="t('resultsPage.search.patients')"
              prepend-inner-icon="mdi-magnify"
              single-line
              variant="solo-filled"
            />
            <v-data-table
              :custom-key-sort="customRankSorters"
              density="compact"
              :headers="patientHeaders"
              item-value="subject_id"
              :items="patientItems"
              :search="patientSearch"
              :sort-by="[{ key: 'gm_rank', order: 'asc' }]"
            >
              <template #item.distance="{ item }">{{ formatScore(item.distance) }}</template>
              <template #item.score="{ item }"><v-progress-linear color="blue-grey" height="10" :model-value="(item.score || 0) * 100" rounded /></template>
              <template #item.numeric_omim_id="{ item }"><a
                v-if="item.numeric_omim_id"
                class="text-decoration-none"
                :href="`https://www.omim.org/entry/${item.numeric_omim_id}`"
                rel="noopener noreferrer"
                target="_blank"
              >{{ item.numeric_omim_id }} <v-icon class="ml-1" icon="mdi-open-in-new" size="x-small" /></a></template>
              <template #item.phenotypic_series_id="{ item }"><a
                v-if="item.phenotypic_series_id"
                class="text-decoration-none"
                :href="`https://www.omim.org/phenotypicSeries/${item.phenotypic_series_id}`"
                rel="noopener noreferrer"
                target="_blank"
              >{{ item.phenotypic_series_id }} <v-icon class="ml-1" icon="mdi-open-in-new" size="x-small" /></a></template>
              <template #item.pubcasefinder_rank="{ item }">{{ item.pubcasefinder_rank ?? '-' }}</template>
              <template #item.pubcasefinder_score="{ item }">{{ formatScore(item.pubcasefinder_score) }}</template>
              <template #item.pcf_match_visual="{ item }"><v-progress-linear
                v-if="item.pubcasefinder_score !== null && item.pubcasefinder_score !== undefined"
                color="teal"
                height="10"
                :model-value="item.pubcasefinder_score * 100"
                rounded
              /><span v-else>-</span></template>
            </v-data-table>
          </v-window-item>
        </v-window>
      </v-card-text>
    </v-card>
  </v-container>
  <v-container v-else>
    <v-alert border="start" type="info" variant="tonal">{{ t('resultsPage.noResults') }}</v-alert>
  </v-container>
</template>
