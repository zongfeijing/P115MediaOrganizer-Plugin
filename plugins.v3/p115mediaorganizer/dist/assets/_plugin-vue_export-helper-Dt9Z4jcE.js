function unwrap(response) {
  const envelope = response?.data && typeof response.data.success === "boolean" ? response.data : response;
  if (envelope?.success === false) {
    const error = new Error(envelope.message || "请求失败");
    error.details = envelope.data;
    throw error;
  }
  return typeof envelope?.success === "boolean" ? envelope.data : envelope?.data ?? envelope;
}
function client(props) {
  if (!props.pluginId)
    throw new Error("宿主未提供插件实例 ID，请更新 MoviePilot");
  const prefix = `plugin/${encodeURIComponent(props.pluginId)}`;
  return {
    get: async (path, params = {}) => unwrap(await props.api.get(`${prefix}/${path}`, { params })),
    post: async (path, data = {}) => unwrap(await props.api.post(`${prefix}/${path}`, data))
  };
}
const stateLabels = {
  planned: "待执行",
  executed: "已执行",
  skipped: "跳过",
  failed: "失败",
  queued: "排队中",
  running: "运行中",
  stopping: "正在停止",
  completed: "已完成",
  cancelled: "已停止",
  idle: "尚未运行"
};

const _export_sfc = (sfc, props) => {
  const target = sfc.__vccOpts || sfc;
  for (const [key, val] of props) {
    target[key] = val;
  }
  return target;
};

export { _export_sfc as _, client as c, stateLabels as s };
