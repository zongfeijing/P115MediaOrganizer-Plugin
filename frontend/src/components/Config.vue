<script setup lang="ts">
import { icons } from "../icons";
import { computed, inject, onMounted, ref } from "vue";
import { client, type HostProps } from "../api";
const props = defineProps<
  HostProps & { initialConfig?: Record<string, any> }
>();
const emit = defineEmits(["save", "close", "switch"]);
const api = client(props);
const config = ref<Record<string, any>>({
  enabled: false,
  notify: true,
  onlyonce: false,
  cron: "",
  dry_run: true,
  delete_empty_source_dirs: true,
  refresh_plex_after_execute: true,
  allow_external_execute: false,
  max_depth: 5,
  max_items_per_run: 200,
  min_file_size_mb: 100,
  batch_size: 30,
  sleep_between_batches: 1,
  plan_ttl_hours: 24,
  min_request_interval_ms: 300,
  max_retries: 3,
  retry_base_seconds: 1.5,
  jitter_ratio: 0.3,
  list_page_size: 200,
  history_limit: 1000,
  run_limit: 100,
  cookie_path: "/config/115-cookies.txt",
  cookie_text: "",
  exclude_keywords: "sample,trailer,花絮,预告",
  category_mapping: JSON.stringify({ movie: {}, tv: {} }, null, 2),
  target_cids: JSON.stringify(
    {
      movie: { 动画电影: "", 外语电影: "", 华语电影: "" },
      tv: { 未分类: "", 综艺: "", 日韩剧: "", 欧美剧: "", 国产剧: "" },
      unrecognized: "",
    },
    null,
    2,
  ),
  ...props.initialConfig,
});
config.value.cookie_mode ||= config.value.cookie_text ? "text" : "file";
const sources = ref<any[]>([]),
  errors = ref<string[]>([]),
  validating = ref(false),
  checked = ref(false);
const browser = ref<{
  index: number;
  field: string;
  path: string;
  items: any[];
  message: string;
} | null>(null);
const tab = ref("connection");
const revealCookie = ref(false);
const rawSources = ref(String(config.value.source_mappings || "[]"));
const hostConfirm = inject<((options: any) => Promise<boolean>) | null>(
  "moviepilot:confirm",
  null,
);
const deleteIndex = ref<number | null>(null);
const autoExecutePending = ref(false);
const connectionOptions = [
  { title: "粘贴 Cookie", value: "text" },
  { title: "使用 Cookie 文件", value: "file" },
];
const mediaOptions = [
  { title: "电影", value: "movie" },
  { title: "电视剧", value: "tv" },
];
const conflictOptions = [
  { title: "跳过，不覆盖", value: "skip" },
  { title: "自动添加后缀", value: "rename_with_suffix" },
];
const unrecognizedOptions = [
  { title: "跳过并显示原因", value: "skip" },
  { title: "移动到未识别目录 CID", value: "move_to_unrecognized" },
];
const scheduleOptions = [
  { title: "不自动运行", value: "" },
  { title: "每天凌晨 3 点", value: "0 3 * * *" },
  { title: "每 6 小时", value: "0 */6 * * *" },
  { title: "每周日凌晨 3 点", value: "0 3 * * 0" },
];
const batchFields = [
  { key: "batch_size", label: "批大小", min: 1, max: 100, step: 1 },
  {
    key: "sleep_between_batches",
    label: "批间隔（秒）",
    min: 0,
    max: 120,
    step: 0.1,
  },
  {
    key: "plan_ttl_hours",
    label: "计划有效期（小时）",
    min: 1,
    max: 720,
    step: 1,
  },
];
const rateFields = [
  {
    key: "min_request_interval_ms",
    label: "请求间隔（毫秒）",
    min: 0,
    max: 60000,
    step: 1,
  },
  { key: "max_retries", label: "重试次数", min: 0, max: 10, step: 1 },
  {
    key: "retry_base_seconds",
    label: "退避基数（秒）",
    min: 0.1,
    max: 120,
    step: 0.1,
  },
  { key: "jitter_ratio", label: "抖动比例", min: 0, max: 1, step: 0.1 },
  { key: "list_page_size", label: "目录分页大小", min: 50, max: 1000, step: 1 },
  { key: "history_limit", label: "历史保留条数", min: 1, step: 1 },
];
async function removeSource(index: number) {
  if (hostConfirm) {
    if (
      await hostConfirm({
        type: "warn",
        title: "移除来源",
        content: "仅删除此来源配置，不会删除网盘文件。",
        confirmText: "移除",
        cancelText: "取消",
      })
    )
      sources.value.splice(index, 1);
  } else deleteIndex.value = index;
}
async function setRunMode(previewOnly: boolean) {
  if (previewOnly) {
    config.value.dry_run = true;
    return;
  }
  if (config.value.dry_run === false) return;
  if (hostConfirm) {
    if (
      await hostConfirm({
        type: "warn",
        title: "开启自动执行",
        content:
          "定时或立即运行任务将自动移动和重命名文件，不会逐次弹出确认。请先用少量测试文件验证目录与规则。",
        confirmText: "开启自动执行",
        cancelText: "保持仅预览",
      })
    )
      config.value.dry_run = false;
  } else autoExecutePending.value = true;
}
const mode = ref<"visual" | "json">("visual"),
  browsersLoading = ref(false);
try {
  const rows =
    typeof config.value.source_mappings === "string"
      ? JSON.parse(config.value.source_mappings || "[]")
      : config.value.source_mappings || [];
  if (!Array.isArray(rows)) throw new Error();
  sources.value = rows.map((row: any) =>
    row && typeof row === "object" && !Array.isArray(row) ? row : {},
  );
} catch {
  mode.value = "json";
  errors.value = ["旧来源映射 JSON 无效，请修正后再切换到可视化编辑"];
}
const canSave = computed(
  () =>
    !validating.value &&
    !browser.value &&
    !autoExecutePending.value &&
    deleteIndex.value === null,
);
function payload() {
  return {
    ...config.value,
    source_mappings:
      mode.value === "json" ? rawSources.value : JSON.stringify(sources.value),
  };
}
function add() {
  sources.value.push({
    name: `来源 ${sources.value.length + 1}`,
    media_type: "movie",
    source_path: "",
    target_root_path: "",
  });
}
function switchMode() {
  if (mode.value === "visual") {
    rawSources.value = JSON.stringify(sources.value, null, 2);
    mode.value = "json";
    return;
  }
  try {
    const rows = JSON.parse(rawSources.value);
    if (!Array.isArray(rows)) throw new Error("必须是数组");
    sources.value = rows.map((row: any) =>
      row && typeof row === "object" && !Array.isArray(row) ? row : {},
    );
    mode.value = "visual";
    errors.value = [];
  } catch {
    errors.value = ["来源映射必须是有效的 JSON 数组"];
  }
}
async function validate(save = false) {
  if (!canSave.value) return;
  validating.value = true;
  checked.value = false;
  errors.value = [];
  try {
    const data = await api.post("validate_config", { config: payload() });
    errors.value = data.errors || [];
    checked.value = data.valid;
    if (save && data.valid) emit("save", payload());
    if (!data.valid) tab.value = "connection";
  } catch (e: any) {
    errors.value = e.details?.errors || [e.message || "配置检查失败"];
    tab.value = "connection";
  } finally {
    validating.value = false;
  }
}
async function openBrowser(index: number, field: string) {
  browser.value = {
    index,
    field,
    path: sources.value[index][field] || "/",
    items: [],
    message: "",
  };
  await browse(browser.value.path);
}
async function browse(path: string) {
  if (!browser.value) return;
  const selection = browser.value;
  browsersLoading.value = true;
  browser.value.message = "";
  try {
    // The live plugin uses the saved connection, not unsaved cookie text. No cookie is sent to list_dir.
    const data = await api.post("list_dir", { path });
    if (browser.value === selection) {
      browser.value.path = path;
      browser.value.items = data.items.filter((r: any) => r.is_dir);
    }
  } catch (e: any) {
    if (browser.value === selection)
      browser.value.message = e.message || "目录读取失败";
  } finally {
    browsersLoading.value = false;
  }
}
function selectDirectory() {
  if (!browser.value) return;
  sources.value[browser.value.index][browser.value.field] = browser.value.path;
  browser.value = null;
}
function child(name: string) {
  return `${browser.value?.path.replace(/\/$/, "")}/${name}`;
}
function parent() {
  const parts = (browser.value?.path || "/").split("/").filter(Boolean);
  parts.pop();
  return "/" + parts.join("/");
}
onMounted(() => {
  if (!sources.value.length && mode.value === "visual") add();
});
</script>
<template>
  <VForm class="p115-config" @submit.prevent="validate(true)">
    <div class="px-4 px-sm-6 pt-5 pb-4 d-flex align-center ga-3">
      <VAvatar color="primary" variant="tonal" rounded="lg" size="42"
        ><VIcon :icon="icons.mdiTuneVariant"
      /></VAvatar>
      <div class="flex-grow-1 min-width-0">
        <h2 class="text-h6">配置云端整理</h2>
        <div class="text-caption text-medium-emphasis">
          先连接 115，再设置来源和运行方式
        </div>
      </div>
      <VBtn
        :icon="icons.mdiClose"
        variant="text"
        color="secondary"
        size="small"
        aria-label="关闭配置"
        @click="emit('close')"
      />
    </div>
    <VTabs v-model="tab" class="px-4 px-sm-6" show-arrows
      ><VTab value="connection" :prepend-icon="icons.mdiFolderCogOutline"
        >连接与目录</VTab
      ><VTab value="automation" :prepend-icon="icons.mdiCalendarClock"
        >自动化</VTab
      ><VTab value="advanced" :prepend-icon="icons.mdiTune">高级</VTab></VTabs
    >
    <VDivider />
    <div class="pa-4 pa-sm-6">
      <VAlert
        v-if="errors.length"
        type="error"
        variant="tonal"
        density="compact"
        role="alert"
        class="mb-4"
        ><ul class="ps-4">
          <li v-for="e in errors" :key="e">{{ e }}</li>
        </ul></VAlert
      >
      <VAlert
        v-if="checked"
        type="success"
        variant="tonal"
        density="compact"
        class="mb-4"
        >配置格式检查通过。保存后可在详情页检查实际连接与目录。</VAlert
      >
      <VWindow v-model="tab">
        <VWindowItem value="connection">
          <div class="text-subtitle-1 font-weight-medium mb-3">115 连接</div>
          <VRow
            ><VCol cols="12" sm="5"
              ><VSelect
                v-model="config.cookie_mode"
                :items="connectionOptions"
                label="连接方式"
                density="comfortable"
                hide-details /></VCol
            ><VCol cols="12" sm="7"
              ><VTextField
                v-if="config.cookie_mode === 'text'"
                v-model="config.cookie_text"
                :type="revealCookie ? 'text' : 'password'"
                label="Cookie 文本"
                autocomplete="off"
                :append-inner-icon="
                  revealCookie ? icons.mdiEyeOffOutline : icons.mdiEyeOutline
                "
                @click:append-inner="revealCookie = !revealCookie"
                hide-details /><VTextField
                v-else
                v-model="config.cookie_path"
                label="容器内 Cookie 文件路径"
                placeholder="/config/115-cookies.txt"
                :prepend-inner-icon="icons.mdiFileKeyOutline"
                hide-details /></VCol
          ></VRow>
          <p class="text-caption text-medium-emphasis mt-3 mb-6">
            只使用当前选择的方式。Cookie 不会出现在进度或诊断记录中。
          </p>
          <div class="d-flex align-center flex-wrap ga-2 mb-3">
            <div class="text-subtitle-1 font-weight-medium flex-grow-1">
              来源与目标
            </div>
            <VBtn
              variant="text"
              color="secondary"
              size="small"
              :prepend-icon="icons.mdiCodeJson"
              @click="switchMode"
              >{{ mode === "visual" ? "JSON 编辑" : "可视化编辑" }}</VBtn
            ><VBtn
              v-if="mode === 'visual'"
              variant="tonal"
              size="small"
              :prepend-icon="icons.mdiPlus"
              @click="add"
              >添加来源</VBtn
            >
          </div>
          <VTextarea
            v-if="mode === 'json'"
            v-model="rawSources"
            label="来源映射 JSON"
            rows="10"
            auto-grow
            class="p115-json"
          />
          <template v-else>
            <VCard
              v-for="(s, i) in sources"
              :key="i"
              variant="tonal"
              class="mb-4 p115-source"
            >
              <div class="d-flex align-center ga-2 px-4 pt-3">
                <VIcon
                  :icon="
                    s.media_type === 'tv'
                      ? icons.mdiTelevisionClassic
                      : icons.mdiMovieOutline
                  "
                  color="primary"
                  size="20"
                /><span class="text-subtitle-2 flex-grow-1">{{
                  s.name || `来源 ${i + 1}`
                }}</span
                ><VTooltip text="移除来源配置，不删除文件"
                  ><template #activator="{ props: tip }"
                    ><VBtn
                      v-bind="tip"
                      :icon="icons.mdiTrashCanOutline"
                      variant="text"
                      color="secondary"
                      size="small"
                      :aria-label="`移除来源 ${i + 1}`"
                      @click="removeSource(i)" /></template
                ></VTooltip>
              </div>
              <VCardText class="pt-2"
                ><VRow dense
                  ><VCol cols="12" sm="7"
                    ><VTextField
                      v-model="s.name"
                      label="名称"
                      density="compact"
                      hide-details /></VCol
                  ><VCol cols="12" sm="5"
                    ><VSelect
                      v-model="s.media_type"
                      :items="mediaOptions"
                      label="媒体类型"
                      density="compact"
                      hide-details
                  /></VCol>
                  <VCol cols="12"
                    ><VTextField
                      v-model="s.source_path"
                      label="115 待整理来源"
                      placeholder="/待整理/Movie"
                      :append-inner-icon="icons.mdiFolderOpenOutline"
                      density="compact"
                      hide-details
                      @click:append-inner="openBrowser(i, 'source_path')"
                  /></VCol>
                  <VCol cols="12"
                    ><VTextField
                      v-model="s.target_root_path"
                      label="目标媒体库根目录"
                      placeholder="/媒体库/Movie"
                      :append-inner-icon="icons.mdiFolderOpenOutline"
                      density="compact"
                      hide-details
                      @click:append-inner="openBrowser(i, 'target_root_path')"
                  /></VCol>
                </VRow>
                <div class="text-caption text-medium-emphasis mt-3">
                  目标不能位于任何来源目录内；分类目录需与 MP 分类匹配。
                </div></VCardText
              >
            </VCard>
            <VSheet v-if="!sources.length" rounded="lg" class="text-center pa-6"
              ><VIcon
                :icon="icons.mdiFolderPlusOutline"
                color="secondary"
                size="28"
              />
              <p class="text-body-2 mt-2 mb-3">添加一个待整理来源开始配置</p>
              <VBtn variant="tonal" :prepend-icon="icons.mdiPlus" @click="add"
                >添加来源</VBtn
              ></VSheet
            >
          </template>
          <VAlert
            v-if="deleteIndex !== null"
            type="warning"
            variant="tonal"
            class="mb-4"
            ><p class="text-body-2">移除此来源配置？不会删除网盘文件。</p>
            <div class="d-flex justify-end ga-2 mt-2">
              <VBtn variant="text" color="secondary" @click="deleteIndex = null"
                >取消</VBtn
              ><VBtn
                variant="tonal"
                color="warning"
                @click="
                  sources.splice(deleteIndex!, 1);
                  deleteIndex = null;
                "
                >确认移除</VBtn
              >
            </div></VAlert
          >
          <VCard
            v-if="browser"
            variant="outlined"
            class="p115-directory mb-4"
            role="region"
            aria-label="115 目录选择"
            ><VCardTitle class="d-flex align-center ga-2 text-subtitle-1"
              ><VIcon
                :icon="icons.mdiFolderOpenOutline"
                color="primary"
                size="20" /><span class="p115-wrap flex-grow-1">{{
                browser.path
              }}</span
              ><VBtn
                :icon="icons.mdiClose"
                size="small"
                color="secondary"
                variant="text"
                aria-label="取消目录选择"
                @click="browser = null" /></VCardTitle
            ><VCardText
              ><div class="text-caption text-medium-emphasis mb-3">
                使用已经保存的连接。首次配置可先填写路径并保存，再浏览目录。
              </div>
              <VAlert
                v-if="browser.message"
                type="warning"
                variant="tonal"
                density="compact"
                role="alert"
                class="mb-3"
                >{{ browser.message }}</VAlert
              ><VProgressLinear
                v-if="browsersLoading"
                indeterminate
                color="primary"
                class="mb-2" /><VList
                class="p115-directory-list"
                density="compact"
                bg-color="transparent"
                ><VListItem
                  v-for="d in browser.items"
                  :key="d.cid"
                  :title="d.name"
                  :prepend-icon="icons.mdiFolderOutline"
                  :append-icon="icons.mdiChevronRight"
                  :disabled="browsersLoading"
                  @click="browse(child(d.name))" /><VListItem
                  v-if="!browser.items.length && !browsersLoading"
                  title="暂无子目录" /></VList></VCardText
            ><VCardActions
              ><VBtn
                variant="text"
                color="secondary"
                :prepend-icon="icons.mdiArrowUp"
                :disabled="browsersLoading || browser.path === '/'"
                @click="browse(parent())"
                >上一级</VBtn
              ><VSpacer /><VBtn
                variant="tonal"
                :disabled="browsersLoading || !!browser.message"
                @click="selectDirectory"
                >使用当前目录</VBtn
              ></VCardActions
            ></VCard
          >
        </VWindowItem>
        <VWindowItem value="automation">
          <div class="text-subtitle-1 font-weight-medium mb-3">运行方式</div>
          <VRow dense
            ><VCol cols="12" sm="6"
              ><VSwitch v-model="config.enabled" label="启用定时服务" /></VCol
            ><VCol cols="12" sm="6"
              ><VSwitch v-model="config.notify" label="发送结果通知" /></VCol
          ></VRow>
          <VSelect
            :model-value="config.dry_run"
            :items="[
              { title: '仅生成预览（推荐）', value: true },
              { title: '生成后自动执行', value: false },
            ]"
            label="定时与立即运行模式"
            @update:model-value="setRunMode"
            hide-details
          />
          <div class="text-caption text-medium-emphasis mt-2 mb-4">
            手动执行始终需要确认摘要，无需关闭“仅生成预览”。
          </div>
          <VAlert
            v-if="config.dry_run === false"
            type="warning"
            variant="tonal"
            density="compact"
            class="mb-4"
            >自动运行会直接移动和重命名文件，不会逐次弹出确认。请先验证目录与规则。</VAlert
          >
          <VAlert
            v-if="autoExecutePending"
            type="warning"
            variant="tonal"
            class="mb-4"
            ><p class="text-body-2">
              开启自动执行后，定时或立即运行任务将直接移动和重命名文件。是否继续？
            </p>
            <div class="d-flex justify-end ga-2 mt-3">
              <VBtn
                variant="text"
                color="secondary"
                @click="autoExecutePending = false"
                >保持仅预览</VBtn
              ><VBtn
                variant="tonal"
                color="warning"
                @click="
                  config.dry_run = false;
                  autoExecutePending = false;
                "
                >开启自动执行</VBtn
              >
            </div></VAlert
          >
          <VRow
            ><VCol cols="12" sm="6"
              ><VSelect
                :items="scheduleOptions"
                label="常用运行时间"
                placeholder="选择后填入 CRON"
                @update:model-value="config.cron = $event"
                hide-details /></VCol
            ><VCol cols="12" sm="6"
              ><VTextField
                v-model="config.cron"
                label="五段 CRON"
                placeholder="0 3 * * *"
                hint="留空不自动运行"
                persistent-hint /></VCol
          ></VRow>
          <VSwitch
            v-model="config.onlyonce"
            label="保存后立即运行一次"
            hint="遵循上面的运行模式；仅预览模式不会自动执行"
            persistent-hint
            class="mb-4"
          />
          <VDivider class="my-5" />
          <div class="text-subtitle-1 font-weight-medium mb-3">整理策略</div>
          <VRow dense
            ><VCol cols="12" sm="6"
              ><VSwitch
                v-model="config.delete_empty_source_dirs"
                label="整理后清理空来源目录" /></VCol
            ><VCol cols="12" sm="6"
              ><VSwitch
                v-model="config.refresh_plex_after_execute"
                label="整理后刷新 Plex" /></VCol
            ><VCol cols="12" sm="6"
              ><VSelect
                v-model="config.conflict_strategy"
                :items="conflictOptions"
                label="重名策略"
                hide-details /></VCol
            ><VCol cols="12" sm="6"
              ><VSelect
                v-model="config.unrecognized_action"
                :items="unrecognizedOptions"
                label="无法识别的文件"
                hide-details /></VCol
            ><VCol cols="12" sm="4"
              ><VTextField
                v-model.number="config.max_items_per_run"
                type="number"
                label="单次最多文件"
                :min="0"
                :max="10000"
                hint="0 表示不限"
                persistent-hint /></VCol
            ><VCol cols="12" sm="4"
              ><VTextField
                v-model.number="config.min_file_size_mb"
                type="number"
                label="最小文件体积（MB）"
                :min="0"
                hide-details /></VCol
            ><VCol cols="12" sm="4"
              ><VTextField
                v-model.number="config.max_depth"
                type="number"
                label="扫描深度"
                :min="0"
                :max="30"
                hide-details /></VCol
          ></VRow>
        </VWindowItem>
        <VWindowItem value="advanced">
          <VAlert type="info" variant="tonal" density="compact" class="mb-4"
            >通常无需修改。CID 覆盖和分类别名只在高级场景使用。</VAlert
          >
          <VExpansionPanels variant="accordion" multiple>
            <VExpansionPanel title="目录与分类覆盖"
              ><VExpansionPanelText
                ><VTextarea
                  v-model="config.target_cids"
                  label="目标 CID 覆盖 JSON"
                  rows="5"
                  class="p115-json mb-3" /><VTextarea
                  v-model="config.category_mapping"
                  label="分类别名 JSON"
                  rows="4"
                  class="p115-json" /><VTextField
                  v-model="config.exclude_keywords"
                  label="排除关键词"
                  hint="逗号分隔"
                  persistent-hint
                  class="mt-3" /></VExpansionPanelText
            ></VExpansionPanel>
            <VExpansionPanel title="批次与有效期"
              ><VExpansionPanelText
                ><VRow dense
                  ><VCol
                    v-for="field in batchFields"
                    :key="field.key"
                    cols="12"
                    sm="4"
                    ><VTextField
                      v-model.number="config[field.key]"
                      :label="field.label"
                      type="number"
                      :min="field.min"
                      :max="field.max"
                      :step="field.step"
                      hide-details /></VCol></VRow></VExpansionPanelText
            ></VExpansionPanel>
            <VExpansionPanel title="请求节奏与历史"
              ><VExpansionPanelText
                ><VRow dense
                  ><VCol
                    v-for="field in rateFields"
                    :key="field.key"
                    cols="12"
                    sm="4"
                    ><VTextField
                      v-model.number="config[field.key]"
                      :label="field.label"
                      type="number"
                      :min="field.min"
                      :max="field.max"
                      :step="field.step"
                      hide-details /></VCol></VRow></VExpansionPanelText
            ></VExpansionPanel>
            <VExpansionPanel title="外部执行与 Plex"
              ><VExpansionPanelText
                ><VSwitch
                  v-model="config.allow_external_execute"
                  label="允许 API Key 外部自动执行"
                  hint="默认关闭；不会替代手动确认"
                  persistent-hint /><VCombobox
                  v-model="config.plex_mediaservers"
                  label="Plex 服务器名称"
                  multiple
                  chips
                  closable-chips
                  hint="留空刷新全部已配置 Plex 服务器"
                  persistent-hint
                  class="mt-4" /></VExpansionPanelText
            ></VExpansionPanel>
          </VExpansionPanels>
        </VWindowItem>
      </VWindow>
    </div>
    <div class="p115-config-footer">
      <VDivider /><VCardActions class="px-4 px-sm-6 py-3 ga-2"
        ><VBtn
          variant="text"
          color="secondary"
          :prepend-icon="icons.mdiArrowLeft"
          @click="emit('switch')"
          >查看详情</VBtn
        ><VSpacer /><VBtn
          variant="text"
          color="secondary"
          @click="emit('close')"
          >取消</VBtn
        ><VBtn
          color="primary"
          variant="flat"
          :prepend-icon="icons.mdiContentSaveOutline"
          :loading="validating"
          :disabled="!canSave"
          type="submit"
          >检查并保存</VBtn
        ></VCardActions
      >
    </div>
  </VForm>
</template>
<style scoped>
.p115-config {
  max-width: 1000px;
  margin: auto;
  min-width: 0;
}
.min-width-0 {
  min-width: 0;
}
.p115-wrap {
  overflow-wrap: anywhere;
  word-break: break-word;
}
.p115-source {
  min-width: 0;
}
.p115-directory-list {
  max-height: 260px;
  overflow: auto;
}
.p115-config-footer {
  position: sticky;
  bottom: 0;
  z-index: 1;
  background: rgb(var(--v-theme-surface));
}
.p115-json :deep(textarea) {
  font-family: ui-monospace, SFMono-Regular, monospace;
}
@media (max-width: 600px) {
  .p115-config-footer :deep(.v-card-actions) {
    flex-wrap: wrap;
  }
}
</style>
