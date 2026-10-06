import { describe, it, expect, vi } from "vitest";
import { client, unwrap } from "./api";
describe("host API adapter", () => {
  it("unwraps both host envelopes and legacy Axios responses", () => {
    expect(unwrap({ success: true, data: { x: 1 } })).toEqual({ x: 1 });
    expect(unwrap({ data: { success: true, data: { x: 2 } } })).toEqual({
      x: 2,
    });
    expect(() =>
      unwrap({ success: false, message: "invalid", data: { errors: ["bad"] } }),
    ).toThrow("invalid");
  });
  it("uses the current instance namespace", async () => {
    const api = {
      get: vi.fn().mockResolvedValue({ success: true, data: {} }),
      post: vi.fn().mockResolvedValue({ success: true, data: {} }),
    };
    await client({
      api,
      pluginId: "clone-1",
      sourcePluginId: "P115MediaOrganizer",
    }).post("tasks/start", { kind: "scan" });
    expect(api.post).toHaveBeenCalledWith("plugin/clone-1/tasks/start", {
      kind: "scan",
    });
  });
});
