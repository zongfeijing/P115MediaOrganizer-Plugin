// Local visual QA only. No live API, network requests or credentials are used.
import { createApp, defineComponent, h, ref } from "vue";
import Page from "./components/Page.vue";
import Config from "./components/Config.vue";
const rows = Array.from({ length: 65 }, (_, i) => ({
  source_name: `示例电影.${i + 1}.2026.2160p.WEB-DL.mkv`,
  title: "示例电影",
  year: "2026",
  status: i % 9 === 0 ? "skipped" : "planned",
  target_path: `/媒体库/Movie/华语电影/示例电影 ${i + 1} (2026)/示例电影 ${i + 1}.mkv`,
  warnings: i % 9 === 0 ? ["未识别到媒体，保留源文件"] : [],
}));
const state: any = {
  busy: false,
  configuration: { valid: true, errors: [], cookie_mode: "text" },
  connection: { ok: true, kind: "healthy", message: "连接正常，Cookie 有效" },
  versions: { p115client: "0.0.9.7.2", "python-concurrenttools": "0.1.9" },
  plan: {
    count: 65,
    executable: 57,
    valid: true,
    created_at: "2026-10-06 21:30:00",
    expires_at: 1791351000,
  },
  task: { status: "completed", message: "预览已生成：待执行 57，跳过 8" },
  scan_summary: {
    record_count: 68,
    counts: { 识别完成: 57, 未识别到媒体: 8, 文件小于最小体积: 3 },
  },
  last_result: {
    run_id: "example",
    success: 28,
    failed: 1,
    skipped: 2,
    remaining: 1,
  },
  path_checks: [
    { path: "/待整理/Movie", ok: true },
    { path: "/媒体库/Movie", ok: true },
  ],
};
const api = {
  get: async (path: string, { params }: any = {}) => ({
    success: true,
    data: path.endsWith("workflow")
      ? state
      : {
          items: rows.slice(
            ((params?.page || 1) - 1) * 20,
            (params?.page || 1) * 20,
          ),
          pagination: { page: params?.page || 1, total_pages: 4, total: 65 },
        },
  }),
  post: async (path: string, data: any) => ({
    success: true,
    data: path.endsWith("prepare")
      ? {
          token: "mock-only",
          count: 57,
          retry_count: 0,
          skip_count: 8,
          targets: ["/媒体库/Movie"],
          delete_empty_dirs: true,
        }
      : path.endsWith("list_dir")
        ? { items: [{ name: "Movie", cid: "mock", is_dir: true }] }
        : { valid: true, errors: [] },
  }),
};
const initialConfig = {
  cookie_text: "fake-demo-cookie",
  source_mappings: JSON.stringify([
    {
      name: "电影来源",
      media_type: "movie",
      source_path: "/待整理/Movie",
      target_root_path: "/媒体库/Movie",
    },
    {
      name: "电视剧来源",
      media_type: "tv",
      source_path: "/待整理/TV",
      target_root_path: "/媒体库/TV",
    },
  ]),
};
createApp(
  defineComponent({
    setup() {
      const view = ref(location.hash === "#config" ? "config" : "page");
      return () =>
        h("main", [
          h(
            "p",
            {
              style:
                "padding:10px;background:#eaf2ff;margin:0;font:14px sans-serif",
            },
            "本地测试预览 · 全部为虚构数据 · 不连接 115/NAS",
          ),
          h(view.value === "page" ? Page : Config, {
            api,
            pluginId: "P115MediaOrganizer",
            initialConfig,
            onSwitch: () => {
              view.value = view.value === "page" ? "config" : "page";
            },
            onSave: () => alert("测试：配置已通过检查"),
          }),
        ]);
    },
  }),
).mount("#app");
document.body.style.cssText =
  "margin:0;font-family:system-ui,sans-serif;background:#f7f9fc;color:#243247";
