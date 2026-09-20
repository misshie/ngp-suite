<script setup lang="ts">
  import { useI18n } from 'vue-i18n'

  const { t } = useI18n()

  defineProps<{
    modelValue: boolean
  }>()

  const emit = defineEmits<{ (
    e: 'update:modelValue',
    value: boolean
  ): void
  }>()
</script>

<template>
  <v-dialog
    max-width="600"
    :model-value="modelValue"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <v-card class="text-center" rounded="lg">
      <v-card-text class="pa-6">
        <v-img
          class="mb-4 mx-auto"
          height="100"
          src="@/assets/NGPsuite-Avatar.png"
          style="max-width: 100px;"
        />

        <h2 class="text-h5 font-weight-bold mb-4">
          {{ t('aboutDialog.title') }}
        </h2>

        <div class="text-medium-emphasis mb-4 text-body-1">
          <p>
            {{ t('aboutDialog.programmedBy') }}
            <a href="https://github.com/misshie/" rel="noopener noreferrer" target="_blank">
              Hiroyuki Mishima
            </a>
          </p>
          <p>{{ t('aboutDialog.poweredBy') }}</p>
          <p
            class="text-body-2 text-left"
            v-html="t('aboutDialog.mondoAttribution')"
          />
        </div>

        <v-alert
          class="text-left"
          density="compact"
          type="warning"
          variant="tonal"
        >
          <div v-html="t('aboutDialog.disclaimer')" />
        </v-alert>

      </v-card-text>

      <v-divider />

      <v-card-actions class="pa-4">
        <v-spacer />
        <v-btn
          class="text-none"
          color="primary"
          min-width="90"
          :text="t('common.ok')"
          variant="flat"
          @click="emit('update:modelValue', false)"
        />
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
