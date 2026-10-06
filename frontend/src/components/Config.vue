<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
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
const advanced = ref(false),
  rawSources = ref(String(config.value.source_mappings || "[]"));
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
const canSave = computed(() => !validating.value && !browser.value);
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
  validating.value = true;
  checked.value = false;
  errors.value = [];
  try {
    const data = await api.post("validate_config", { config: payload() });
    errors.value = data.errors || [];
    checked.value = data.valid;
    if (save && data.valid) emit("save", payload());
  } catch (e: any) {
    errors.value = e.details?.errors || [e.message || "配置检查失败"];
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
  <section class="p115-config">
    <header>
      <h2>配置 115 云端媒体整理</h2>
      <p>
        先设置连接和来源，再生成预览。保存不会自动执行，除非明确勾选“立即运行一次”。
      </p>
    </header>
    <div v-if="errors.length" class="notice error" role="alert">
      <ul>
        <li v-for="e in errors" :key="e">{{ e }}</li>
      </ul>
    </div>
    <p v-if="checked" class="notice">
      配置格式检查通过。连接与实际目录请保存后在详情页检查。
    </p>
    <fieldset>
      <legend>1. 115 连接</legend>
      <label
        >连接方式<select v-model="config.cookie_mode">
          <option value="text">粘贴 Cookie</option>
          <option value="file">使用 Cookie 文件</option>
        </select></label
      >
      <label v-if="config.cookie_mode === 'text'"
        >Cookie 文本<input
          v-model="config.cookie_text"
          type="password"
          autocomplete="off"
      /></label>
      <label v-else
        >容器内 Cookie 文件路径<input
          v-model="config.cookie_path"
          placeholder="/config/115-cookies.txt"
      /></label>
      <p>
        只使用你选择的方式，另一种不会覆盖它。Cookie
        不会出现在进度或诊断记录中。
      </p>
    </fieldset>
    <fieldset>
      <legend>2. 来源与目标目录</legend>
      <button @click="switchMode">
        {{ mode === "visual" ? "高级 JSON 编辑" : "切换可视化编辑" }}
      </button>
      <textarea
        v-if="mode === 'json'"
        v-model="rawSources"
        rows="12"
        aria-label="来源映射 JSON"
      ></textarea>
      <template v-else
        ><article v-for="(s, i) in sources" :key="i" class="source-card">
          <div class="row">
            <label>名称<input v-model="s.name" /></label
            ><label
              >媒体类型<select v-model="s.media_type">
                <option value="movie">电影</option>
                <option value="tv">电视剧</option>
              </select></label
            ><button @click="sources.splice(i, 1)" aria-label="删除来源">
              删除
            </button>
          </div>
          <div class="row">
            <label
              >115 待整理来源<input
                v-model="s.source_path"
                placeholder="/待整理/Movie" /></label
            ><button @click="openBrowser(i, 'source_path')">选择目录</button>
          </div>
          <div class="row">
            <label
              >目标媒体库根目录<input
                v-model="s.target_root_path"
                placeholder="/媒体库/Movie" /></label
            ><button @click="openBrowser(i, 'target_root_path')">
              选择目录
            </button>
          </div>
          <p>
            目标不能位于任何来源目录内。目标根目录下的分类目录需与 MoviePilot
            分类匹配。
          </p>
        </article>
        <button @click="add">＋ 添加来源</button></template
      >
      <div
        v-if="browser"
        class="directory-picker"
        role="region"
        aria-label="115 目录选择"
      >
        <b>选择目录：{{ browser.path }}</b>
        <p>
          使用已保存的连接。首次配置请先保存 Cookie 和路径，再打开目录选择。
        </p>
        <p v-if="browser.message" role="alert">{{ browser.message }}</p>
        <div class="row">
          <button
            @click="browse(parent())"
            :disabled="browsersLoading || browser.path === '/'"
          >
            上一级</button
          ><button @click="selectDirectory" :disabled="browsersLoading">
            使用当前目录</button
          ><button @click="browser = null">取消</button>
        </div>
        <ul>
          <li v-for="d in browser.items" :key="d.cid">
            <button @click="browse(child(d.name))" :disabled="browsersLoading">
              📁 {{ d.name }}
            </button>
          </li>
        </ul>
        <p v-if="!browser.items.length && !browsersLoading">暂无子目录。</p>
      </div>
    </fieldset>
    <fieldset>
      <legend>3. 自动运行与整理策略</legend>
      <div class="row">
        <label class="check"
          ><input v-model="config.enabled" type="checkbox" />启用定时服务</label
        ><label class="check"
          ><input v-model="config.notify" type="checkbox" />发送结果通知</label
        >
      </div>
      <label
        >定时模式<select v-model="config.dry_run">
          <option :value="true">仅生成预览（推荐）</option>
          <option :value="false">生成后自动执行</option>
        </select></label
      >
      <p>手动执行始终需要确认摘要；无需为手动执行关闭“仅生成预览”。</p>
      <label
        >运行时间<select
          @change="config.cron = ($event.target as HTMLSelectElement).value"
        >
          <option value="">选择常用时间</option>
          <option value="0 3 * * *">每天凌晨 3 点</option>
          <option value="0 */6 * * *">每 6 小时</option>
          <option value="0 3 * * 0">每周日凌晨 3 点</option>
        </select></label
      >
      <label
        >五段 CRON（留空不自动运行）<input
          v-model="config.cron"
          placeholder="0 3 * * *"
      /></label>
      <label class="check"
        ><input
          v-model="config.onlyonce"
          type="checkbox"
        />保存后立即运行一次（遵循定时模式）</label
      >
      <div class="row">
        <label class="check"
          ><input
            v-model="config.delete_empty_source_dirs"
            type="checkbox"
          />整理后清理空来源目录</label
        ><label class="check"
          ><input
            v-model="config.refresh_plex_after_execute"
            type="checkbox"
          />整理后刷新 Plex</label
        >
      </div>
      <div class="row">
        <label
          >单次扫描最多文件（0 不限）<input
            v-model.number="config.max_items_per_run"
            type="number"
            min="0"
            max="10000" /></label
        ><label
          >最小文件体积（MB）<input
            v-model.number="config.min_file_size_mb"
            type="number"
            min="0" /></label
        ><label
          >扫描深度<input
            v-model.number="config.max_depth"
            type="number"
            min="0"
            max="30"
        /></label>
      </div>
      <label
        >重名策略<select v-model="config.conflict_strategy">
          <option value="skip">跳过，不覆盖</option>
          <option value="rename_with_suffix">自动添加后缀</option>
        </select></label
      >
      <label
        >无法识别的文件<select v-model="config.unrecognized_action">
          <option value="skip">跳过并显示原因</option>
          <option value="move_to_unrecognized">
            移动到未识别 CID（须在高级项配置）
          </option>
        </select></label
      >
    </fieldset>
    <button @click="advanced = !advanced">
      {{ advanced ? "收起" : "展开" }}高级设置
    </button>
    <fieldset v-if="advanced">
      <legend>高级设置</legend>
      <label
        >目标 CID 覆盖 JSON<textarea
          v-model="config.target_cids"
          rows="5"
        ></textarea></label
      ><label
        >分类别名 JSON<textarea
          v-model="config.category_mapping"
          rows="5"
        ></textarea>
      </label>
      <label
        >排除关键词（逗号分隔）<input v-model="config.exclude_keywords"
      /></label>
      <label class="check"
        ><input v-model="config.allow_external_execute" type="checkbox" />允许
        API Key 外部自动执行（默认关闭）</label
      >
      <div class="row">
        <label
          >批大小<input
            v-model.number="config.batch_size"
            type="number"
            min="1"
            max="100" /></label
        ><label
          >批间隔（秒）<input
            v-model.number="config.sleep_between_batches"
            type="number"
            min="0"
            max="120"
            step="0.1" /></label
        ><label
          >计划有效期（小时）<input
            v-model.number="config.plan_ttl_hours"
            type="number"
            min="1"
            max="720"
        /></label>
      </div>
      <div class="row">
        <label
          >请求间隔（毫秒）<input
            v-model.number="config.min_request_interval_ms"
            type="number"
            min="0" /></label
        ><label
          >重试次数<input
            v-model.number="config.max_retries"
            type="number"
            min="0"
            max="10" /></label
        ><label
          >退避基数（秒）<input
            v-model.number="config.retry_base_seconds"
            type="number"
            min="0.1"
            step="0.1"
        /></label>
      </div>
      <div class="row">
        <label
          >抖动比例<input
            v-model.number="config.jitter_ratio"
            type="number"
            min="0"
            max="1"
            step="0.1" /></label
        ><label
          >目录分页大小<input
            v-model.number="config.list_page_size"
            type="number"
            min="50"
            max="1000" /></label
        ><label
          >历史保留数<input
            v-model.number="config.history_limit"
            type="number"
            min="1"
        /></label>
      </div>
    </fieldset>
    <footer class="row">
      <button @click="validate(false)" :disabled="!canSave">检查配置格式</button
      ><button class="primary" @click="validate(true)" :disabled="!canSave">
        {{ validating ? "检查中…" : "检查并保存" }}</button
      ><button @click="emit('switch')">查看详情</button
      ><button @click="emit('close')">关闭</button>
    </footer>
  </section>
</template>
<style scoped>
.p115-config {
  padding: 16px;
  line-height: 1.6;
  max-width: 1000px;
  margin: auto;
}
.p115-config h2 {
  font-size: 1.3rem;
}
.p115-config p {
  font-size: 0.88rem;
  opacity: 0.8;
}
.p115-config fieldset {
  border: 1px solid #85919f60;
  border-radius: 10px;
  padding: 14px;
  margin: 16px 0;
  min-width: 0;
}
.p115-config legend {
  font-weight: 700;
  padding: 0 6px;
}
.p115-config label {
  display: grid;
  gap: 5px;
  margin: 8px 0;
  flex: 1;
  min-width: 160px;
}
.p115-config input:not([type="checkbox"]),
.p115-config select,
.p115-config textarea,
.p115-config button {
  font: inherit;
  color: inherit;
  background: transparent;
  border: 1px solid #85919f70;
  border-radius: 8px;
  padding: 8px;
  max-width: 100%;
  box-sizing: border-box;
}
.p115-config textarea {
  width: 100%;
  font-family: monospace;
}
.p115-config button {
  cursor: pointer;
}
.p115-config button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.p115-config button.primary {
  background: #245ec8;
  color: #fff;
}
.p115-config label.check {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 200px;
}
.p115-config .row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.source-card {
  border: 1px solid #85919f55;
  padding: 12px;
  margin: 12px 0;
  border-radius: 10px;
}
.notice,
.directory-picker {
  background: #8092ac15;
  border-radius: 10px;
  padding: 12px;
  margin: 12px 0;
}
.notice.error {
  background: #cc414115;
}
.directory-picker ul {
  list-style: none;
  padding: 0;
  max-height: 260px;
  overflow: auto;
}
.directory-picker li {
  margin: 5px 0;
}
.directory-picker li button {
  width: 100%;
  text-align: left;
}
footer {
  position: sticky;
  bottom: 0;
  background: rgb(var(--v-theme-surface, 255, 255, 255));
  padding: 12px 0;
}
.p115-config input:focus,
.p115-config button:focus-visible {
  outline: 2px solid #548adf;
  outline-offset: 2px;
}
@media (max-width: 600px) {
  .p115-config {
    padding: 10px;
  }
  .p115-config .row label {
    flex-basis: 100%;
  }
}
</style>
