<script lang="ts" setup>
  import { provide, ref, shallowRef } from 'vue'
  import { useI18n } from 'vue-i18n'
  import { useRouter } from 'vue-router'
  import { useStore } from '@/stores/app'

  const { t, locale } = useI18n()

  // Define the complete list of available languages for the menu
  const availableLocales = [
    { code: 'en-US', name: 'English' },
    { code: 'de', name: 'Deutsch' },
    { code: 'es', name: 'Español' },
    { code: 'fr', name: 'Français' },
    { code: 'it', name: 'Italiano' },
    { code: 'ja', name: '日本語' },
    { code: 'ko', name: '한국어' },
    { code: 'pt-BR', name: 'Português' },
    { code: 'zh-CN', name: '简体中文' },
    { code: 'zh-TW', name: '繁體中文' },
  ]

  const isAboutOpen = ref(false)
  const isAnalysisOpen = ref(false)
  const isSettingsOpen = ref(false)
  const isExportOpen = ref(false)
  const drawer = shallowRef(true)

  const store = useStore()
  const router = useRouter()

  function handleLogoClick () {
    store.clearAnalysisResult()
    router.push('/')
  }

  function changeLanguage (newLocaleCode: string) {
    // 1. Update the i18n locale for the UI
    locale.value = newLocaleCode
    // 2. Update the Pinia store for reactive computations (like in Results.vue)
    store.setLocale(newLocaleCode)
  }

  function openAnalysis () {
    isAnalysisOpen.value = true
  }
  provide('openAnalysis', openAnalysis)

</script>

<template>
  <v-layout>
    <Settings v-model="isSettingsOpen" />
    <Analysis v-model="isAnalysisOpen" />
    <About v-model="isAboutOpen" />
    <Export v-model="isExportOpen" />

    <v-navigation-drawer v-model="drawer" permanent width="80">
      <div class="d-flex justify-center pa-4">
        <router-link to="/">
          <v-avatar
            image="@/assets/NGPsuite-Avatar.png"
            style="cursor: pointer;"
            @click="handleLogoClick"
          />
        </router-link>
      </div>

      <v-btn
        class="text-none"
        stacked
        tile
        variant="text"
        width="80"
        @click="isAnalysisOpen = true"
      >
        <v-icon>mdi-face-recognition</v-icon>
        <span class="text-caption">{{ t('nav.analysis') }}</span>
      </v-btn>

      <v-btn
        class="text-none"
        :disabled="!store.analysisResult"
        stacked
        tile
        variant="text"
        width="80"
        @click="isExportOpen = true"
      >
        <v-icon>mdi-export</v-icon>
        <span class="text-caption">{{ t('nav.export') }}</span>
      </v-btn>

      <v-btn
        class="text-none"
        stacked
        tile
        variant="text"
        width="80"
        @click="isSettingsOpen = true"
      >
        <v-icon>mdi-cog</v-icon>
        <span class="text-caption">{{ t('nav.settings') }}</span>
      </v-btn>

      <v-btn
        class="text-none"
        stacked
        tile
        variant="text"
        width="80"
        @click="isAboutOpen = true"
      >
        <v-icon>mdi-information</v-icon>
        <span class="text-caption">{{ t('nav.about') }}</span>
      </v-btn>

    </v-navigation-drawer>

    <v-app-bar color="tertiary" :elevation="2" :title="t('appTitle')">
      <template #prepend>
        <v-app-bar-nav-icon @click="drawer = !drawer" />
      </template>

      <v-spacer />

      <v-menu>
        <template #activator="{ props }">
          <v-btn icon v-bind="props">
            <v-icon>mdi-translate</v-icon>
          </v-btn>
        </template>

        <v-list>
          <v-list-item
            v-for="item in availableLocales"
            :key="item.code"
            @click="changeLanguage(item.code)"
          >
            <v-list-item-title>{{ item.name }}</v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>

    </v-app-bar>

    <v-main>
      <router-view />
    </v-main>

    <AppFooter />
  </v-layout>
</template>
