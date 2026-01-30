<script setup lang="ts">
  import { computed, inject } from 'vue'
  import { useI18n } from 'vue-i18n'

  const { t } = useI18n()
  const openAnalysis = inject<() => void>('openAnalysis')

  // Main Links
  const mainLinks = [
    {
      href: 'https://www.gestaltmatcher.org/',
      icon: 'mdi-home-variant-outline',
      title: 'GestaltMatcher',
      subtitle: 'Visit the GestaltMatcher project website.',
    },
    {
      href: 'https://en.wikipedia.org/wiki/GestaltMatcher',
      icon: 'mdi-wikipedia',
      title: 'Wikipedia Article',
      subtitle: 'GestaltMatcher on Wikipedia.',
    },
    {
      href: 'https://db.gestaltmatcher.org/',
      icon: 'mdi-database-search-outline',
      title: 'GestaltMatcher Database',
      subtitle: 'Explore the project database.',
    },
    {
      href: 'https://pubcasefinder.dbcls.jp/?lang=en',
      icon: 'mdi-book-search-outline',
      title: 'PubCaseFinder',
      subtitle: 'HPO-based Analysis for Rare Genetic Diseases.',
    },
  ]

  // Related Resources
  const resources = [
    {
      href: 'https://github.com/misshie/ngp-suite',
      icon: 'mdi-github',
      title: 'NGPsuite GitHub repository',
    },
  ]

  // Updated Publications list
  const publications = [
    // GestaltMatcher Publications
    {
      category: 'GestaltMatcher',
      title: 'GestaltMatcher facilitates rare disease matching using facial phenotype descriptors',
      authors: 'Hsieh, T.-C. et al.',
      journal: 'Nature Genetics, 54(3), 349-357',
      year: 2022,
      doi: '10.1038/s41588-021-01010-x',
    },
    {
      category: 'GestaltMatcher',
      title: 'Improving deep facial phenotyping for ultra-rare disorder verification using model ensembles',
      authors: 'Hustinx, A. et al.',
      journal: '2023 IEEE/CVF Winter Conference on Applications of Computer Vision (WACV)',
      year: 2023,
      doi: '10.1109/wacv56688.2023.00499',
    },
    {
      category: 'GestaltMatcher',
      title: 'GestaltMatcher Database - A global reference for facial phenotypic variability in rare human diseases',
      authors: 'Lesmann, H. et al.',
      journal: 'medRxiv',
      year: 2024,
      doi: '10.1101/2023.06.06.23290887',
    },
    // PubCaseFinder Publications
    {
      category: 'PubCaseFinder',
      title: 'Ontology-based expansion of virtual gene panels to improve diagnostic efficiency for rare genetic diseases',
      authors: 'Shin, J., Fujiwara, T., Saitsu, H., & Yamaguchi, A.',
      journal: 'BMC medical informatics and decision making, 25(Suppl 1), 59',
      year: 2025,
      doi: '10.1186/s12911-025-02910-2',
    },
    {
      category: 'PubCaseFinder',
      title: 'Advances in the development of PubCaseFinder, including the new application programming interface and matching algorithm',
      authors: 'Fujiwara, T., Shin, J. M., & Yamaguchi, A.',
      journal: 'Human mutation',
      year: 2022,
      doi: '10.1002/humu.24341',
    },
    {
      category: 'PubCaseFinder',
      title: 'Gene Ranking based on Paths from Phenotypes to Genes on Knowledge Graph',
      authors: 'Yamaguchi, A., Shin, J. M., & Fujiwara, T.',
      journal: 'The 10th International Joint Conference on Knowledge Graphs',
      year: 2021,
      doi: '10.1145/3502223.3502240',
    },
    {
      category: 'PubCaseFinder',
      title: 'PubCaseFinder: A case-report-based, phenotype-driven differential-diagnosis system for rare diseases',
      authors: 'Fujiwara, T., Yamamoto, Y., Kim, J. D., Buske, O., & Takagi, T.',
      journal: 'The American Journal of Human Genetics, 103(3), 389-399',
      year: 2018,
      doi: '10.1016/j.ajhg.2018.08.003',
    },
  ]

  // Group publications by category for easier rendering
  const groupedPublications = computed(() => {
    return publications.reduce((acc, pub) => {
      if (!acc[pub.category]) {
        acc[pub.category] = []
      }
      acc[pub.category].push(pub)
      return acc
    }, {} as Record<string, typeof publications>)
  })
</script>

<template>
  <v-container class="fill-height" style="max-width: 900px;">
    <v-responsive class="align-center text-center fill-height">
      <!-- Logo and Title -->
      <v-img
        class="mb-4 mx-auto"
        height="150"
        src="@/assets/NGPsuite.png"
        style="max-width: 600px;"
      />
      <div class="text-body-1 font-weight-light mt-2 mb-6">
        Next-Generation Phenotyping powered by GestaltMatcher and PubCaseFinder
      </div>

      <!-- Call to Action -->
      <v-card
        class="get-started-card py-4 mb-8"
        color="tertiary"
        prepend-icon="mdi-rocket-launch-outline"
        role="button"
        rounded="lg"
        tabindex="0"
        variant="tonal"
        @click="openAnalysis?.()"
        @keydown.enter.prevent="openAnalysis?.()"
        @keydown.space.prevent="openAnalysis?.()"
      >
        <template #title>
          <h2 class="text-h5 font-weight-bold">
            {{ t('startPage.getStarted') }}
          </h2>
        </template>
        <template #subtitle>
          <div class="text-subtitle-1">
            <span v-html="t('startPage.pressAnalysis')" />
          </div>
        </template>
      </v-card>

      <!-- Main Links -->
      <v-row class="mb-4">
        <v-col v-for="link in mainLinks" :key="link.href" cols="12" md="6">
          <v-card
            append-icon="mdi-open-in-new"
            class="py-4 text-left"
            :href="link.href"
            :prepend-icon="link.icon"
            rel="noopener noreferrer"
            rounded="lg"
            :subtitle="link.subtitle"
            target="_blank"
            :title="link.title"
            variant="outlined"
          />
        </v-col>
      </v-row>

      <v-divider class="my-6" />

      <!-- Related Resources -->
      <div class="text-left mb-6">
        <h3 class="text-h6 font-weight-medium mb-2">Related Resources</h3>
        <v-list bg-color="transparent" lines="one">
          <v-list-item
            v-for="resource in resources"
            :key="resource.title"
            :href="resource.href"
            rel="noopener noreferrer"
            rounded="lg"
            target="_blank"
          >
            <template #prepend>
              <v-icon class="mr-4" :icon="resource.icon" />
            </template>
            <v-list-item-title>{{ resource.title }}</v-list-item-title>
            <template #append>
              <v-icon icon="mdi-open-in-new" size="small" />
            </template>
          </v-list-item>
        </v-list>
      </div>

      <!-- Publications -->
      <div class="text-left">
        <h3 class="text-h6 font-weight-medium mb-4">Publications</h3>
        <div v-for="(pubs, category) in groupedPublications" :key="category" class="mb-6">
          <h4 class="text-subtitle-1 font-weight-bold mb-3">{{ category }}</h4>
          <v-list bg-color="transparent" lines="three" class="pa-0">
            <v-list-item
              v-for="(pub, i) in pubs"
              :key="i"
              class="mb-2"
              rounded="lg"
              variant="tonal"
            >
              <v-list-item-title class="font-weight-bold mb-1" style="white-space: normal;">
                {{ pub.title }}
              </v-list-item-title>
              <v-list-item-subtitle style="white-space: normal;">
                {{ pub.authors }} ({{ pub.year }})<br><em>{{ pub.journal }}</em>
              </v-list-item-subtitle>

              <template #append>
                <div class="d-flex flex-column ga-2">
                  <v-btn
                    v-if="pub.doi"
                    :href="`https://doi.org/${pub.doi}`"
                    icon="mdi-book-open-variant"
                    rel="noopener noreferrer"
                    size="small"
                    target="_blank"
                    variant="text"
                  />
                </div>
              </template>
            </v-list-item>
          </v-list>
        </div>
      </div>
      <div class="py-12" />
    </v-responsive>
  </v-container>
</template>

<style scoped>
.get-started-card {
  cursor: pointer;
  transition: opacity 0.2s ease;
}
.get-started-card:hover {
  opacity: 0.92;
}
.get-started-card:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 2px;
}
</style>
