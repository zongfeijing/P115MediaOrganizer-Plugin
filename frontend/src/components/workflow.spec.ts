import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import Page from "./Page.vue";
import Config from "./Config.vue";
const state = {
  busy: false,
  configuration: { valid: true, cookie_mode: "text", errors: [] },
  connection: { ok: true, message: "连接正常" },
  versions: {},
  plan: {
    valid: true,
    count: 65,
    executable: 65,
    created_at: "2026-10-06",
    expires_at: 123,
  },
  task: { status: "idle", message: "尚未运行" },
  scan_summary: {},
  last_result: {},
};
function hostApi() {
  return {
    get: vi.fn(async (path: string) => ({
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
    })),
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
afterEach(() => vi.restoreAllMocks());
describe("interactive workflow", () => {
  it("does not execute until the explicit confirmation is accepted", async () => {
    const api = hostApi(),
      w = mount(Page, { props: { api, pluginId: "clone-1" } });
    await flushPromises();
    expect(w.text()).toContain("共 65 条");
    const button = w
      .findAll("button")
      .find((b) => b.text().includes("确认执行 65"))!;
    await button.trigger("click");
    await flushPromises();
    expect(api.post).toHaveBeenCalledWith("plugin/clone-1/execute/prepare", {});
    expect(api.post.mock.calls.some(([p]) => p.endsWith("confirm"))).toBe(
      false,
    );
    await w
      .findAll("button")
      .find((b) => b.text().includes("我已核对"))!
      .trigger("click");
    await flushPromises();
    expect(api.post).toHaveBeenCalledWith("plugin/clone-1/execute/confirm", {
      token: "receipt",
    });
    w.unmount();
  });
  it("pages through all records on mobile and desktop using the same API", async () => {
    const api = hostApi(),
      w = mount(Page, { props: { api, pluginId: "P115MediaOrganizer" } });
    await flushPromises();
    await w
      .findAll("button")
      .find((b) => b.text() === "下一页")!
      .trigger("click");
    await flushPromises();
    expect(api.get).toHaveBeenCalledWith("plugin/P115MediaOrganizer/records", {
      params: { kind: "plan", status: "", query: "", page: 2, page_size: 20 },
    });
    w.unmount();
  });
  it("shows busy state and disables mutation buttons", async () => {
    const api = hostApi();
    api.get = vi.fn(async (path: string) => ({
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
    }));
    const w = mount(Page, { props: { api, pluginId: "P115MediaOrganizer" } });
    await flushPromises();
    expect(w.find("progress").attributes("value")).toBe("20");
    expect(
      w
        .findAll("button")
        .find((b) => b.text().includes("确认执行"))!
        .attributes("disabled"),
    ).toBeDefined();
    expect(w.text()).toContain("完成当前批次后停止");
    w.unmount();
  });
  it("validates a visual source list before saving and retains legacy text-first mode", async () => {
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
    const w = mount(Config, {
      props: { api, pluginId: "P115MediaOrganizer", initialConfig },
    });
    await w
      .findAll("button")
      .find((b) => b.text() === "检查并保存")!
      .trigger("click");
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
  it("keeps invalid legacy JSON visible instead of replacing it with example paths", async () => {
    const w = mount(Config, {
      props: {
        api: hostApi(),
        pluginId: "P115MediaOrganizer",
        initialConfig: { source_mappings: "[{bad]" },
      },
    });
    expect((w.find("textarea").element as HTMLTextAreaElement).value).toBe(
      "[{bad]",
    );
    expect(w.text()).toContain("旧来源映射 JSON 无效");
    w.unmount();
  });
});
