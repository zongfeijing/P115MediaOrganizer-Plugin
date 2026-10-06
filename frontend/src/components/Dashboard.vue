<script setup lang="ts">
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
  <section class="p115-dashboard">
    <b>115 云端媒体整理</b>
    <p v-if="error">{{ error }}</p>
    <template v-if="state"
      ><p>{{ state.task.message }}</p>
      <p>
        待执行 {{ state.plan.executable }} · {{ state.connection.message }}
      </p></template
    >
  </section>
</template>
<style scoped>
.p115-dashboard {
  padding: 12px;
  line-height: 1.6;
}
.p115-dashboard p {
  margin: 5px 0;
  overflow-wrap: anywhere;
}
</style>
