<script setup lang="ts">
  import { ref, watch } from 'vue'
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

  // Create local refs to hold the form data.
  // This prevents direct mutation of the Pinia store state.
  const localHost = ref('')
  const localPort = ref('')
  const localUser = ref('')
  const localPassword = ref('')

  // When the dialog is opened, copy the current settings from the store
  // to the local refs.
  watch(() => props.modelValue, isVisible => {
    if (isVisible) {
      localHost.value = store.host
      localPort.value = store.port
      localUser.value = store.user
      localPassword.value = store.password
    }
  })

  // This function is called when the "Save" button is clicked.
  // It commits the local changes to the Pinia store.
  function handleSaveChanges () {
    store.updateSettings({
      host: localHost.value,
      port: localPort.value,
      user: localUser.value,
      password: localPassword.value,
    })
    // Close the dialog after saving
    emit('update:modelValue', false)
  }

  // This function is called when the "Reset" button is clicked.
  // It resets settings to default values and clears localStorage.
  function handleResetSettings () {
    store.resetSettings()
    // Update local refs to reflect the reset values
    localHost.value = store.host
    localPort.value = store.port
    localUser.value = store.user
    localPassword.value = store.password
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
        <span class="text-h5">{{ t('settingsDialog.title') }}</span>
      </v-card-title>
      <v-card-subtitle>{{ t('settingsDialog.subtitle') }}</v-card-subtitle>

      <v-card-text class="pt-4">
        <p class="text-overline">{{ t('settingsDialog.apiServer') }}</p>
        <v-text-field
          v-model="localHost"
          density="compact"
          :label="t('settingsDialog.host')"
          placeholder="http://localhost/"
          prepend-inner-icon="mdi-server"
          variant="outlined"
        />
        <v-text-field
          v-model="localPort"
          density="compact"
          :label="t('settingsDialog.port')"
          placeholder="8000"
          prepend-inner-icon="mdi-ethernet-cable"
          variant="outlined"
        />

        <v-divider class="my-4" />

        <p class="text-overline">{{ t('settingsDialog.auth') }}</p>
        <v-text-field
          v-model="localUser"
          density="compact"
          :label="t('settingsDialog.user')"
          placeholder="your_username"
          prepend-inner-icon="mdi-account"
          variant="outlined"
        />
        <v-text-field
          v-model="localPassword"
          density="compact"
          :label="t('settingsDialog.password')"
          placeholder="your_password"
          prepend-inner-icon="mdi-key-variant"
          type="password"
          variant="outlined"
        />
      </v-card-text>

      <v-card-actions>
        <v-btn
          color="error"
          :text="t('common.reset')"
          variant="text"
          @click="handleResetSettings"
        />
        <v-spacer />
        <v-btn
          :text="t('common.cancel')"
          @click="emit('update:modelValue', false)"
        />
        <v-btn
          color="primary"
          :text="t('common.save')"
          variant="flat"
          @click="handleSaveChanges"
        />
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
