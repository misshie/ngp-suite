<script setup lang="ts">
  import type { VDataTable } from 'vuetify/components'
  import { computed, inject, ref, watch } from 'vue'
  import { useI18n } from 'vue-i18n'
  import { useStore } from '@/stores/app'
  import { geneLabel, syndromeLabel } from '@/utils/mondoLabel'

  const { t } = useI18n()
  const store = useStore()
  const openExport = inject<() => void>('openExport')

  type TabKey = 'Syndromes' | 'Genes' | 'Patients'

  const tab = ref<TabKey>('Syndromes')
  const geneSearch = ref('')
  const syndromeSearch = ref('')
  const patientSearch = ref('')

  type ReadonlyHeaders = VDataTable['$props']['headers']
  type Header = NonNullable<ReadonlyHeaders>[number]
  type TableSortItem = {
    key: string
    order?: 'asc' | 'desc' | boolean
  }

  const syndromeSortBy = ref<TableSortItem[]>([{ key: 'gm_rank', order: 'asc' }])

  const PCF_COLUMN_KEYS = new Set(['meta_rank', 'pubcasefinder_rank', 'pubcasefinder_score', 'pcf_match_visual'])

  const tabs = computed(() => {
    if (!store.analysisResult) return []
    const availableTabs: { key: TabKey, labelKey: string, count: number }[] = []
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

  const geneHeadersAll = computed((): Header[] => [
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

  const syndromeHeadersAll = computed((): Header[] => [
    { title: 'Meta Rank', key: 'meta_rank', align: 'end' },
    { title: 'GM Rank', key: 'gm_rank', align: 'end' },
    { title: 'PCF Rank', key: 'pubcasefinder_rank', align: 'end' },
    { title: 'Syndrome Name', key: 'syndrome_name', align: 'start' },
    { title: 'MONDO ID', key: 'mondo_id', align: 'start' },
    { title: '1-level higher term (MONDO)', key: 'mondo_parents', align: 'start', sortable: false },
    { title: '2-level higher term (MONDO)', key: 'mondo_grandparents', align: 'start', sortable: false },
    { title: 'OMIM ID', key: 'omim_id', align: 'start' },
    { title: 'GM Score', key: 'gm_score', align: 'end' },
    { title: 'ACMG PP4', key: 'ACMG_PP4', align: 'start' },
    { title: 'GM Distance', key: 'distance', align: 'end' },
    { title: 'GM Match', key: 'score', align: 'center', sortable: false },
    { title: 'PCF Score', key: 'pubcasefinder_score', align: 'end' },
    { title: 'PCF Match', key: 'pcf_match_visual', align: 'center', sortable: false },
  ])

  const patientHeadersAll = computed((): Header[] => [
    { title: 'Meta Rank', key: 'meta_rank', align: 'end' },
    { title: 'GM Rank', key: 'gm_rank', align: 'end' },
    { title: 'PCF Rank', key: 'pubcasefinder_rank', align: 'end' },
    { title: 'GM Patient ID', key: 'subject_id', align: 'start' },
    { title: 'Syndrome Name', key: 'syndrome_name', align: 'start' },
    { title: 'MONDO ID', key: 'mondo_id', align: 'start', sortable: false },
    { title: 'OMIM ID', key: 'numeric_omim_id', align: 'start' },
    { title: 'Phenotypic Series', key: 'phenotypic_series_id', align: 'start' },
    { title: 'GM Distance', key: 'distance', align: 'end' },
    { title: 'GM Match', key: 'score', align: 'center', sortable: false },
    { title: 'PCF Score', key: 'pubcasefinder_score', align: 'end' },
    { title: 'PCF Match', key: 'pcf_match_visual', align: 'center', sortable: false },
  ])

  const headersByTab = computed((): Record<TabKey, Header[]> => ({
    Syndromes: syndromeHeadersAll.value,
    Genes: geneHeadersAll.value,
    Patients: patientHeadersAll.value,
  }))

  const columnVisibility = ref<Record<TabKey, Record<string, boolean>>>({
    Syndromes: {},
    Genes: {},
    Patients: {},
  })

  function hasHpo (result: typeof store.analysisResult) {
    return Boolean(result?.queried_hpo_ids?.length)
  }

  function defaultVisibility (headers: Header[], tabKey: TabKey, withHpo: boolean) {
    const visible: Record<string, boolean> = {}
    for (const header of headers) {
      const key = header.key as string
      if (tabKey === 'Syndromes' && key === 'ACMG_PP4') {
        visible[key] = false
      } else if (!withHpo && PCF_COLUMN_KEYS.has(key)) {
        visible[key] = false
      } else {
        visible[key] = true
      }
    }
    return visible
  }

  function applyColumnDefaults () {
    const withHpo = hasHpo(store.analysisResult)
    columnVisibility.value = {
      Syndromes: defaultVisibility(syndromeHeadersAll.value, 'Syndromes', withHpo),
      Genes: defaultVisibility(geneHeadersAll.value, 'Genes', withHpo),
      Patients: defaultVisibility(patientHeadersAll.value, 'Patients', withHpo),
    }
  }

  function setColumnVisible (key: string, value: boolean | null) {
    columnVisibility.value[tab.value] = {
      ...columnVisibility.value[tab.value],
      [key]: Boolean(value),
    }
  }

  const currentTabHeaders = computed(() => headersByTab.value[tab.value] || [])
  const geneHeaders = computed(() => geneHeadersAll.value.filter(h => columnVisibility.value.Genes[h.key as string] !== false))
  const syndromeHeaders = computed(() => syndromeHeadersAll.value.filter(h => columnVisibility.value.Syndromes[h.key as string] !== false))
  const patientHeaders = computed(() => patientHeadersAll.value.filter(h => columnVisibility.value.Patients[h.key as string] !== false))

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
      if (newResult) {
        applyColumnDefaults()
      }
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

  const PP4_RANK: Record<string, number> = {
    very_strong: 4,
    strong: 3,
    moderate: 2,
    supporting: 1,
  }

  function pp4Rank (value: string | null | undefined) {
    if (!value) return 0
    const normalized = value.trim().toLowerCase().replace(/\s+/g, '_')
    return PP4_RANK[normalized] ?? 0
  }

  function comparePp4Values (
    a: string | null | undefined,
    b: string | null | undefined,
    order: 'asc' | 'desc',
  ) {
    const aRank = pp4Rank(a)
    const bRank = pp4Rank(b)
    const aMissing = aRank === 0
    const bMissing = bRank === 0
    if (aMissing && bMissing) return 0
    if (aMissing) return 1
    if (bMissing) return -1
    const diff = aRank - bRank
    return order === 'desc' ? -diff : diff
  }

  function getPp4SortOrder (): 'asc' | 'desc' {
    const item = syndromeSortBy.value.find(sort => sort.key === 'ACMG_PP4')
    return item?.order === 'desc' ? 'desc' : 'asc'
  }

  /** Undo Vuetify's desc operand swap so missing values always sort last. */
  function pp4Sort (sortA: string | null | undefined, sortB: string | null | undefined) {
    const order = getPp4SortOrder()
    const a = order === 'desc' ? sortB : sortA
    const b = order === 'desc' ? sortA : sortB
    return comparePp4Values(a, b, order)
  }

  const customRankSorters = {
    meta_rank: rankSort,
    gm_rank: rankSort,
    pubcasefinder_rank: rankSort,
    gm_score: rankSort,
  }

  const syndromeCustomSorters = {
    ...customRankSorters,
    ACMG_PP4: pp4Sort,
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
      <v-card-text class="d-flex justify-end text-caption py-2">
        <span>
          <template v-if="store.analysisResult?.mondo_version">{{ t('resultsPage.mondoVersion') }}: {{ store.analysisResult.mondo_version }}, </template>{{ t('resultsPage.modelVersion') }}: {{ store.analysisResult?.model_version }}, {{ t('resultsPage.galleryVersion') }}: {{ store.analysisResult?.gallery_version }}
        </span>
      </v-card-text>
      <v-divider />

      <div class="d-flex align-center bg-tertiary">
        <v-tabs
          v-model="tab"
          bg-color="tertiary"
          class="results-tabs flex-grow-1"
          slider-color="white"
        >
          <v-tab v-for="item in tabs" :key="item.key" :value="item.key">
            {{ t(item.labelKey) }} ({{ item.count }})
          </v-tab>
        </v-tabs>
        <v-menu :close-on-content-click="false">
          <template #activator="{ props }">
            <v-btn
              class="text-none me-2"
              color="surface"
              prepend-icon="mdi-table-column"
              size="small"
              v-bind="props"
              variant="flat"
            >
              {{ t('resultsPage.columns') }}
            </v-btn>
          </template>
          <v-list density="compact" max-height="420" style="overflow-y: auto">
            <v-list-item v-for="header in currentTabHeaders" :key="String(header.key)">
              <v-checkbox
                density="compact"
                hide-details
                :label="String(header.title)"
                :model-value="columnVisibility[tab][header.key as string] !== false"
                @update:model-value="setColumnVisible(header.key as string, $event)"
              />
            </v-list-item>
          </v-list>
        </v-menu>
        <v-btn
          class="text-none me-2"
          color="surface"
          prepend-icon="mdi-export"
          size="small"
          variant="flat"
          @click="openExport?.()"
        >
          {{ t('nav.export') }}
        </v-btn>
      </div>

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
              v-model:sort-by="syndromeSortBy"
              :custom-key-sort="syndromeCustomSorters"
              density="compact"
              :headers="syndromeHeaders"
              item-value="syndrome_name"
              :items="syndromeTableItems"
              :search="syndromeSearch"
            >
              <template #item.syndrome_name="{ item }">
                {{ syndromeLabel(item, store.locale) }}
                <v-chip
                  v-if="item.mondo_source === 'gene'"
                  class="ml-1"
                  color="blue-grey"
                  size="x-small"
                  :title="t('resultsPage.mondo.geneDerivedHint')"
                  variant="tonal"
                >{{ t('resultsPage.mondo.geneDerived') }}</v-chip>
              </template>
              <template #item.mondo_id="{ item }">
                <template v-if="item.mondo_id">
                  <a
                    class="text-decoration-none"
                    :href="`https://monarchinitiative.org/${item.mondo_id}`"
                    rel="noopener noreferrer"
                    target="_blank"
                  >{{ item.mondo_id }} <v-icon class="ml-1" icon="mdi-open-in-new" size="x-small" /></a>
                  <PubCaseFinderPanelLink :mondo-id="item.mondo_id" />
                  <NanbyoDataLink :mondo-id="item.mondo_id" />
                  <OmimEntryLink :mondo-id="item.mondo_id" />
                </template>
                <span v-else>-</span>
              </template>
              <template #item.mondo_parents="{ item }"><MondoTermList :terms="item.mondo_parents" /></template>
              <template #item.mondo_grandparents="{ item }"><MondoTermList :terms="item.mondo_grandparents" /></template>
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
              <template #item.gene_name="{ item }">
                {{ geneLabel(item, store.locale) }}
                <v-chip
                  v-if="item.gene_unresolved"
                  class="ml-1"
                  color="blue-grey"
                  size="x-small"
                  :title="t('resultsPage.gene.unresolvedHint')"
                  variant="tonal"
                >{{ t('resultsPage.gene.unresolved') }}</v-chip>
                <v-chip
                  v-else-if="item.subtype_unresolved"
                  class="ml-1"
                  color="amber-darken-2"
                  size="x-small"
                  :title="t('resultsPage.gene.subtypeUnresolvedHint')"
                  variant="tonal"
                >{{ t('resultsPage.gene.subtypeUnresolved') }}</v-chip>
                <v-chip
                  v-else-if="item.gene_source === 'mondo'"
                  class="ml-1"
                  color="teal"
                  size="x-small"
                  :title="t('resultsPage.gene.mondoSourcedHint')"
                  variant="tonal"
                >{{ t('resultsPage.gene.mondoSourced') }}</v-chip>
              </template>
              <template #item.distance="{ item }">{{ formatScore(item.distance) }}</template>
              <template #item.score="{ item }"><v-progress-linear color="blue-grey" height="10" :model-value="(item.score || 0) * 100" rounded /></template>
              <template #item.gene_entrez_id="{ item }">
                <a
                  v-if="item.gene_entrez_id"
                  class="text-decoration-none"
                  :href="`https://www.ncbi.nlm.nih.gov/gene/${item.gene_entrez_id}`"
                  rel="noopener noreferrer"
                  target="_blank"
                >{{ item.gene_entrez_id }} <v-icon class="ml-1" icon="mdi-open-in-new" size="x-small" /></a>
                <a
                  v-else-if="item.hgnc_id"
                  class="text-decoration-none"
                  :href="`https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/${item.hgnc_id}`"
                  rel="noopener noreferrer"
                  target="_blank"
                >{{ item.hgnc_id }} <v-icon class="ml-1" icon="mdi-open-in-new" size="x-small" /></a>
                <span v-else>-</span>
              </template>
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
              <template #item.syndrome_name="{ item }">{{ syndromeLabel(item, store.locale) }}</template>
              <template #item.score="{ item }"><v-progress-linear color="blue-grey" height="10" :model-value="(item.score || 0) * 100" rounded /></template>
              <template #item.mondo_id="{ item }"><MondoTermList :ids="item.mondo_id" nanbyo-link omim-link panel-link /></template>
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

<style scoped>
.results-tabs :deep(.v-tab__slider) {
  height: 4px;
}
</style>
