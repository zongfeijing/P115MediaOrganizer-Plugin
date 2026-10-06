export interface HostApi {
  get(path: string, options?: any): Promise<any>;
  post(path: string, data?: any): Promise<any>;
}
export interface HostProps {
  api: HostApi;
  pluginId: string;
  sourcePluginId?: string;
}
export function unwrap<T = any>(response: any): T {
  // The host Axios interceptor returns envelopes, while older hosts return AxiosResponse.
  const envelope =
    response?.data && typeof response.data.success === "boolean"
      ? response.data
      : response;
  if (envelope?.success === false) {
    const error = new Error(envelope.message || "请求失败") as Error & {
      details?: any;
    };
    error.details = envelope.data;
    throw error;
  }
  return typeof envelope?.success === "boolean"
    ? envelope.data
    : (envelope?.data ?? envelope);
}
export function client(props: HostProps) {
  if (!props.pluginId)
    throw new Error("宿主未提供插件实例 ID，请更新 MoviePilot");
  const prefix = `plugin/${encodeURIComponent(props.pluginId)}`;
  return {
    get: async (path: string, params: any = {}) =>
      unwrap(await props.api.get(`${prefix}/${path}`, { params })),
    post: async (path: string, data: any = {}) =>
      unwrap(await props.api.post(`${prefix}/${path}`, data)),
  };
}
export const stateLabels: Record<string, string> = {
  planned: "待执行",
  executed: "已执行",
  skipped: "跳过",
  failed: "失败",
  queued: "排队中",
  running: "运行中",
  stopping: "正在停止",
  completed: "已完成",
  cancelled: "已停止",
  idle: "尚未运行",
};
