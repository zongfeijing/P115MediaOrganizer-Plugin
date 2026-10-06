import { importShared } from './__federation_fn_import-JrT3xvdd.js';
import { c as client, s as stateLabels, _ as _export_sfc } from './_plugin-vue_export-helper-Dt9Z4jcE.js';

const {defineComponent:_defineComponent} = await importShared('vue');

const {createElementVNode:_createElementVNode,toDisplayString:_toDisplayString,openBlock:_openBlock,createElementBlock:_createElementBlock,createCommentVNode:_createCommentVNode,normalizeClass:_normalizeClass,renderList:_renderList,Fragment:_Fragment,createTextVNode:_createTextVNode,unref:_unref,vModelSelect:_vModelSelect,withDirectives:_withDirectives,vModelText:_vModelText,createStaticVNode:_createStaticVNode} = await importShared('vue');

const _hoisted_1 = { class: "p115-page" };
const _hoisted_2 = { class: "p115-toolbar" };
const _hoisted_3 = ["disabled"];
const _hoisted_4 = ["disabled"];
const _hoisted_5 = {
  key: 0,
  class: "p115-alert danger",
  role: "alert"
};
const _hoisted_6 = {
  class: "p115-steps",
  "aria-label": "整理流程"
};
const _hoisted_7 = {
  key: 0,
  class: "p115-alert danger"
};
const _hoisted_8 = {
  key: 1,
  class: "p115-paths"
};
const _hoisted_9 = { class: "p115-actions" };
const _hoisted_10 = ["disabled"];
const _hoisted_11 = ["disabled"];
const _hoisted_12 = ["disabled"];
const _hoisted_13 = {
  key: 2,
  class: "p115-note"
};
const _hoisted_14 = {
  key: 3,
  class: "p115-note"
};
const _hoisted_15 = {
  key: 4,
  class: "p115-alert danger",
  role: "alertdialog",
  "aria-label": "执行确认"
};
const _hoisted_16 = ["disabled"];
const _hoisted_17 = {
  class: "p115-task",
  "aria-live": "polite"
};
const _hoisted_18 = ["value", "aria-label"];
const _hoisted_19 = { key: 1 };
const _hoisted_20 = ["disabled"];
const _hoisted_21 = {
  key: 3,
  class: "p115-note"
};
const _hoisted_22 = {
  key: 5,
  class: "p115-summary"
};
const _hoisted_23 = {
  key: 6,
  class: "p115-alert"
};
const _hoisted_24 = { key: 7 };
const _hoisted_25 = { class: "p115-filters" };
const _hoisted_26 = {
  key: 8,
  class: "p115-pager",
  "aria-label": "顶部记录分页"
};
const _hoisted_27 = ["disabled"];
const _hoisted_28 = ["disabled"];
const _hoisted_29 = {
  key: 9,
  class: "p115-records"
};
const _hoisted_30 = { class: "p115-filename" };
const _hoisted_31 = { key: 0 };
const _hoisted_32 = {
  key: 1,
  class: "p115-path"
};
const _hoisted_33 = { key: 2 };
const _hoisted_34 = {
  key: 3,
  class: "p115-warning"
};
const _hoisted_35 = { key: 4 };
const _hoisted_36 = { key: 5 };
const _hoisted_37 = { key: 6 };
const _hoisted_38 = {
  key: 10,
  class: "p115-empty"
};
const _hoisted_39 = {
  class: "p115-pager",
  "aria-label": "记录分页"
};
const _hoisted_40 = ["disabled"];
const _hoisted_41 = ["disabled"];
const _hoisted_42 = { key: 2 };
const {computed,inject,onBeforeUnmount,onMounted,ref,watch} = await importShared('vue');
const _sfc_main = /* @__PURE__ */ _defineComponent({
  __name: "Page",
  props: {
    api: {},
    pluginId: {},
    sourcePluginId: {}
  },
  emits: ["action", "switch", "close"],
  setup(__props, { emit: __emit }) {
    const props = __props;
    const emit = __emit;
    const api = client(props);
    const confirm = inject(
      "moviepilot:confirm",
      null
    );
    const workflow = ref(null), records = ref([]), pagination = ref({ page: 1, total_pages: 1, total: 0 });
    const error = ref(""), loading = ref(false), submitting = ref(false), prepared = ref(null);
    const kind = ref("plan"), filter = ref(""), query = ref(""), page = ref(1);
    let timer, searchTimer;
    let generation = 0, stopped = false;
    const valid = computed(() => workflow.value?.configuration?.valid);
    const busy = computed(() => workflow.value?.busy);
    const currentPlan = computed(() => workflow.value?.plan);
    const result = computed(() => workflow.value?.last_result);
    const progress = computed(() => {
      const t = workflow.value?.task;
      return t?.total ? Math.min(100, Math.round(100 * t.completed / t.total)) : null;
    });
    async function loadRecords() {
      const id = ++generation;
      try {
        const data = await api.get("records", {
          kind: kind.value,
          status: filter.value,
          query: query.value,
          page: page.value,
          page_size: 20
        });
        if (id === generation && !stopped) {
          records.value = data.items;
          pagination.value = data.pagination;
        }
      } catch (e) {
        if (id === generation) error.value = e.message || "无法读取记录";
      }
    }
    async function refresh() {
      loading.value = true;
      try {
        workflow.value = await api.get("workflow");
        await loadRecords();
      } catch (e) {
        error.value = e.message || "无法读取插件状态";
      } finally {
        loading.value = false;
      }
    }
    async function poll() {
      await refresh();
      if (!stopped) timer = setTimeout(poll, busy.value ? 2e3 : 1e4);
    }
    async function run(action, body = {}) {
      submitting.value = true;
      error.value = "";
      try {
        await api.post(action, body);
        await refresh();
      } catch (e) {
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
            cancelText: "取消"
          });
          if (ok) await execute();
          else prepared.value = null;
        }
      } catch (e) {
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
    function name(row) {
      return row.source_name || row.title || row.run_id || row.path_hint || "记录";
    }
    function warnings(row) {
      return row.reason || row.error || (row.warnings || []).join("；");
    }
    function timeLabel(epoch) {
      return epoch ? new Date(epoch * 1e3).toLocaleString("zh-CN") : "—";
    }
    return (_ctx, _cache) => {
      return _openBlock(), _createElementBlock("section", _hoisted_1, [
        _createElementVNode("header", _hoisted_2, [
          _cache[13] || (_cache[13] = _createElementVNode("div", null, [
            _createElementVNode("h2", null, "115 云端媒体整理"),
            _createElementVNode("p", null, "检查配置 → 生成预览 → 确认执行")
          ], -1)),
          _createElementVNode("button", {
            onClick: _cache[0] || (_cache[0] = ($event) => emit("switch")),
            disabled: busy.value
          }, "配置", 8, _hoisted_3),
          _createElementVNode("button", {
            onClick: refresh,
            disabled: loading.value
          }, "刷新", 8, _hoisted_4)
        ]),
        error.value ? (_openBlock(), _createElementBlock("p", _hoisted_5, _toDisplayString(error.value), 1)) : _createCommentVNode("", true),
        workflow.value ? (_openBlock(), _createElementBlock(_Fragment, { key: 1 }, [
          _createElementVNode("div", _hoisted_6, [
            _createElementVNode("div", {
              class: _normalizeClass({ ready: valid.value })
            }, [
              _cache[14] || (_cache[14] = _createElementVNode("b", null, "1. 配置检查", -1)),
              _createElementVNode("span", null, _toDisplayString(valid.value ? "配置格式通过" : "请先修正配置"), 1)
            ], 2),
            _createElementVNode("div", {
              class: _normalizeClass({ ready: currentPlan.value?.valid })
            }, [
              _cache[15] || (_cache[15] = _createElementVNode("b", null, "2. 生成预览", -1)),
              _createElementVNode("span", null, _toDisplayString(currentPlan.value?.count || 0) + " 条 · 待执行 " + _toDisplayString(currentPlan.value?.executable || 0), 1)
            ], 2),
            _cache[16] || (_cache[16] = _createElementVNode("div", null, [
              _createElementVNode("b", null, "3. 确认执行"),
              _createElementVNode("span", null, "按确认摘要整理，定时模式不变")
            ], -1))
          ]),
          !valid.value ? (_openBlock(), _createElementBlock("div", _hoisted_7, [
            _createElementVNode("ul", null, [
              (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(workflow.value.configuration.errors, (e) => {
                return _openBlock(), _createElementBlock("li", { key: e }, _toDisplayString(e), 1);
              }), 128))
            ]),
            _createElementVNode("button", {
              onClick: _cache[1] || (_cache[1] = ($event) => emit("switch"))
            }, "去修正配置")
          ])) : _createCommentVNode("", true),
          _createElementVNode("div", {
            class: _normalizeClass(["p115-connection", {
              "p115-alert": true,
              danger: workflow.value.connection.kind === "login" || workflow.value.connection.kind === "dependency"
            }])
          }, [
            _createElementVNode("b", null, _toDisplayString(workflow.value.connection.ok === true ? "115 连接正常" : "连接状态"), 1),
            _createTextVNode(" · " + _toDisplayString(workflow.value.connection.message) + " ", 1),
            _createElementVNode("small", null, "当前使用：" + _toDisplayString(workflow.value.configuration.cookie_mode === "text" ? "Cookie 文本" : "Cookie 文件") + " · 客户端 " + _toDisplayString(workflow.value.versions.p115client || "未安装") + " · 并发库 " + _toDisplayString(workflow.value.versions["python-concurrenttools"] || "未安装"), 1)
          ], 2),
          workflow.value.path_checks?.length ? (_openBlock(), _createElementBlock("ul", _hoisted_8, [
            (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(workflow.value.path_checks, (r) => {
              return _openBlock(), _createElementBlock("li", {
                key: r.path
              }, _toDisplayString(r.ok ? "✓" : "✗") + " " + _toDisplayString(r.path) + " " + _toDisplayString(r.message || ""), 1);
            }), 128))
          ])) : _createCommentVNode("", true),
          _createElementVNode("div", _hoisted_9, [
            _createElementVNode("button", {
              onClick: _cache[2] || (_cache[2] = ($event) => run("tasks/start", { kind: "check" })),
              disabled: !valid.value || busy.value || submitting.value
            }, " 检查连接与目录 ", 8, _hoisted_10),
            _createElementVNode("button", {
              class: "primary",
              onClick: _cache[3] || (_cache[3] = ($event) => run("tasks/start", { kind: "scan" })),
              disabled: !valid.value || busy.value || submitting.value
            }, _toDisplayString(currentPlan.value?.count ? "重新生成预览" : "生成预览"), 9, _hoisted_11),
            _createElementVNode("button", {
              class: "danger-button",
              onClick: prepare,
              disabled: !currentPlan.value?.valid || busy.value || submitting.value
            }, " 确认执行 " + _toDisplayString(currentPlan.value?.executable || 0) + " 个文件 ", 9, _hoisted_12)
          ]),
          !currentPlan.value?.valid ? (_openBlock(), _createElementBlock("p", _hoisted_13, _toDisplayString(currentPlan.value?.reason), 1)) : (_openBlock(), _createElementBlock("p", _hoisted_14, " 生成于 " + _toDisplayString(currentPlan.value.created_at) + " · 有效至 " + _toDisplayString(timeLabel(currentPlan.value.expires_at)) + "。执行全部待处理项，不仅是当前页。 ", 1)),
          prepared.value && !_unref(confirm) ? (_openBlock(), _createElementBlock("div", _hoisted_15, [
            _cache[17] || (_cache[17] = _createElementVNode("h3", null, "执行前确认", -1)),
            _createElementVNode("p", null, " 执行 " + _toDisplayString(prepared.value.count) + " 个文件，含失败重试 " + _toDisplayString(prepared.value.retry_count) + " 个；跳过 " + _toDisplayString(prepared.value.skip_count) + " 个。 ", 1),
            _createElementVNode("p", null, " 目标：" + _toDisplayString(prepared.value.targets.join("、")) + "。" + _toDisplayString(prepared.value.delete_empty_dirs ? "将清理成功整理来源中的空目录。" : "不清理空目录。") + " 已开始的移动无法一键撤销。 ", 1),
            _createElementVNode("button", {
              class: "danger-button",
              onClick: execute,
              disabled: submitting.value
            }, " 我已核对，确认执行", 8, _hoisted_16),
            _createElementVNode("button", {
              onClick: _cache[4] || (_cache[4] = ($event) => prepared.value = null)
            }, "取消")
          ])) : _createCommentVNode("", true),
          _createElementVNode("section", _hoisted_17, [
            _createElementVNode("b", null, _toDisplayString(_unref(stateLabels)[workflow.value.task.status] || workflow.value.task.status), 1),
            _createTextVNode(" · " + _toDisplayString(workflow.value.task.message) + " ", 1),
            busy.value && progress.value !== null ? (_openBlock(), _createElementBlock("progress", {
              key: 0,
              value: progress.value,
              max: "100",
              "aria-label": `任务进度 ${progress.value}%`
            }, null, 8, _hoisted_18)) : _createCommentVNode("", true),
            workflow.value.task.updated_at ? (_openBlock(), _createElementBlock("small", _hoisted_19, "最近活动 " + _toDisplayString(timeLabel(workflow.value.task.updated_at)) + _toDisplayString(workflow.value.task.discovered ? ` · 已检查 ${workflow.value.task.discovered} 条` : ""), 1)) : _createCommentVNode("", true),
            busy.value ? (_openBlock(), _createElementBlock("button", {
              key: 2,
              onClick: _cache[5] || (_cache[5] = ($event) => run("tasks/stop")),
              disabled: submitting.value || workflow.value.task.status === "stopping"
            }, " 完成当前批次后停止 ", 8, _hoisted_20)) : _createCommentVNode("", true),
            busy.value ? (_openBlock(), _createElementBlock("p", _hoisted_21, " 可以关闭页面，任务仍在后台运行；停止会保留已完成项目。 ")) : _createCommentVNode("", true)
          ]),
          result.value?.run_id ? (_openBlock(), _createElementBlock("div", _hoisted_22, [
            _cache[18] || (_cache[18] = _createElementVNode("b", null, "上次执行", -1)),
            _createElementVNode("span", null, "成功 " + _toDisplayString(result.value.success), 1),
            _createElementVNode("span", null, "失败 " + _toDisplayString(result.value.failed), 1),
            _createElementVNode("span", null, "跳过 " + _toDisplayString(result.value.skipped), 1),
            _createElementVNode("span", null, "剩余 " + _toDisplayString(result.value.remaining || 0), 1)
          ])) : _createCommentVNode("", true),
          workflow.value.scan_summary.limit_reached ? (_openBlock(), _createElementBlock("p", _hoisted_23, " 本次达到扫描上限，后面的文件可能尚未检查；整理本次后可再次生成预览，或调整单次上限。 ")) : _createCommentVNode("", true),
          workflow.value.scan_summary.record_count ? (_openBlock(), _createElementBlock("details", _hoisted_24, [
            _createElementVNode("summary", null, " 扫描说明：共 " + _toDisplayString(workflow.value.scan_summary.record_count) + " 条记录 ", 1),
            _createElementVNode("ul", null, [
              (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(workflow.value.scan_summary.counts, (count, reason) => {
                return _openBlock(), _createElementBlock("li", { key: reason }, _toDisplayString(reason) + "：" + _toDisplayString(count), 1);
              }), 128))
            ]),
            _cache[19] || (_cache[19] = _createElementVNode("p", null, "扫描诊断最多保留 5000 条，计数覆盖全部。", -1))
          ])) : _createCommentVNode("", true),
          _createElementVNode("div", _hoisted_25, [
            _createElementVNode("label", null, [
              _cache[21] || (_cache[21] = _createTextVNode("记录", -1)),
              _withDirectives(_createElementVNode("select", {
                "onUpdate:modelValue": _cache[6] || (_cache[6] = ($event) => kind.value = $event)
              }, [..._cache[20] || (_cache[20] = [
                _createElementVNode("option", { value: "plan" }, "本次预览", -1),
                _createElementVNode("option", { value: "scan" }, "扫描与跳过原因", -1),
                _createElementVNode("option", { value: "history" }, "整理历史", -1),
                _createElementVNode("option", { value: "runs" }, "执行批次", -1)
              ])], 512), [
                [_vModelSelect, kind.value]
              ])
            ]),
            _createElementVNode("label", null, [
              _cache[23] || (_cache[23] = _createTextVNode("状态", -1)),
              _withDirectives(_createElementVNode("select", {
                "onUpdate:modelValue": _cache[7] || (_cache[7] = ($event) => filter.value = $event)
              }, [..._cache[22] || (_cache[22] = [
                _createStaticVNode('<option value="" data-v-356064ff>全部</option><option value="planned" data-v-356064ff>待执行</option><option value="executed" data-v-356064ff>已执行</option><option value="failed" data-v-356064ff>失败</option><option value="skipped" data-v-356064ff>跳过</option>', 5)
              ])], 512), [
                [_vModelSelect, filter.value]
              ])
            ]),
            _createElementVNode("label", null, [
              _cache[24] || (_cache[24] = _createTextVNode("搜索", -1)),
              _withDirectives(_createElementVNode("input", {
                "onUpdate:modelValue": _cache[8] || (_cache[8] = ($event) => query.value = $event),
                placeholder: "文件名、路径、错误或批次 ID"
              }, null, 512), [
                [_vModelText, query.value]
              ])
            ])
          ]),
          pagination.value.total_pages > 1 ? (_openBlock(), _createElementBlock("nav", _hoisted_26, [
            _createElementVNode("button", {
              disabled: page.value <= 1,
              onClick: _cache[9] || (_cache[9] = ($event) => page.value--)
            }, "上一页", 8, _hoisted_27),
            _createElementVNode("span", null, "第 " + _toDisplayString(pagination.value.page) + " / " + _toDisplayString(pagination.value.total_pages) + " 页", 1),
            _createElementVNode("button", {
              disabled: page.value >= pagination.value.total_pages,
              onClick: _cache[10] || (_cache[10] = ($event) => page.value++)
            }, " 下一页 ", 8, _hoisted_28)
          ])) : _createCommentVNode("", true),
          records.value.length ? (_openBlock(), _createElementBlock("div", _hoisted_29, [
            (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(records.value, (r, i) => {
              return _openBlock(), _createElementBlock("article", {
                key: `${kind.value}-${page.value}-${i}`
              }, [
                _createElementVNode("header", null, [
                  _createElementVNode("b", null, _toDisplayString(_unref(stateLabels)[r.status] || (kind.value === "runs" ? "执行批次" : "记录")), 1),
                  _createElementVNode("time", null, _toDisplayString(r.time || r.created_at || ""), 1)
                ]),
                _createElementVNode("strong", _hoisted_30, _toDisplayString(name(r)), 1),
                r.title && r.source_name ? (_openBlock(), _createElementBlock("p", _hoisted_31, " 识别为：" + _toDisplayString(r.title) + " " + _toDisplayString(r.year || "") + " " + _toDisplayString(r.season ? `第 ${r.season} 季` : "") + " " + _toDisplayString(r.episode ? `第 ${r.episode} 集` : ""), 1)) : _createCommentVNode("", true),
                r.target_path ? (_openBlock(), _createElementBlock("p", _hoisted_32, "→ " + _toDisplayString(r.target_path), 1)) : r.target_name ? (_openBlock(), _createElementBlock("p", _hoisted_33, " → " + _toDisplayString(r.target_category) + " / " + _toDisplayString(r.target_name), 1)) : _createCommentVNode("", true),
                warnings(r) ? (_openBlock(), _createElementBlock("p", _hoisted_34, _toDisplayString(warnings(r)), 1)) : _createCommentVNode("", true),
                r.path_hint && kind.value === "scan" ? (_openBlock(), _createElementBlock("small", _hoisted_35, _toDisplayString(r.path_hint), 1)) : _createCommentVNode("", true),
                kind.value === "runs" ? (_openBlock(), _createElementBlock("p", _hoisted_36, " 成功 " + _toDisplayString(r.success) + " · 失败 " + _toDisplayString(r.failed) + " · 跳过 " + _toDisplayString(r.skipped) + "（共 " + _toDisplayString(r.total) + "） ", 1)) : _createCommentVNode("", true),
                r.run_id ? (_openBlock(), _createElementBlock("small", _hoisted_37, "批次 " + _toDisplayString(r.run_id), 1)) : _createCommentVNode("", true)
              ]);
            }), 128))
          ])) : (_openBlock(), _createElementBlock("p", _hoisted_38, " 暂无符合条件的记录。可切换记录类型或清除筛选。 ")),
          _createElementVNode("nav", _hoisted_39, [
            _createElementVNode("button", {
              disabled: page.value <= 1,
              onClick: _cache[11] || (_cache[11] = ($event) => page.value--)
            }, "上一页", 8, _hoisted_40),
            _createElementVNode("span", null, "第 " + _toDisplayString(pagination.value.page) + " / " + _toDisplayString(pagination.value.total_pages || 1) + " 页 · 共 " + _toDisplayString(pagination.value.total) + " 条", 1),
            _createElementVNode("button", {
              disabled: page.value >= pagination.value.total_pages,
              onClick: _cache[12] || (_cache[12] = ($event) => page.value++)
            }, " 下一页 ", 8, _hoisted_41)
          ])
        ], 64)) : (_openBlock(), _createElementBlock("p", _hoisted_42, "正在读取插件状态…"))
      ]);
    };
  }
});

const Page = /* @__PURE__ */ _export_sfc(_sfc_main, [["__scopeId", "data-v-356064ff"]]);

export { Page as default };
