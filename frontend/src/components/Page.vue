<script setup lang="ts">
import { icons } from "../icons";
import { computed, inject, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { client, stateLabels, type HostProps } from "../api";
import RecordList from "./RecordList.vue";
const props = defineProps<HostProps>();
const emit = defineEmits(["action", "switch", "close"]);
const api = client(props);
const confirm = inject<((options: any) => Promise<boolean>) | null>(
  "moviepilot:confirm",
  null,
);
const workflow = ref<any>(null),
  records = ref<any[]>([]),
  pagination = ref<any>({ page: 1, total_pages: 1, total: 0 });
const error = ref(""),
  loading = ref(false),
  submitting = ref(false),
  prepared = ref<any>(null);
const kind = ref("plan"),
  filter = ref(""),
  query = ref(""),
  page = ref(1);
let timer: ReturnType<typeof setTimeout> | undefined,
  searchTimer: ReturnType<typeof setTimeout> | undefined;
let generation = 0,
  stopped = false;
const valid = computed(() => workflow.value?.configuration?.valid);
const busy = computed(() => workflow.value?.busy);
const currentPlan = computed(() => workflow.value?.plan);
const result = computed(() => workflow.value?.last_result);
const progress = computed(() => {
  const t = workflow.value?.task;
  return t?.total
    ? Math.min(100, Math.round((100 * t.completed) / t.total))
    : null;
});
async function loadRecords() {
  const id = ++generation;
  try {
    const data = await api.get("records", {
      kind: kind.value,
      status: filter.value,
      query: query.value || "",
      page: page.value,
      page_size: 20,
    });
    if (id === generation && !stopped) {
      records.value = data.items;
      pagination.value = data.pagination;
    }
  } catch (e: any) {
    if (id === generation) error.value = e.message || "无法读取记录";
  }
}
async function refresh() {
  loading.value = true;
  try {
    workflow.value = await api.get("workflow");
    await loadRecords();
  } catch (e: any) {
    error.value = e.message || "无法读取插件状态";
  } finally {
    loading.value = false;
  }
}
async function poll() {
  await refresh();
  if (!stopped) timer = setTimeout(poll, busy.value ? 2000 : 10000);
}
async function run(action: string, body: any = {}) {
  submitting.value = true;
  error.value = "";
  try {
    await api.post(action, body);
    await refresh();
  } catch (e: any) {
    error.value = e.message || "操作失败";
  } finally {
    submitting.value = false;
  }
}
const connectionDetails = ref(false);
const tabs = [
  { value: "plan", title: "本次预览" },
  { value: "history", title: "整理历史" },
  { value: "runs", title: "执行批次" },
  { value: "scan", title: "扫描诊断" },
];
const statusOptions = [
  { title: "全部状态", value: "" },
  { title: "待执行", value: "planned" },
  { title: "已执行", value: "executed" },
  { title: "失败", value: "failed" },
  { title: "跳过", value: "skipped" },
  { title: "已停止", value: "cancelled" },
];
const connectionColor = computed(() =>
  workflow.value?.connection?.ok === true
    ? "success"
    : ["login", "dependency"].includes(workflow.value?.connection?.kind)
      ? "error"
      : "warning",
);
const connectionLabel = computed(() =>
  workflow.value?.connection?.ok === true
    ? "连接正常"
    : ["login", "dependency"].includes(workflow.value?.connection?.kind)
      ? "连接不可用"
      : "连接待检查",
);
const hasPlan = computed(() => currentPlan.value?.valid);
const canMutate = computed(() => !busy.value && !submitting.value);
async function primaryAction() {
  if (hasPlan.value) await prepare();
  else await run("tasks/start", { kind: "scan" });
}
async function prepare() {
  submitting.value = true;
  error.value = "";
  try {
    prepared.value = await api.post("execute/prepare");
    if (confirm) {
      const p = prepared.value;
      const ok = await confirm({
        type: "warn",
        title: "确认云端整理",
        content: `将执行 ${p.count} 个文件（含失败重试 ${p.retry_count} 个），跳过 ${p.skip_count} 个。${p.delete_empty_dirs ? "会清理成功整理来源中的空目录。" : "不清理空目录。"}目标：${p.targets.join("、")}。已开始的移动无法一键撤销。`,
        confirmText: "确认执行",
        cancelText: "取消",
      });
      if (ok) await execute();
      else prepared.value = null;
    }
  } catch (e: any) {
    error.value = e.message || "无法取得执行摘要";
  } finally {
    submitting.value = false;
  }
}
async function execute() {
  if (!prepared.value) return;
  const token = prepared.value.token;
  prepared.value = null;
  await run("execute/confirm", { token });
}
watch([kind, filter], () => {
  page.value = 1;
  void loadRecords();
});
watch(query, () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    page.value = 1;
    void loadRecords();
  }, 300);
});
watch(page, () => {
  void loadRecords();
});
onMounted(() => {
  void poll();
});
onBeforeUnmount(() => {
  stopped = true;
  clearTimeout(timer);
  clearTimeout(searchTimer);
  generation++;
});
function timeLabel(epoch: number) {
  return epoch ? new Date(epoch * 1000).toLocaleString("zh-CN") : "—";
}
</script>
<template>
  <section class="p115-page pa-4 pa-sm-6">
    <div class="d-flex align-center ga-3 mb-4">
      <VAvatar color="primary" variant="tonal" rounded="lg" size="42"
        ><VIcon :icon="icons.mdiCloudCheckOutline"
      /></VAvatar>
      <div class="flex-grow-1 min-width-0">
        <h2 class="text-h6">115 云端媒体整理</h2>
        <div class="text-caption text-medium-emphasis">
          在云端整理媒体，不下载文件
        </div>
      </div>
      <VTooltip text="配置"
        ><template #activator="{ props: tip }"
          ><VBtn
            v-bind="tip"
            :icon="icons.mdiCogOutline"
            variant="text"
            color="secondary"
            size="small"
            aria-label="配置"
            :disabled="busy"
            @click="emit('switch')" /></template
      ></VTooltip>
      <VTooltip text="刷新状态"
        ><template #activator="{ props: tip }"
          ><VBtn
            v-bind="tip"
            :icon="icons.mdiRefresh"
            variant="text"
            color="secondary"
            size="small"
            aria-label="刷新状态"
            :loading="loading"
            @click="refresh" /></template
      ></VTooltip>
      <VTooltip text="关闭"
        ><template #activator="{ props: tip }"
          ><VBtn
            v-bind="tip"
            :icon="icons.mdiClose"
            variant="text"
            color="secondary"
            size="small"
            aria-label="关闭"
            @click="emit('close')" /></template
      ></VTooltip>
    </div>
    <VAlert
      v-if="error"
      type="error"
      variant="tonal"
      density="compact"
      class="mb-4"
      closable
      role="alert"
      @click:close="error = ''"
      >{{ error }}</VAlert
    >
    <template v-if="workflow">
      <VAlert
        v-if="!valid"
        type="warning"
        variant="tonal"
        density="compact"
        class="mb-4"
        role="alert"
      >
        <div class="font-weight-medium">完成配置后再生成预览</div>
        <ul class="ps-4 my-2">
          <li v-for="e in workflow.configuration.errors" :key="e">{{ e }}</li>
        </ul>
        <VBtn size="small" variant="tonal" @click="emit('switch')">去配置</VBtn>
      </VAlert>
      <div class="d-flex align-center flex-wrap ga-2 mb-4">
        <VChip
          :color="connectionColor"
          size="small"
          variant="tonal"
          :prepend-icon="
            workflow.connection.ok === true
              ? icons.mdiCheckCircleOutline
              : icons.mdiCloudAlertOutline
          "
          >{{ connectionLabel }}</VChip
        >
        <VChip
          size="small"
          color="secondary"
          variant="tonal"
          :prepend-icon="icons.mdiCalendarClock"
          >{{
            workflow.configuration.preview_only ? "定时仅预览" : "定时自动执行"
          }}</VChip
        >
        <VSpacer />
        <VBtn
          size="small"
          color="secondary"
          variant="text"
          :append-icon="
            connectionDetails ? icons.mdiChevronUp : icons.mdiChevronDown
          "
          @click="connectionDetails = !connectionDetails"
          >连接详情</VBtn
        >
      </div>
      <VAlert
        v-if="
          ['login', 'dependency', 'network', 'rate_limit'].includes(
            workflow.connection.kind,
          )
        "
        :type="connectionColor === 'error' ? 'error' : 'warning'"
        variant="tonal"
        density="compact"
        class="mb-4"
        >{{ workflow.connection.message }}</VAlert
      >
      <VCard v-if="connectionDetails" variant="tonal" class="mb-4">
        <VCardText class="pa-4">
          <div class="text-body-2 mb-2">{{ workflow.connection.message }}</div>
          <div class="text-caption text-medium-emphasis mb-3">
            {{
              workflow.configuration.cookie_mode === "text"
                ? "使用 Cookie 文本"
                : "使用 Cookie 文件"
            }}
            · 客户端 {{ workflow.versions.p115client || "未安装" }} · 并发库
            {{ workflow.versions["python-concurrenttools"] || "未安装" }}
          </div>
          <div
            v-for="r in workflow.path_checks || []"
            :key="r.path"
            class="d-flex align-start ga-2 mb-2 text-body-2"
          >
            <VIcon
              :icon="
                r.ok ? icons.mdiCheckCircleOutline : icons.mdiAlertCircleOutline
              "
              :color="r.ok ? 'success' : 'warning'"
              size="18"
            /><span class="p115-path">{{ r.path }} {{ r.message || "" }}</span>
          </div>
          <VBtn
            variant="tonal"
            size="small"
            :prepend-icon="icons.mdiConnection"
            :disabled="!valid || !canMutate"
            :loading="submitting"
            @click="run('tasks/start', { kind: 'check' })"
            >检查连接与目录</VBtn
          >
        </VCardText>
      </VCard>
      <VRow dense class="mb-4">
        <VCol cols="4"
          ><div class="p115-stat">
            <div class="text-caption text-medium-emphasis">待执行</div>
            <div class="text-h5 text-primary">
              {{ currentPlan?.executable || 0 }}
            </div>
          </div></VCol
        >
        <VCol cols="4"
          ><div class="p115-stat">
            <div class="text-caption text-medium-emphasis">已完成</div>
            <div class="text-h5">{{ currentPlan?.counts?.executed || 0 }}</div>
          </div></VCol
        >
        <VCol cols="4"
          ><div class="p115-stat">
            <div class="text-caption text-medium-emphasis">需处理</div>
            <div
              class="text-h5"
              :class="currentPlan?.counts?.failed || 0 ? 'text-warning' : ''"
            >
              {{ currentPlan?.counts?.failed || 0 }}
            </div>
          </div></VCol
        >
      </VRow>
      <div class="d-flex flex-wrap align-center ga-2 mb-2">
        <VBtn
          color="primary"
          variant="flat"
          :prepend-icon="
            hasPlan ? icons.mdiPlayOutline : icons.mdiFileSearchOutline
          "
          :loading="submitting"
          :disabled="!valid || !canMutate"
          @click="primaryAction"
          >{{
            hasPlan
              ? `确认执行 ${currentPlan.executable} 个文件`
              : currentPlan?.count
                ? "重新生成预览"
                : "生成预览"
          }}</VBtn
        >
        <VBtn
          v-if="hasPlan"
          variant="tonal"
          color="secondary"
          :prepend-icon="icons.mdiRefresh"
          :disabled="!canMutate"
          @click="run('tasks/start', { kind: 'scan' })"
          >重新生成预览</VBtn
        >
        <span v-if="!valid" class="text-caption text-medium-emphasis"
          >配置 → 预览 → 确认</span
        >
      </div>
      <p
        v-if="currentPlan?.count && !currentPlan.valid"
        class="text-caption text-medium-emphasis mb-4"
      >
        {{ currentPlan.reason }}
      </p>
      <p
        v-else-if="currentPlan?.valid"
        class="text-caption text-medium-emphasis mb-4"
      >
        生成于 {{ currentPlan.created_at }} · 有效至
        {{
          timeLabel(currentPlan.expires_at)
        }}。执行全部有效项目，不仅是当前页。
      </p>
      <p v-else class="text-caption text-medium-emphasis mb-4">
        先生成预览，核对名称与目标目录，再确认执行。
      </p>
      <VCard
        v-if="prepared && !confirm"
        variant="tonal"
        color="warning"
        class="mb-4"
        role="alertdialog"
        aria-label="执行确认"
      >
        <VCardText
          ><div class="text-subtitle-1 font-weight-medium mb-2">执行前确认</div>
          <p>
            执行 {{ prepared.count }} 个文件，含失败重试
            {{ prepared.retry_count }} 个；跳过 {{ prepared.skip_count }} 个。
          </p>
          <p class="p115-path mt-2">
            目标：{{ prepared.targets.join("、") }}。{{
              prepared.delete_empty_dirs
                ? "将清理成功整理来源中的空目录。"
                : "不清理空目录。"
            }}
          </p>
          <p class="text-caption mt-2">
            已开始的移动无法一键撤销；定时运行模式不会改变。
          </p></VCardText
        >
        <VCardActions
          ><VSpacer /><VBtn
            variant="text"
            color="secondary"
            @click="prepared = null"
            >取消</VBtn
          ><VBtn
            color="primary"
            variant="flat"
            :loading="submitting"
            @click="execute"
            >我已核对，确认执行</VBtn
          ></VCardActions
        >
      </VCard>
      <VCard
        v-if="busy || ['failed', 'cancelled'].includes(workflow.task.status)"
        variant="tonal"
        class="mb-4"
        aria-live="polite"
      >
        <VCardText
          ><div class="d-flex align-center ga-2 mb-2">
            <VChip
              size="small"
              :color="workflow.task.status === 'failed' ? 'error' : 'primary'"
              >{{
                stateLabels[workflow.task.status] || workflow.task.status
              }}</VChip
            ><span class="text-body-2 p115-path">{{
              workflow.task.message
            }}</span>
          </div>
          <VProgressLinear
            v-if="busy"
            :model-value="progress || 0"
            :indeterminate="progress === null"
            color="primary"
            rounded
            height="6"
            class="my-3"
            :aria-label="`任务进度 ${progress ?? 0}%`"
          />
          <div class="d-flex flex-wrap align-center ga-2">
            <span class="text-caption text-medium-emphasis"
              >最近活动 {{ timeLabel(workflow.task.updated_at)
              }}{{
                workflow.task.discovered
                  ? ` · 已检查 ${workflow.task.discovered} 条`
                  : ""
              }}</span
            ><VSpacer /><VBtn
              v-if="busy"
              variant="text"
              color="warning"
              size="small"
              :prepend-icon="icons.mdiStopCircleOutline"
              :disabled="submitting || workflow.task.status === 'stopping'"
              @click="run('tasks/stop')"
              >完成当前批次后停止</VBtn
            >
          </div>
          <div v-if="busy" class="text-caption text-medium-emphasis mt-2">
            可关闭页面，任务仍在后台运行；停止会保留已完成项目。
          </div>
        </VCardText>
      </VCard>
      <div
        v-else-if="workflow.task.status === 'completed'"
        class="text-caption text-medium-emphasis mb-4"
      >
        <VIcon
          :icon="icons.mdiCheckCircleOutline"
          color="success"
          size="16"
          class="me-1"
        />{{ workflow.task.message }}
      </div>
      <VAlert
        v-if="workflow.scan_summary.limit_reached"
        type="info"
        variant="tonal"
        density="compact"
        class="mb-4"
        >本次达到扫描上限，后面的文件可能尚未检查；整理后可再次生成预览。</VAlert
      >
      <VTabs v-model="kind" density="comfortable" show-arrows class="mb-4"
        ><VTab v-for="tab in tabs" :key="tab.value" :value="tab.value">{{
          tab.title
        }}</VTab></VTabs
      >
      <VRow dense class="mb-3"
        ><VCol cols="12" sm="8"
          ><VTextField
            v-model="query"
            density="compact"
            label="搜索记录"
            placeholder="文件名、路径、错误或批次 ID"
            :prepend-inner-icon="icons.mdiMagnify"
            clearable
            hide-details
            @click:clear="query = ''" /></VCol
        ><VCol cols="12" sm="4"
          ><VSelect
            v-model="filter"
            :items="statusOptions"
            label="状态"
            density="compact"
            hide-details /></VCol
      ></VRow>
      <VExpansionPanels
        v-if="kind === 'scan' && workflow.scan_summary.record_count"
        variant="accordion"
        class="mb-4"
        ><VExpansionPanel title="扫描统计"
          ><VExpansionPanelText
            ><div class="d-flex flex-wrap ga-2 mb-2">
              <VChip
                v-for="(count, reason) in workflow.scan_summary.counts"
                :key="reason"
                size="small"
                variant="tonal"
                >{{ reason }} · {{ count }}</VChip
              >
            </div>
            <p class="text-caption text-medium-emphasis">
              诊断最多保留 5000 条，汇总计数覆盖全部。
            </p></VExpansionPanelText
          ></VExpansionPanel
        ></VExpansionPanels
      >
      <RecordList :records="records" :kind="kind" />
      <div
        class="p115-pagination d-flex flex-wrap align-center justify-center ga-2 mt-4"
      >
        <span class="text-caption text-medium-emphasis"
          >共 {{ pagination.total }} 条 · 第 {{ pagination.page }} /
          {{ pagination.total_pages || 1 }} 页</span
        ><VPagination
          v-model="page"
          :length="pagination.total_pages || 1"
          :total-visible="3"
          density="compact"
          :disabled="loading"
          aria-label="记录分页"
        />
      </div>
      <div v-if="result?.run_id" class="text-caption text-medium-emphasis mt-4">
        上次执行：成功 {{ result.success }} · 失败 {{ result.failed }} · 跳过
        {{ result.skipped }} · 剩余 {{ result.remaining || 0 }}
      </div>
    </template>
    <div v-else class="d-flex align-center justify-center ga-3 py-10">
      <VProgressCircular
        indeterminate
        size="24"
        width="2"
        color="primary"
      /><span class="text-body-2 text-medium-emphasis">正在读取插件状态…</span>
    </div>
  </section>
</template>
<style scoped>
.p115-page {
  max-width: 1100px;
  margin: auto;
  min-width: 0;
}
.min-width-0 {
  min-width: 0;
}
.p115-path {
  overflow-wrap: anywhere;
  word-break: break-word;
}
.p115-stat {
  padding: 8px 12px;
  border-inline-start: 2px solid rgba(var(--v-theme-primary), 0.25);
}
.p115-pagination {
  min-width: 0;
}
</style>
