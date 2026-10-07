<script setup lang="ts">
import { icons } from "../icons";
import { onMounted, ref } from "vue";
import { client, type HostProps } from "../api";
const props = defineProps<HostProps>();
const state = ref<any>(null),
  error = ref("");
onMounted(async () => {
  try {
    state.value = await client(props).get("workflow");
  } catch (e: any) {
    error.value = e.message;
  }
});
</script>
<template>
  <section class="p115-dashboard pa-4">
    <div class="d-flex align-center ga-2 mb-3">
      <VIcon
        :icon="icons.mdiCloudCheckOutline"
        color="primary"
        size="22"
      /><span class="text-subtitle-2">115 云端媒体整理</span>
    </div>
    <VAlert v-if="error" type="warning" variant="tonal" density="compact">{{
      error
    }}</VAlert>
    <template v-if="state"
      ><div class="d-flex align-center justify-space-between mb-2">
        <span class="text-caption text-medium-emphasis">待执行</span
        ><span class="text-h6 text-primary">{{ state.plan.executable }}</span>
      </div>
      <VChip
        size="x-small"
        variant="tonal"
        :color="state.connection.ok === true ? 'success' : 'warning'"
        >{{ state.connection.ok === true ? "连接正常" : "连接待检查" }}</VChip
      >
      <p class="text-caption text-medium-emphasis mt-3 p115-wrap">
        {{ state.task.message }}
      </p></template
    >
    <VProgressLinear v-else-if="!error" indeterminate color="primary" rounded />
  </section>
</template>
<style scoped>
.p115-dashboard {
  min-width: 0;
}
.p115-wrap {
  overflow-wrap: anywhere;
}
</style>
