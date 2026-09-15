<script setup lang="ts">
  import { reactive, watch } from 'vue'
  import { useI18n } from 'vue-i18n'
  import { useStore } from '@/stores/app'

  const { t } = useI18n()

  const props = defineProps<{
    modelValue: boolean
  }>()

  const emit = defineEmits<{
    (e: 'update:modelValue', value: boolean): void
  }>()

  const store = useStore()

  const metadata = reactive({
    image_id: '',
    patient_id: '',
    disorder_name: '',
    omim_id: '',
    mondo_id: '',
    gene_name: '',
    gene_entrez_id: '',
    notes: '',
  })

  function resetForm () {
    metadata.image_id = ''
    metadata.patient_id = ''
    metadata.disorder_name = ''
    metadata.omim_id = ''
    metadata.mondo_id = ''
    metadata.gene_name = ''
    metadata.gene_entrez_id = ''
    metadata.notes = ''
  }

  watch(() => props.modelValue, isVisible => {
    if (isVisible) {
      resetForm()
    }
  })

  function exportGalleryAddJson () {
    if (!store.analysisResult?.feature_vectors?.length) return

    const payload = {
      schema_hint: 'ngpsuite-gallery-add-experimental-v0',
      model_version: store.analysisResult.model_version,
      gallery_version: store.analysisResult.gallery_version,
      metadata: { ...metadata },
      feature_vectors: store.analysisResult.feature_vectors,
    }

    const jsonString = JSON.stringify(payload, null, 2)
    const blob = new Blob([jsonString], { type: 'application/json;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute('download', 'ngpsuite_gallery_add_experimental.json')
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
    max-width="560"
    :model-value="modelValue"
    persistent
    @update:model-value="emit('update:modelValue', $event)"
  >
    <v-card rounded="lg">
      <v-card-title>
        <span class="text-h5">{{ t('galleryAddDialog.title') }}</span>
      </v-card-title>
      <v-card-subtitle>{{ t('galleryAddDialog.subtitle') }}</v-card-subtitle>

      <v-card-text class="pt-4">
        <v-alert
          class="mb-4"
          density="compact"
          type="warning"
          variant="tonal"
        >
          {{ t('galleryAddDialog.experimentalNotice') }}
        </v-alert>

        <p class="text-overline">{{ t('galleryAddDialog.metadataTitle') }}</p>
        <p class="text-body-2 mb-4">{{ t('galleryAddDialog.metadataDescription') }}</p>

        <v-text-field
          v-model="metadata.image_id"
          density="compact"
          :label="t('galleryAddDialog.fields.imageId')"
          variant="outlined"
        />
        <v-text-field
          v-model="metadata.patient_id"
          density="compact"
          :label="t('galleryAddDialog.fields.patientId')"
          variant="outlined"
        />
        <v-text-field
          v-model="metadata.disorder_name"
          density="compact"
          :label="t('galleryAddDialog.fields.disorderName')"
          variant="outlined"
        />
        <v-text-field
          v-model="metadata.omim_id"
          density="compact"
          :label="t('galleryAddDialog.fields.omimId')"
          variant="outlined"
        />
        <v-text-field
          v-model="metadata.mondo_id"
          density="compact"
          :label="t('galleryAddDialog.fields.mondoId')"
          variant="outlined"
        />
        <v-text-field
          v-model="metadata.gene_name"
          density="compact"
          :label="t('galleryAddDialog.fields.geneName')"
          variant="outlined"
        />
        <v-text-field
          v-model="metadata.gene_entrez_id"
          density="compact"
          :label="t('galleryAddDialog.fields.geneEntrezId')"
          variant="outlined"
        />
        <v-textarea
          v-model="metadata.notes"
          density="compact"
          :label="t('galleryAddDialog.fields.notes')"
          rows="2"
          variant="outlined"
        />

        <v-divider class="my-4" />

        <p class="text-overline">{{ t('galleryAddDialog.vectorsTitle') }}</p>
        <p class="text-body-2 mb-4">
          {{ t('galleryAddDialog.vectorsDescription') }}
        </p>
        <v-btn
          block
          color="success"
          :disabled="!store.analysisResult?.feature_vectors?.length"
          prepend-icon="mdi-code-json"
          @click="exportGalleryAddJson"
        >
          {{ t('galleryAddDialog.button') }}
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
