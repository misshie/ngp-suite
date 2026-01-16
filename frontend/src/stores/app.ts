import { defineStore } from 'pinia'

interface GeneEntry {
  gene_name: string
  gene_entrez_id: string
  distance: number
  score: number | null
  gm_rank?: number
  pubcasefinder_rank?: number
  pubcasefinder_score?: number
  mean_rank?: number | null
  meta_rank?: number
}

interface SyndromeEntry {
  syndrome_name: string
  omim_id: number
  distance: number
  image_id: string
  subject_id: string
  score: number | null
  gm_rank?: number
  pubcasefinder_rank?: number
  pubcasefinder_score?: number
  mean_rank?: number | null
  meta_rank?: number
}

interface PatientEntry {
  subject_id: string
  gene_name: string
  gene_entrez_id: string
  distance: number
  image_id: string
  syndrome_name: string
  omim_id: number | string
  score: number | null
  gm_rank?: number
  pubcasefinder_rank?: number
  pubcasefinder_score?: number
  mean_rank?: number | null
  meta_rank?: number
  numeric_omim_id?: number | null
  phenotypic_series_id?: string | null
}

interface HpoNameEntry {
  name_en: string
  name_ja: string
}

interface HpoNames {
  // Allows indexing by HPO ID string, e.g., "HP:0000347"
  [key: string]: HpoNameEntry
}

interface PubCaseFinderResult {
  ranked_list: any[] // This contains the raw ranked list for matching
  hpo_names: HpoNames
}

export interface AnalysisResult {
  model_version: string
  gallery_version: string
  suggested_genes_list: GeneEntry[]
  suggested_syndromes_list: SyndromeEntry[]
  suggested_patients_list: PatientEntry[]
  // The original HPO IDs sent in the request
  queried_hpo_ids?: string[]
  // The structured result from pubcasefinder.py
  pubcasefinder?: PubCaseFinderResult
}

export interface AppSettings {
  host: string
  port: string
  user: string
  password: string
  locale: string
}

// LocalStorage key for settings
const SETTINGS_STORAGE_KEY = 'ngpsuite_settings'

// Default settings
const defaultSettings: AppSettings = {
  host: 'https://localhost/',
  port: '443',
  user: 'your_username',
  password: 'your_password',
  locale: 'en-US',
}

// Load settings from localStorage
function loadSettingsFromStorage (): AppSettings {
  try {
    const stored = localStorage.getItem(SETTINGS_STORAGE_KEY)
    if (stored) {
      const parsed = JSON.parse(stored)
      // Merge with defaults to handle missing fields
      return { ...defaultSettings, ...parsed }
    }
  } catch (error) {
    console.warn('Failed to load settings from localStorage:', error)
  }
  return defaultSettings
}

// Save settings to localStorage
function saveSettingsToStorage (settings: AppSettings): void {
  try {
    localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings))
  } catch (error) {
    console.warn('Failed to save settings to localStorage:', error)
  }
}

// Load initial settings
const initialSettings = loadSettingsFromStorage()

export const useStore = defineStore('app', {
  state: () => ({
    host: initialSettings.host,
    port: initialSettings.port,
    user: initialSettings.user,
    password: initialSettings.password,
    locale: initialSettings.locale,
    analysisResult: null as AnalysisResult | null,
    uploadedImage: null as string | null,
  }),

  getters: {
    predictApiUri: (state): string => {
      const baseUrl = `${state.host.replace(/\/$/, '')}:${state.port}`
      return `${baseUrl}/api/predict`
    },
  },

  actions: {
    setLocale (newLocale: string) {
      this.locale = newLocale
      // Save to localStorage (preserve other settings)
      const currentSettings = loadSettingsFromStorage()
      saveSettingsToStorage({
        ...currentSettings,
        locale: newLocale,
      })
    },

    setUploadedImage (imageDataUrl: string) {
      this.uploadedImage = imageDataUrl
    },

    setAnalysisResult (result: AnalysisResult) {
      this.analysisResult = result
    },

    clearAnalysisResult () {
      this.analysisResult = null
      this.uploadedImage = null
    },

    updateSettings (newSettings: AppSettings) {
      this.host = newSettings.host
      this.port = newSettings.port
      this.user = newSettings.user
      this.password = newSettings.password
      // Save to localStorage (preserve locale setting)
      const currentSettings = loadSettingsFromStorage()
      saveSettingsToStorage({
        host: newSettings.host,
        port: newSettings.port,
        user: newSettings.user,
        password: newSettings.password,
        locale: currentSettings.locale,
      })
    },

    resetSettings () {
      // Clear localStorage
      try {
        localStorage.removeItem(SETTINGS_STORAGE_KEY)
      } catch (error) {
        console.warn('Failed to clear settings from localStorage:', error)
      }
      // Reset to default values
      this.host = defaultSettings.host
      this.port = defaultSettings.port
      this.user = defaultSettings.user
      this.password = defaultSettings.password
      this.locale = defaultSettings.locale
    },
  },
})
