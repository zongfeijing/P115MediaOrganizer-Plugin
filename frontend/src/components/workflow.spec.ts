import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createVuetify } from "vuetify";
import * as components from "vuetify/components";
import * as directives from "vuetify/directives";
import Page from "./Page.vue";
import Config from "./Config.vue";
const state = {
  busy: false,
  configuration: {
    valid: true,
    cookie_mode: "text",
    errors: [],
    preview_only: true,
  },
  connection: { ok: true, message: "连接正常" },
  versions: {},
  plan: {
    valid: true,
    count: 65,
    executable: 65,
    created_at: "2026-10-06",
    expires_at: 123,
    counts: {},
  },
  task: { status: "idle", message: "尚未运行" },
  scan_summary: {},
  last_result: {},
};
function hostApi() {
  return {
    get: vi.fn(
      async (path: string): Promise<any> => ({
        success: true,
        data: path.endsWith("workflow")
          ? state
          : {
              items: [
                {
                  source_name: "a.mkv",
                  status: "planned",
                  target_path: "/library/a.mkv",
                },
              ],
              pagination: { page: 1, total_pages: 4, total: 65 },
            },
      }),
    ),
    post: vi.fn(async (path: string) => ({
      success: true,
      data: path.endsWith("prepare")
        ? {
            token: "receipt",
            count: 65,
            retry_count: 0,
            skip_count: 0,
            targets: ["/library"],
            delete_empty_dirs: false,
          }
        : { valid: true, errors: [] },
    })),
  };
}
function render(component: any, props: any, provide: any = {}) {
  return mount(component, {
    props,
    global: { plugins: [createVuetify({ components, directives })], provide },
  });
}
function button(w: any, text: string) {
  return w.findAll("button").find((b: any) => b.text().includes(text))!;
}
afterEach(() => vi.restoreAllMocks());
describe("MP-native workflow", () => {
  it("requires explicit confirmation and preserves current instance API namespace", async () => {
    const api = hostApi(),
      w = render(Page, { api, pluginId: "clone-1" });
    await flushPromises();
    expect(w.text()).toContain("共 65 条");
    expect(w.find(".v-btn--variant-flat").exists()).toBe(true);
    await button(w, "确认执行 65").trigger("click");
    await flushPromises();
    expect(api.post).toHaveBeenCalledWith("plugin/clone-1/execute/prepare", {});
    expect(api.post.mock.calls.some(([path]) => path.endsWith("confirm"))).toBe(
      false,
    );
    await button(w, "我已核对").trigger("click");
    await flushPromises();
    expect(api.post).toHaveBeenCalledWith("plugin/clone-1/execute/confirm", {
      token: "receipt",
    });
    w.unmount();
  });
  it("uses native pagination to access all records", async () => {
    const api = hostApi(),
      w = render(Page, { api, pluginId: "P115MediaOrganizer" });
    await flushPromises();
    w.findComponent(components.VPagination).vm.$emit("update:modelValue", 2);
    await flushPromises();
    expect(api.get).toHaveBeenCalledWith("plugin/P115MediaOrganizer/records", {
      params: { kind: "plan", status: "", query: "", page: 2, page_size: 20 },
    });
    w.unmount();
  });
  it("shows native progress and disables actions while busy", async () => {
    const api = hostApi();
    api.get = vi.fn(
      async (path: string): Promise<any> => ({
        success: true,
        data: path.endsWith("workflow")
          ? {
              ...state,
              busy: true,
              task: {
                status: "running",
                message: "识别文件",
                total: 50,
                completed: 10,
              },
            }
          : { items: [], pagination: { page: 1, total_pages: 1, total: 0 } },
      }),
    );
    const w = render(Page, { api, pluginId: "P115MediaOrganizer" });
    await flushPromises();
    expect(
      w
        .findAllComponents(components.VProgressLinear)
        .find((c) => c.attributes("aria-label") === "任务进度 20%")!
        .props("modelValue"),
    ).toBe(20);
    expect(button(w, "确认执行").attributes("disabled")).toBeDefined();
    expect(w.text()).toContain("完成当前批次后停止");
    w.unmount();
  });
  it("validates visual sources before save and retains legacy text-first behavior", async () => {
    const api = hostApi(),
      initialConfig = {
        cookie_text: "fake",
        source_mappings: JSON.stringify([
          {
            name: "Movie",
            media_type: "movie",
            source_path: "/in",
            target_root_path: "/library",
          },
        ]),
      };
    const w = render(Config, {
      api,
      pluginId: "P115MediaOrganizer",
      initialConfig,
    });
    await w.find("form").trigger("submit");
    await flushPromises();
    const saved = w.emitted("save")![0][0] as any;
    expect(saved.cookie_mode).toBe("text");
    expect(JSON.parse(saved.source_mappings)[0].source_path).toBe("/in");
    expect(api.post).toHaveBeenCalledWith(
      "plugin/P115MediaOrganizer/validate_config",
      { config: saved },
    );
    w.unmount();
  });
  it("keeps invalid legacy JSON visible and uses outlined native fields", async () => {
    const w = render(Config, {
      api: hostApi(),
      pluginId: "P115MediaOrganizer",
      initialConfig: { source_mappings: "[{bad]" },
    });
    expect((w.find("textarea").element as HTMLTextAreaElement).value).toBe(
      "[{bad]",
    );
    expect(w.text()).toContain("旧来源映射 JSON 无效");
    expect(w.findComponent(components.VTextarea).exists()).toBe(true);
    w.unmount();
  });
  it("asks before enabling automatic execution or removing a source", async () => {
    const confirm = vi.fn().mockResolvedValue(false),
      initialConfig = {
        cookie_text: "fake",
        source_mappings: JSON.stringify([
          {
            name: "Movie",
            media_type: "movie",
            source_path: "/in",
            target_root_path: "/library",
          },
        ]),
      };
    const w = render(
      Config,
      { api: hostApi(), pluginId: "P115MediaOrganizer", initialConfig },
      { "moviepilot:confirm": confirm },
    );
    await w.find('[aria-label="移除来源 1"]').trigger("click");
    await flushPromises();
    expect(confirm).toHaveBeenCalled();
    expect(w.findAll(".p115-source").length).toBe(1);
    w.findComponent(components.VTabs).vm.$emit(
      "update:modelValue",
      "automation",
    );
    await flushPromises();
    const mode = w
      .findAllComponents(components.VSelect)
      .find((c) => c.props("label") === "定时与立即运行模式")!;
    mode.vm.$emit("update:modelValue", false);
    await flushPromises();
    expect(confirm).toHaveBeenCalledWith(
      expect.objectContaining({ title: "开启自动执行" }),
    );
    await w.find("form").trigger("submit");
    await flushPromises();
    expect((w.emitted("save")![0][0] as any).dry_run).toBe(true);
    w.unmount();
  });
  it("promotes preview generation when no valid plan exists", async () => {
    const api = hostApi();
    api.get = vi.fn(
      async (path: string): Promise<any> => ({
        success: true,
        data: path.endsWith("workflow")
          ? {
              ...state,
              plan: {
                valid: false,
                count: 0,
                executable: 0,
                reason: "先生成预览",
              },
            }
          : { items: [], pagination: { page: 1, total_pages: 1, total: 0 } },
      }),
    );
    const w = render(Page, { api, pluginId: "P115MediaOrganizer" });
    await flushPromises();
    expect(button(w, "生成预览").exists()).toBe(true);
    expect(w.text()).not.toContain("确认执行 0 个文件");
    await button(w, "生成预览").trigger("click");
    await flushPromises();
    expect(api.post).toHaveBeenCalledWith(
      "plugin/P115MediaOrganizer/tasks/start",
      { kind: "scan" },
    );
    w.unmount();
  });
});

describe("native UI safeguards", () => {
  it("keeps manual confirm cancellation from starting execution", async () => {
    const api = hostApi();
    const confirm = vi.fn().mockResolvedValue(false);
    const w = render(
      Page,
      { api, pluginId: "P115MediaOrganizer" },
      { "moviepilot:confirm": confirm },
    );
    await flushPromises();
    await button(w, "确认执行").trigger("click");
    await flushPromises();
    expect(confirm).toHaveBeenCalledWith(
      expect.objectContaining({ title: "确认云端整理" }),
    );
    expect(api.post.mock.calls.some(([path]) => path.endsWith("confirm"))).toBe(
      false,
    );
    w.unmount();
  });
  it("saves automatic execution only after accepting the native warning", async () => {
    const api = hostApi();
    const confirm = vi.fn().mockResolvedValue(true);
    const initialConfig = {
      cookie_text: "fake",
      source_mappings: JSON.stringify([
        {
          name: "Movie",
          media_type: "movie",
          source_path: "/in",
          target_root_path: "/library",
        },
      ]),
    };
    const w = render(
      Config,
      { api, pluginId: "P115MediaOrganizer", initialConfig },
      { "moviepilot:confirm": confirm },
    );
    w.findComponent(components.VTabs).vm.$emit(
      "update:modelValue",
      "automation",
    );
    await flushPromises();
    w.findAllComponents(components.VSelect)
      .find((c) => c.props("label") === "定时与立即运行模式")!
      .vm.$emit("update:modelValue", false);
    await flushPromises();
    await w.find("form").trigger("submit");
    await flushPromises();
    expect((w.emitted("save")![0][0] as any).dry_run).toBe(false);
    w.unmount();
  });
  it("renders separate native desktop and mobile views without dropping movie episode-like text", async () => {
    const { default: RecordList } = await import("./RecordList.vue");
    const w = render(RecordList, {
      kind: "plan",
      records: [
        {
          source_name: "Movie.10.mkv",
          title: "Movie",
          media_type: "movie",
          season: 1,
          episode: 10,
          year: "2026",
          status: "planned",
          target_path: "/library/Movie.mkv",
        },
      ],
    });
    expect(w.find(".p115-desktop .v-table__wrapper").exists()).toBe(true);
    expect(w.find(".p115-mobile .v-card").exists()).toBe(true);
    expect(w.text()).not.toContain("第 10 集");
    expect(w.text()).toContain("/library/Movie.mkv");
    w.unmount();
  });
});

describe("offline native icon rendering", () => {
  it("renders SVG paths for toolbar and directory actions without icon-font CSS", async () => {
    const api = hostApi();
    const w = render(Page, { api, pluginId: "P115MediaOrganizer" });
    await flushPromises();
    for (const name of ["配置", "刷新状态", "关闭"]) {
      expect(w.find(`[aria-label="${name}"] path`).exists()).toBe(true);
    }
    w.unmount();
    const config = render(Config, {
      api,
      pluginId: "P115MediaOrganizer",
      initialConfig: {
        cookie_text: "fake",
        source_mappings: JSON.stringify([
          {
            name: "Movie",
            media_type: "movie",
            source_path: "/in",
            target_root_path: "/library",
          },
        ]),
      },
    });
    expect(
      config.findAll(".v-field__append-inner path").length,
    ).toBeGreaterThanOrEqual(3);
    config.unmount();
  });
});
