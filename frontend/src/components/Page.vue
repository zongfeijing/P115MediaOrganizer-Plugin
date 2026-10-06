<script setup lang="ts">
import { computed, inject, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { client, stateLabels, type HostProps } from "../api";
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
      query: query.value,
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
function name(row: any) {
  return row.source_name || row.title || row.run_id || row.path_hint || "记录";
}
function warnings(row: any) {
  return row.reason || row.error || (row.warnings || []).join("；");
}
function timeLabel(epoch: number) {
  return epoch ? new Date(epoch * 1000).toLocaleString("zh-CN") : "—";
}
</script>
<template>
  <section class="p115-page">
    <header class="p115-toolbar">
      <div>
        <h2>115 云端媒体整理</h2>
        <p>检查配置 → 生成预览 → 确认执行</p>
      </div>
      <button @click="emit('switch')" :disabled="busy">配置</button
      ><button @click="refresh" :disabled="loading">刷新</button>
    </header>
    <p v-if="error" class="p115-alert danger" role="alert">{{ error }}</p>
    <template v-if="workflow">
      <div class="p115-steps" aria-label="整理流程">
        <div :class="{ ready: valid }">
          <b>1. 配置检查</b
          ><span>{{ valid ? "配置格式通过" : "请先修正配置" }}</span>
        </div>
        <div :class="{ ready: currentPlan?.valid }">
          <b>2. 生成预览</b
          ><span
            >{{ currentPlan?.count || 0 }} 条 · 待执行
            {{ currentPlan?.executable || 0 }}</span
          >
        </div>
        <div><b>3. 确认执行</b><span>按确认摘要整理，定时模式不变</span></div>
      </div>
      <div v-if="!valid" class="p115-alert danger">
        <ul>
          <li v-for="e in workflow.configuration.errors" :key="e">{{ e }}</li>
        </ul>
        <button @click="emit('switch')">去修正配置</button>
      </div>
      <div
        class="p115-connection"
        :class="{
          'p115-alert': true,
          danger:
            workflow.connection.kind === 'login' ||
            workflow.connection.kind === 'dependency',
        }"
      >
        <b>{{
          workflow.connection.ok === true ? "115 连接正常" : "连接状态"
        }}</b>
        · {{ workflow.connection.message }}
        <small
          >当前使用：{{
            workflow.configuration.cookie_mode === "text"
              ? "Cookie 文本"
              : "Cookie 文件"
          }}
          · 客户端 {{ workflow.versions.p115client || "未安装" }} · 并发库
          {{ workflow.versions["python-concurrenttools"] || "未安装" }}</small
        >
      </div>
      <ul v-if="workflow.path_checks?.length" class="p115-paths">
        <li v-for="r in workflow.path_checks" :key="r.path">
          {{ r.ok ? "✓" : "✗" }} {{ r.path }} {{ r.message || "" }}
        </li>
      </ul>
      <div class="p115-actions">
        <button
          @click="run('tasks/start', { kind: 'check' })"
          :disabled="!valid || busy || submitting"
        >
          检查连接与目录
        </button>
        <button
          class="primary"
          @click="run('tasks/start', { kind: 'scan' })"
          :disabled="!valid || busy || submitting"
        >
          {{ currentPlan?.count ? "重新生成预览" : "生成预览" }}
        </button>
        <button
          class="danger-button"
          @click="prepare"
          :disabled="!currentPlan?.valid || busy || submitting"
        >
          确认执行 {{ currentPlan?.executable || 0 }} 个文件
        </button>
      </div>
      <p v-if="!currentPlan?.valid" class="p115-note">
        {{ currentPlan?.reason }}
      </p>
      <p v-else class="p115-note">
        生成于 {{ currentPlan.created_at }} · 有效至
        {{
          timeLabel(currentPlan.expires_at)
        }}。执行全部待处理项，不仅是当前页。
      </p>
      <div
        v-if="prepared && !confirm"
        class="p115-alert danger"
        role="alertdialog"
        aria-label="执行确认"
      >
        <h3>执行前确认</h3>
        <p>
          执行 {{ prepared.count }} 个文件，含失败重试
          {{ prepared.retry_count }} 个；跳过 {{ prepared.skip_count }} 个。
        </p>
        <p>
          目标：{{ prepared.targets.join("、") }}。{{
            prepared.delete_empty_dirs
              ? "将清理成功整理来源中的空目录。"
              : "不清理空目录。"
          }}
          已开始的移动无法一键撤销。
        </p>
        <button class="danger-button" @click="execute" :disabled="submitting">
          我已核对，确认执行</button
        ><button @click="prepared = null">取消</button>
      </div>
      <section class="p115-task" aria-live="polite">
        <b>{{ stateLabels[workflow.task.status] || workflow.task.status }}</b> ·
        {{ workflow.task.message }}
        <progress
          v-if="busy && progress !== null"
          :value="progress"
          max="100"
          :aria-label="`任务进度 ${progress}%`"
        ></progress>
        <small v-if="workflow.task.updated_at"
          >最近活动 {{ timeLabel(workflow.task.updated_at)
          }}{{
            workflow.task.discovered
              ? ` · 已检查 ${workflow.task.discovered} 条`
              : ""
          }}</small
        >
        <button
          v-if="busy"
          @click="run('tasks/stop')"
          :disabled="submitting || workflow.task.status === 'stopping'"
        >
          完成当前批次后停止
        </button>
        <p v-if="busy" class="p115-note">
          可以关闭页面，任务仍在后台运行；停止会保留已完成项目。
        </p>
      </section>
      <div v-if="result?.run_id" class="p115-summary">
        <b>上次执行</b><span>成功 {{ result.success }}</span
        ><span>失败 {{ result.failed }}</span
        ><span>跳过 {{ result.skipped }}</span
        ><span>剩余 {{ result.remaining || 0 }}</span>
      </div>
      <p v-if="workflow.scan_summary.limit_reached" class="p115-alert">
        本次达到扫描上限，后面的文件可能尚未检查；整理本次后可再次生成预览，或调整单次上限。
      </p>
      <details v-if="workflow.scan_summary.record_count">
        <summary>
          扫描说明：共 {{ workflow.scan_summary.record_count }} 条记录
        </summary>
        <ul>
          <li
            v-for="(count, reason) in workflow.scan_summary.counts"
            :key="reason"
          >
            {{ reason }}：{{ count }}
          </li>
        </ul>
        <p>扫描诊断最多保留 5000 条，计数覆盖全部。</p>
      </details>
      <div class="p115-filters">
        <label
          >记录<select v-model="kind">
            <option value="plan">本次预览</option>
            <option value="scan">扫描与跳过原因</option>
            <option value="history">整理历史</option>
            <option value="runs">执行批次</option>
          </select></label
        >
        <label
          >状态<select v-model="filter">
            <option value="">全部</option>
            <option value="planned">待执行</option>
            <option value="executed">已执行</option>
            <option value="failed">失败</option>
            <option value="skipped">跳过</option>
          </select></label
        >
        <label
          >搜索<input v-model="query" placeholder="文件名、路径、错误或批次 ID"
        /></label>
      </div>
      <nav
        v-if="pagination.total_pages > 1"
        class="p115-pager"
        aria-label="顶部记录分页"
      >
        <button :disabled="page <= 1" @click="page--">上一页</button>
        <span>第 {{ pagination.page }} / {{ pagination.total_pages }} 页</span>
        <button :disabled="page >= pagination.total_pages" @click="page++">
          下一页
        </button>
      </nav>
      <div v-if="records.length" class="p115-records">
        <article v-for="(r, i) in records" :key="`${kind}-${page}-${i}`">
          <header>
            <b>{{
              stateLabels[r.status] || (kind === "runs" ? "执行批次" : "记录")
            }}</b
            ><time>{{ r.time || r.created_at || "" }}</time>
          </header>
          <strong class="p115-filename">{{ name(r) }}</strong>
          <p v-if="r.title && r.source_name">
            识别为：{{ r.title }} {{ r.year || "" }}
            {{ r.season ? `第 ${r.season} 季` : "" }}
            {{ r.episode ? `第 ${r.episode} 集` : "" }}
          </p>
          <p v-if="r.target_path" class="p115-path">→ {{ r.target_path }}</p>
          <p v-else-if="r.target_name">
            → {{ r.target_category }} / {{ r.target_name }}
          </p>
          <p v-if="warnings(r)" class="p115-warning">{{ warnings(r) }}</p>
          <small v-if="r.path_hint && kind === 'scan'">{{ r.path_hint }}</small>
          <p v-if="kind === 'runs'">
            成功 {{ r.success }} · 失败 {{ r.failed }} · 跳过
            {{ r.skipped }}（共 {{ r.total }}）
          </p>
          <small v-if="r.run_id">批次 {{ r.run_id }}</small>
        </article>
      </div>
      <p v-else class="p115-empty">
        暂无符合条件的记录。可切换记录类型或清除筛选。
      </p>
      <nav class="p115-pager" aria-label="记录分页">
        <button :disabled="page <= 1" @click="page--">上一页</button
        ><span
          >第 {{ pagination.page }} / {{ pagination.total_pages || 1 }} 页 · 共
          {{ pagination.total }} 条</span
        ><button :disabled="page >= pagination.total_pages" @click="page++">
          下一页
        </button>
      </nav>
    </template>
    <p v-else>正在读取插件状态…</p>
  </section>
</template>
<style scoped>
.p115-page {
  padding: 16px;
  line-height: 1.6;
  max-width: 1100px;
  margin: auto;
  color: inherit;
}
.p115-page h2 {
  font-size: 1.35rem;
  margin: 0;
}
.p115-page p {
  margin: 6px 0;
}
.p115-page button,
.p115-page input,
.p115-page select {
  font: inherit;
  border: 1px solid #85919f70;
  border-radius: 8px;
  padding: 7px 12px;
  color: inherit;
  background: transparent;
}
.p115-page button {
  cursor: pointer;
}
.p115-page button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.p115-page button.primary {
  background: #245ec8;
  color: #fff;
  border-color: #245ec8;
}
.p115-page button.danger-button {
  border-color: #ce5656;
  color: #cf4545;
}
.p115-toolbar,
.p115-actions,
.p115-summary,
.p115-pager,
.p115-filters {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}
.p115-toolbar > div {
  flex: 1;
}
.p115-steps {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin: 16px 0;
}
.p115-steps > div {
  border: 1px solid #85919f55;
  padding: 12px;
  border-radius: 10px;
}
.p115-steps b,
.p115-steps span,
.p115-connection small,
.p115-task small {
  display: block;
}
.p115-steps .ready {
  border-color: #38896f;
}
.p115-alert {
  padding: 12px;
  border-radius: 10px;
  background: #8092ac15;
  margin: 10px 0;
  overflow-wrap: anywhere;
}
.p115-alert.danger {
  background: #cc414115;
  border: 1px solid #ce565650;
}
.p115-note,
small {
  opacity: 0.72;
  font-size: 0.85rem;
}
.p115-task {
  border: 1px solid #85919f55;
  border-radius: 10px;
  padding: 14px;
  margin: 16px 0;
}
.p115-task progress {
  display: block;
  width: 100%;
  margin: 10px 0;
}
.p115-filters {
  margin-top: 20px;
}
.p115-filters label {
  display: grid;
  gap: 4px;
}
.p115-filters label:last-child {
  flex: 1;
  min-width: 160px;
}
.p115-records {
  display: grid;
  gap: 10px;
  margin: 12px 0;
}
.p115-records article {
  border: 1px solid #85919f55;
  border-radius: 10px;
  padding: 12px;
  overflow-wrap: anywhere;
}
.p115-records header {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  font-size: 0.85rem;
}
.p115-filename {
  display: block;
  margin-top: 6px;
}
.p115-path {
  font-size: 0.9rem;
}
.p115-warning {
  color: #ba731e;
}
.p115-empty {
  text-align: center;
  padding: 25px;
}
.p115-pager {
  justify-content: center;
}
.p115-paths {
  font-size: 0.9rem;
  overflow-wrap: anywhere;
}
@media (max-width: 600px) {
  .p115-steps {
    grid-template-columns: 1fr;
  }
  .p115-page {
    padding: 10px;
  }
  .p115-actions button {
    flex: 1 1 130px;
  }
  .p115-records header {
    flex-wrap: wrap;
  }
}
</style>
