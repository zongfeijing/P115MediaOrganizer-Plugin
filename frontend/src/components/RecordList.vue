<script setup lang="ts">
import { icons } from "../icons";
import { stateLabels } from "../api";
defineProps<{ records: any[]; kind: string }>();
function label(row: any) {
  return stateLabels[row.status] || "记录";
}
function color(row: any) {
  return (
    (
      {
        executed: "success",
        failed: "error",
        skipped: "warning",
        planned: "primary",
        cancelled: "secondary",
      } as Record<string, string>
    )[row.status] || "secondary"
  );
}
function name(row: any) {
  return row.source_name || row.title || row.run_id || row.path_hint || "记录";
}
function note(row: any) {
  return row.reason || row.error || (row.warnings || []).join("；");
}
function identity(row: any) {
  return [
    row.title,
    row.year,
    row.media_type === "tv" && row.season ? `第 ${row.season} 季` : "",
    row.media_type === "tv" && row.episode ? `第 ${row.episode} 集` : "",
  ]
    .filter(Boolean)
    .join(" · ");
}
</script>
<template>
  <div v-if="records.length" class="p115-records">
    <VTable class="p115-desktop" density="compact" hover
      ><thead>
        <tr>
          <th>{{ kind === "runs" ? "执行批次" : "文件 / 识别结果" }}</th>
          <th>{{ kind === "runs" ? "执行结果" : "目标位置 / 提示" }}</th>
          <th>状态</th>
          <th>时间</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, index) in records" :key="index">
          <td class="p115-file">
            <div class="text-body-2 font-weight-medium">{{ name(row) }}</div>
            <div
              v-if="row.title && row.source_name"
              class="text-caption text-medium-emphasis mt-1"
            >
              {{ identity(row) }}
            </div>
            <div
              v-if="kind === 'scan' && row.path_hint"
              class="text-caption text-medium-emphasis mt-1"
            >
              {{ row.path_hint }}
            </div>
          </td>
          <td class="p115-target">
            <template v-if="kind === 'runs'"
              ><div class="text-body-2">
                成功 {{ row.success }} · 失败 {{ row.failed }} · 跳过
                {{ row.skipped }}
              </div></template
            ><template v-else
              ><div v-if="row.target_path" class="text-body-2">
                {{ row.target_path }}
              </div>
              <div v-else-if="row.target_name" class="text-body-2">
                {{ row.target_category }} / {{ row.target_name }}
              </div>
              <div
                v-if="note(row)"
                class="text-caption mt-1"
                :class="
                  row.status === 'failed'
                    ? 'text-error'
                    : 'text-medium-emphasis'
                "
              >
                {{ note(row) }}
              </div></template
            >
          </td>
          <td>
            <VChip :color="color(row)" size="x-small" variant="tonal">{{
              label(row)
            }}</VChip>
          </td>
          <td class="text-caption text-medium-emphasis p115-time">
            {{ row.time || row.created_at || "—" }}
          </td>
        </tr>
      </tbody></VTable
    >
    <div class="p115-mobile">
      <VCard
        v-for="(row, index) in records"
        :key="index"
        variant="tonal"
        class="mb-3"
        ><VCardText class="pa-3"
          ><div class="d-flex justify-space-between align-center ga-2 mb-2">
            <VChip :color="color(row)" size="x-small" variant="tonal">{{
              label(row)
            }}</VChip
            ><span class="text-caption text-medium-emphasis">{{
              row.time || row.created_at || ""
            }}</span>
          </div>
          <div class="text-body-2 font-weight-medium p115-wrap">
            {{ name(row) }}
          </div>
          <div
            v-if="row.title && row.source_name"
            class="text-caption text-medium-emphasis mt-1"
          >
            {{ identity(row) }}
          </div>
          <div
            v-if="row.target_path || row.target_name"
            class="text-caption p115-wrap mt-2"
          >
            <VIcon :icon="icons.mdiArrowRight" size="14" class="me-1" />{{
              row.target_path ||
              `${row.target_category || ""} / ${row.target_name}`
            }}
          </div>
          <div v-if="kind === 'runs'" class="text-body-2 mt-2">
            成功 {{ row.success }} · 失败 {{ row.failed }} · 跳过
            {{ row.skipped }}
          </div>
          <div
            v-if="note(row)"
            class="text-caption p115-wrap mt-2"
            :class="
              row.status === 'failed' ? 'text-error' : 'text-medium-emphasis'
            "
          >
            {{ note(row) }}
          </div></VCardText
        ></VCard
      >
    </div>
  </div>
  <VSheet v-else rounded="lg" class="pa-8 text-center"
    ><VIcon
      :icon="icons.mdiFolderSearchOutline"
      color="secondary"
      size="32"
      class="mb-3"
    />
    <div class="text-body-2 text-medium-emphasis">暂无符合条件的记录</div>
    <div class="text-caption text-medium-emphasis mt-1">
      可以切换记录类型或清除筛选。
    </div></VSheet
  >
</template>
<style scoped>
.p115-records {
  min-width: 0;
}
.p115-desktop {
  border-radius: 8px;
}
.p115-file {
  width: 30%;
  min-width: 180px;
  padding-block: 12px !important;
  overflow-wrap: anywhere;
}
.p115-target {
  width: 45%;
  overflow-wrap: anywhere;
}
.p115-time {
  min-width: 125px;
}
.p115-wrap {
  overflow-wrap: anywhere;
  word-break: break-word;
}
.p115-mobile {
  display: none;
}
@media (max-width: 600px) {
  .p115-desktop {
    display: none;
  }
  .p115-mobile {
    display: block;
  }
}
</style>
