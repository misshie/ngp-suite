<!-- eslint-disable unicorn/prefer-add-event-listener -->
<script setup lang="ts">
  import type { AnalysisResult } from '@/stores/app'
  import axios from 'axios'
  import FilePondPluginFileValidateType from 'filepond-plugin-file-validate-type'
  import FilePondPluginImagePreview from 'filepond-plugin-image-preview'
  import { ref, watch } from 'vue'
  import vueFilePond from 'vue-filepond'
  import { useI18n } from 'vue-i18n'
  import { useStore } from '@/stores/app'
  import 'filepond/dist/filepond.min.css'
  import 'filepond-plugin-image-preview/dist/filepond-plugin-image-preview.min.css'

  const { t } = useI18n()

  const props = defineProps<{
    modelValue: boolean
  }>()

  const emit = defineEmits<{ (
    e: 'update:modelValue',
    value: boolean
  ): void
  }>()

  const FilePond = vueFilePond(
    FilePondPluginFileValidateType,
    FilePondPluginImagePreview,
  )

  const pond = ref<any>(null)
  const isUploading = ref(false)

  // HPO Phenotypes related state
  const useHpo = ref(false)
  const hpoIds = ref('')
  const exampleHpos = 'HP:0007655,HP:0045075,HP:0000175,HP:0000750'

  const store = useStore()
  const uploadStatusKey = ref('')

  const uploadStatusMessage = computed(() => {
    return uploadStatusKey.value ? t(uploadStatusKey.value) : ''
  })

  function setExampleHpos () {
    hpoIds.value = exampleHpos
  }

  function preventBrowserDefaults (e: DragEvent) {
    e.preventDefault()
  }

  watch(() => props.modelValue, isVisible => {
    if (isVisible) {
      window.addEventListener('dragover', preventBrowserDefaults, false)
      window.addEventListener('drop', preventBrowserDefaults, false)
    } else {
      window.removeEventListener('dragover', preventBrowserDefaults, false)
      window.removeEventListener('drop', preventBrowserDefaults, false)
    }
  })

  watch(() => store.analysisResult, newResult => {
    if (newResult === null) {
      uploadStatusKey.value = 'analysisDialog.status.noFile'
      pond.value?.removeFiles()
      useHpo.value = false
      hpoIds.value = ''
    }
  })

  function processFile (file: File): Promise<{ dataUrl: string, base64: string }> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.readAsDataURL(file)
      reader.onload = () => {
        const dataUrl = reader.result as string
        const base64 = dataUrl.split(',')[1]
        resolve({ dataUrl, base64 })
      }
      reader.onerror = error => reject(error)
    })
  }

  async function uploadFile () {
    const fileItem = pond.value?.getFile()
    if (!fileItem) {
      uploadStatusKey.value = 'analysisDialog.status.noFile'
      return
    }

    isUploading.value = true
    uploadStatusKey.value = 'analysisDialog.status.uploading'

    try {
      const { dataUrl, base64 } = await processFile(fileItem.file)

      store.setUploadedImage(dataUrl)

      // Construct the payload
      const payload: { img: string, hpo_ids?: string[] } = {
        img: base64,
      }

      if (useHpo.value && hpoIds.value) {
        // Split by comma, semicolon, tab, or space (including newline), trim, filter empty
        payload.hpo_ids = hpoIds.value
          .split(/[,;\s]+/)
          .map(id => id.trim())
          .filter(Boolean)
      }

      const url = store.predictApiUri
      const config = {
        auth: {
          username: store.user,
          password: store.password,
        },
      }
      const response = await axios.post<AnalysisResult>(url, payload, config)
      store.setAnalysisResult(response.data)
      uploadStatusKey.value = 'analysisDialog.status.success'
      console.log('Succeeded:', response.data)
      setTimeout(() => {
        emit('update:modelValue', false)
      }, 1500)
    } catch (error) {
      uploadStatusKey.value = 'analysisDialog.status.failure'
      console.error(error)
    } finally {
      isUploading.value = false
    }
  }
</script>

<template>
  <v-dialog
    max-width="600"
    :model-value="modelValue"
    persistent
    @update:model-value="emit('update:modelValue', $event)"
  >
    <v-card rounded="lg">
      <v-overlay
        v-model="isUploading"
        class="align-center justify-center"
        contained
      >
        <v-progress-circular
          color="white"
          indeterminate
          size="64"
        />
      </v-overlay>

      <v-card-title>
        <span class="text-h5">{{ t('analysisDialog.title') }}</span>
      </v-card-title>

      <!-- Main content area -->
      <v-card-text>
        <file-pond
          ref="pond"
          accepted-file-types="image/jpeg, image/png"
          :allow-multiple="false"
          :label-idle="t('analysisDialog.labelIdle')"
          name="analysis"
        />

        <!-- HPO Phenotypes Section -->
        <v-checkbox v-model="useHpo" hide-details label="Use HPO phenotypes" />
        <v-expand-transition>
          <div v-if="useHpo" class="mt-4">
            <v-textarea
              v-model="hpoIds"
              auto-grow
              clearable
              :label="t('analysisDialog.inputHpoIdsLabel')"
              rows="2"
            >
              <template #append-inner>
                <v-btn size="small" variant="tonal" @click="setExampleHpos"> Example </v-btn>
              </template>
            </v-textarea>
          </div>
        </v-expand-transition>
      </v-card-text>

      <v-card-text v-if="uploadStatusKey" class="pt-0 text-center">
        <p>{{ uploadStatusMessage }}</p>
      </v-card-text>

      <v-card-actions>
        <v-spacer />

        <v-btn
          color="blue-darken-1"
          variant="text"
          @click="emit('update:modelValue', false)"
        >
          {{ t('common.cancel') }}
        </v-btn>

        <v-btn
          color="blue-darken-1"
          variant="text"
          @click="uploadFile"
        >
          {{ t('common.submit') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
