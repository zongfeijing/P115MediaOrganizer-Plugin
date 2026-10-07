import { importShared } from './__federation_fn_import-JrT3xvdd.js';
import { i as icons, s as stateLabels, _ as _export_sfc, c as client } from './_plugin-vue_export-helper-CZk8cyVf.js';

const {defineComponent:_defineComponent$1} = await importShared('vue');

const {toDisplayString:_toDisplayString$1,createElementVNode:_createElementVNode$1,renderList:_renderList$1,Fragment:_Fragment$1,openBlock:_openBlock$1,createElementBlock:_createElementBlock$1,createCommentVNode:_createCommentVNode$1,normalizeClass:_normalizeClass$1,createTextVNode:_createTextVNode$1,resolveComponent:_resolveComponent$1,withCtx:_withCtx$1,createVNode:_createVNode$1,unref:_unref$1,createBlock:_createBlock$1} = await importShared('vue');

const _hoisted_1$1 = {
  key: 0,
  class: "p115-records"
};
const _hoisted_2$1 = { class: "p115-file" };
const _hoisted_3$1 = { class: "text-body-2 font-weight-medium" };
const _hoisted_4$1 = {
  key: 0,
  class: "text-caption text-medium-emphasis mt-1"
};
const _hoisted_5$1 = {
  key: 1,
  class: "text-caption text-medium-emphasis mt-1"
};
const _hoisted_6$1 = { class: "p115-target" };
const _hoisted_7$1 = {
  key: 0,
  class: "text-body-2"
};
const _hoisted_8$1 = {
  key: 0,
  class: "text-body-2"
};
const _hoisted_9$1 = {
  key: 1,
  class: "text-body-2"
};
const _hoisted_10$1 = { class: "text-caption text-medium-emphasis p115-time" };
const _hoisted_11$1 = { class: "p115-mobile" };
const _hoisted_12$1 = { class: "d-flex justify-space-between align-center ga-2 mb-2" };
const _hoisted_13$1 = { class: "text-caption text-medium-emphasis" };
const _hoisted_14$1 = { class: "text-body-2 font-weight-medium p115-wrap" };
const _hoisted_15$1 = {
  key: 0,
  class: "text-caption text-medium-emphasis mt-1"
};
const _hoisted_16$1 = {
  key: 1,
  class: "text-caption p115-wrap mt-2"
};
const _hoisted_17$1 = {
  key: 2,
  class: "text-body-2 mt-2"
};
const _sfc_main$1 = /* @__PURE__ */ _defineComponent$1({
  __name: "RecordList",
  props: {
    records: {},
    kind: {}
  },
  setup(__props) {
    function label(row) {
      return stateLabels[row.status] || "记录";
    }
    function color(row) {
      return {
        executed: "success",
        failed: "error",
        skipped: "warning",
        planned: "primary",
        cancelled: "secondary"
      }[row.status] || "secondary";
    }
    function name(row) {
      return row.source_name || row.title || row.run_id || row.path_hint || "记录";
    }
    function note(row) {
      return row.reason || row.error || (row.warnings || []).join("；");
    }
    function identity(row) {
      return [
        row.title,
        row.year,
        row.media_type === "tv" && row.season ? `第 ${row.season} 季` : "",
        row.media_type === "tv" && row.episode ? `第 ${row.episode} 集` : ""
      ].filter(Boolean).join(" · ");
    }
    return (_ctx, _cache) => {
      const _component_VChip = _resolveComponent$1("VChip");
      const _component_VTable = _resolveComponent$1("VTable");
      const _component_VIcon = _resolveComponent$1("VIcon");
      const _component_VCardText = _resolveComponent$1("VCardText");
      const _component_VCard = _resolveComponent$1("VCard");
      const _component_VSheet = _resolveComponent$1("VSheet");
      return __props.records.length ? (_openBlock$1(), _createElementBlock$1("div", _hoisted_1$1, [
        _createVNode$1(_component_VTable, {
          class: "p115-desktop",
          density: "compact",
          hover: ""
        }, {
          default: _withCtx$1(() => [
            _createElementVNode$1("thead", null, [
              _createElementVNode$1("tr", null, [
                _createElementVNode$1("th", null, _toDisplayString$1(__props.kind === "runs" ? "执行批次" : "文件 / 识别结果"), 1),
                _createElementVNode$1("th", null, _toDisplayString$1(__props.kind === "runs" ? "执行结果" : "目标位置 / 提示"), 1),
                _cache[0] || (_cache[0] = _createElementVNode$1("th", null, "状态", -1)),
                _cache[1] || (_cache[1] = _createElementVNode$1("th", null, "时间", -1))
              ])
            ]),
            _createElementVNode$1("tbody", null, [
              (_openBlock$1(true), _createElementBlock$1(_Fragment$1, null, _renderList$1(__props.records, (row, index) => {
                return _openBlock$1(), _createElementBlock$1("tr", { key: index }, [
                  _createElementVNode$1("td", _hoisted_2$1, [
                    _createElementVNode$1("div", _hoisted_3$1, _toDisplayString$1(name(row)), 1),
                    row.title && row.source_name ? (_openBlock$1(), _createElementBlock$1("div", _hoisted_4$1, _toDisplayString$1(identity(row)), 1)) : _createCommentVNode$1("", true),
                    __props.kind === "scan" && row.path_hint ? (_openBlock$1(), _createElementBlock$1("div", _hoisted_5$1, _toDisplayString$1(row.path_hint), 1)) : _createCommentVNode$1("", true)
                  ]),
                  _createElementVNode$1("td", _hoisted_6$1, [
                    __props.kind === "runs" ? (_openBlock$1(), _createElementBlock$1("div", _hoisted_7$1, " 成功 " + _toDisplayString$1(row.success) + " · 失败 " + _toDisplayString$1(row.failed) + " · 跳过 " + _toDisplayString$1(row.skipped), 1)) : (_openBlock$1(), _createElementBlock$1(_Fragment$1, { key: 1 }, [
                      row.target_path ? (_openBlock$1(), _createElementBlock$1("div", _hoisted_8$1, _toDisplayString$1(row.target_path), 1)) : row.target_name ? (_openBlock$1(), _createElementBlock$1("div", _hoisted_9$1, _toDisplayString$1(row.target_category) + " / " + _toDisplayString$1(row.target_name), 1)) : _createCommentVNode$1("", true),
                      note(row) ? (_openBlock$1(), _createElementBlock$1("div", {
                        key: 2,
                        class: _normalizeClass$1([
                          "text-caption mt-1",
                          row.status === "failed" ? "text-error" : "text-medium-emphasis"
                        ])
                      }, _toDisplayString$1(note(row)), 3)) : _createCommentVNode$1("", true)
                    ], 64))
                  ]),
                  _createElementVNode$1("td", null, [
                    _createVNode$1(_component_VChip, {
                      color: color(row),
                      size: "x-small",
                      variant: "tonal"
                    }, {
                      default: _withCtx$1(() => [
                        _createTextVNode$1(_toDisplayString$1(label(row)), 1)
                      ]),
                      _: 2
                    }, 1032, ["color"])
                  ]),
                  _createElementVNode$1("td", _hoisted_10$1, _toDisplayString$1(row.time || row.created_at || "—"), 1)
                ]);
              }), 128))
            ])
          ]),
          _: 1
        }),
        _createElementVNode$1("div", _hoisted_11$1, [
          (_openBlock$1(true), _createElementBlock$1(_Fragment$1, null, _renderList$1(__props.records, (row, index) => {
            return _openBlock$1(), _createBlock$1(_component_VCard, {
              key: index,
              variant: "tonal",
              class: "mb-3"
            }, {
              default: _withCtx$1(() => [
                _createVNode$1(_component_VCardText, { class: "pa-3" }, {
                  default: _withCtx$1(() => [
                    _createElementVNode$1("div", _hoisted_12$1, [
                      _createVNode$1(_component_VChip, {
                        color: color(row),
                        size: "x-small",
                        variant: "tonal"
                      }, {
                        default: _withCtx$1(() => [
                          _createTextVNode$1(_toDisplayString$1(label(row)), 1)
                        ]),
                        _: 2
                      }, 1032, ["color"]),
                      _createElementVNode$1("span", _hoisted_13$1, _toDisplayString$1(row.time || row.created_at || ""), 1)
                    ]),
                    _createElementVNode$1("div", _hoisted_14$1, _toDisplayString$1(name(row)), 1),
                    row.title && row.source_name ? (_openBlock$1(), _createElementBlock$1("div", _hoisted_15$1, _toDisplayString$1(identity(row)), 1)) : _createCommentVNode$1("", true),
                    row.target_path || row.target_name ? (_openBlock$1(), _createElementBlock$1("div", _hoisted_16$1, [
                      _createVNode$1(_component_VIcon, {
                        icon: _unref$1(icons).mdiArrowRight,
                        size: "14",
                        class: "me-1"
                      }, null, 8, ["icon"]),
                      _createTextVNode$1(_toDisplayString$1(row.target_path || `${row.target_category || ""} / ${row.target_name}`), 1)
                    ])) : _createCommentVNode$1("", true),
                    __props.kind === "runs" ? (_openBlock$1(), _createElementBlock$1("div", _hoisted_17$1, " 成功 " + _toDisplayString$1(row.success) + " · 失败 " + _toDisplayString$1(row.failed) + " · 跳过 " + _toDisplayString$1(row.skipped), 1)) : _createCommentVNode$1("", true),
                    note(row) ? (_openBlock$1(), _createElementBlock$1("div", {
                      key: 3,
                      class: _normalizeClass$1([
                        "text-caption p115-wrap mt-2",
                        row.status === "failed" ? "text-error" : "text-medium-emphasis"
                      ])
                    }, _toDisplayString$1(note(row)), 3)) : _createCommentVNode$1("", true)
                  ]),
                  _: 2
                }, 1024)
              ]),
              _: 2
            }, 1024);
          }), 128))
        ])
      ])) : (_openBlock$1(), _createBlock$1(_component_VSheet, {
        key: 1,
        rounded: "lg",
        class: "pa-8 text-center"
      }, {
        default: _withCtx$1(() => [
          _createVNode$1(_component_VIcon, {
            icon: _unref$1(icons).mdiFolderSearchOutline,
            color: "secondary",
            size: "32",
            class: "mb-3"
          }, null, 8, ["icon"]),
          _cache[2] || (_cache[2] = _createElementVNode$1("div", { class: "text-body-2 text-medium-emphasis" }, "暂无符合条件的记录", -1)),
          _cache[3] || (_cache[3] = _createElementVNode$1("div", { class: "text-caption text-medium-emphasis mt-1" }, " 可以切换记录类型或清除筛选。 ", -1))
        ]),
        _: 1
      }));
    };
  }
});

const RecordList = /* @__PURE__ */ _export_sfc(_sfc_main$1, [["__scopeId", "data-v-d5aff0ce"]]);

const {defineComponent:_defineComponent} = await importShared('vue');

const {unref:_unref,resolveComponent:_resolveComponent,createVNode:_createVNode,withCtx:_withCtx,createElementVNode:_createElementVNode,mergeProps:_mergeProps,toDisplayString:_toDisplayString,createTextVNode:_createTextVNode,openBlock:_openBlock,createBlock:_createBlock,createCommentVNode:_createCommentVNode,renderList:_renderList,Fragment:_Fragment,createElementBlock:_createElementBlock,normalizeClass:_normalizeClass} = await importShared('vue');

const _hoisted_1 = { class: "p115-page pa-4 pa-sm-6" };
const _hoisted_2 = { class: "d-flex align-center ga-3 mb-4" };
const _hoisted_3 = { class: "ps-4 my-2" };
const _hoisted_4 = { class: "d-flex align-center flex-wrap ga-2 mb-4" };
const _hoisted_5 = { class: "text-body-2 mb-2" };
const _hoisted_6 = { class: "text-caption text-medium-emphasis mb-3" };
const _hoisted_7 = { class: "p115-path" };
const _hoisted_8 = { class: "p115-stat" };
const _hoisted_9 = { class: "text-h5 text-primary" };
const _hoisted_10 = { class: "p115-stat" };
const _hoisted_11 = { class: "text-h5" };
const _hoisted_12 = { class: "p115-stat" };
const _hoisted_13 = { class: "d-flex flex-wrap align-center ga-2 mb-2" };
const _hoisted_14 = {
  key: 1,
  class: "text-caption text-medium-emphasis"
};
const _hoisted_15 = {
  key: 3,
  class: "text-caption text-medium-emphasis mb-4"
};
const _hoisted_16 = {
  key: 4,
  class: "text-caption text-medium-emphasis mb-4"
};
const _hoisted_17 = {
  key: 5,
  class: "text-caption text-medium-emphasis mb-4"
};
const _hoisted_18 = { class: "p115-path mt-2" };
const _hoisted_19 = { class: "d-flex align-center ga-2 mb-2" };
const _hoisted_20 = { class: "text-body-2 p115-path" };
const _hoisted_21 = { class: "d-flex flex-wrap align-center ga-2" };
const _hoisted_22 = { class: "text-caption text-medium-emphasis" };
const _hoisted_23 = {
  key: 1,
  class: "text-caption text-medium-emphasis mt-2"
};
const _hoisted_24 = {
  key: 8,
  class: "text-caption text-medium-emphasis mb-4"
};
const _hoisted_25 = { class: "d-flex flex-wrap ga-2 mb-2" };
const _hoisted_26 = { class: "p115-pagination d-flex flex-wrap align-center justify-center ga-2 mt-4" };
const _hoisted_27 = { class: "text-caption text-medium-emphasis" };
const _hoisted_28 = {
  key: 11,
  class: "text-caption text-medium-emphasis mt-4"
};
const _hoisted_29 = {
  key: 2,
  class: "d-flex align-center justify-center ga-3 py-10"
};
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
          query: query.value || "",
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
    const connectionDetails = ref(false);
    const tabs = [
      { value: "plan", title: "本次预览" },
      { value: "history", title: "整理历史" },
      { value: "runs", title: "执行批次" },
      { value: "scan", title: "扫描诊断" }
    ];
    const statusOptions = [
      { title: "全部状态", value: "" },
      { title: "待执行", value: "planned" },
      { title: "已执行", value: "executed" },
      { title: "失败", value: "failed" },
      { title: "跳过", value: "skipped" },
      { title: "已停止", value: "cancelled" }
    ];
    const connectionColor = computed(
      () => workflow.value?.connection?.ok === true ? "success" : ["login", "dependency"].includes(workflow.value?.connection?.kind) ? "error" : "warning"
    );
    const connectionLabel = computed(
      () => workflow.value?.connection?.ok === true ? "连接正常" : ["login", "dependency"].includes(workflow.value?.connection?.kind) ? "连接不可用" : "连接待检查"
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
    function timeLabel(epoch) {
      return epoch ? new Date(epoch * 1e3).toLocaleString("zh-CN") : "—";
    }
    return (_ctx, _cache) => {
      const _component_VIcon = _resolveComponent("VIcon");
      const _component_VAvatar = _resolveComponent("VAvatar");
      const _component_VBtn = _resolveComponent("VBtn");
      const _component_VTooltip = _resolveComponent("VTooltip");
      const _component_VAlert = _resolveComponent("VAlert");
      const _component_VChip = _resolveComponent("VChip");
      const _component_VSpacer = _resolveComponent("VSpacer");
      const _component_VCardText = _resolveComponent("VCardText");
      const _component_VCard = _resolveComponent("VCard");
      const _component_VCol = _resolveComponent("VCol");
      const _component_VRow = _resolveComponent("VRow");
      const _component_VCardActions = _resolveComponent("VCardActions");
      const _component_VProgressLinear = _resolveComponent("VProgressLinear");
      const _component_VTab = _resolveComponent("VTab");
      const _component_VTabs = _resolveComponent("VTabs");
      const _component_VTextField = _resolveComponent("VTextField");
      const _component_VSelect = _resolveComponent("VSelect");
      const _component_VExpansionPanelText = _resolveComponent("VExpansionPanelText");
      const _component_VExpansionPanel = _resolveComponent("VExpansionPanel");
      const _component_VExpansionPanels = _resolveComponent("VExpansionPanels");
      const _component_VPagination = _resolveComponent("VPagination");
      const _component_VProgressCircular = _resolveComponent("VProgressCircular");
      return _openBlock(), _createElementBlock("section", _hoisted_1, [
        _createElementVNode("div", _hoisted_2, [
          _createVNode(_component_VAvatar, {
            color: "primary",
            variant: "tonal",
            rounded: "lg",
            size: "42"
          }, {
            default: _withCtx(() => [
              _createVNode(_component_VIcon, {
                icon: _unref(icons).mdiCloudCheckOutline
              }, null, 8, ["icon"])
            ]),
            _: 1
          }),
          _cache[14] || (_cache[14] = _createElementVNode("div", { class: "flex-grow-1 min-width-0" }, [
            _createElementVNode("h2", { class: "text-h6" }, "115 云端媒体整理"),
            _createElementVNode("div", { class: "text-caption text-medium-emphasis" }, " 在云端整理媒体，不下载文件 ")
          ], -1)),
          _createVNode(_component_VTooltip, { text: "配置" }, {
            activator: _withCtx(({ props: tip }) => [
              _createVNode(_component_VBtn, _mergeProps(tip, {
                icon: _unref(icons).mdiCogOutline,
                variant: "text",
                color: "secondary",
                size: "small",
                "aria-label": "配置",
                disabled: busy.value,
                onClick: _cache[0] || (_cache[0] = ($event) => emit("switch"))
              }), null, 16, ["icon", "disabled"])
            ]),
            _: 1
          }),
          _createVNode(_component_VTooltip, { text: "刷新状态" }, {
            activator: _withCtx(({ props: tip }) => [
              _createVNode(_component_VBtn, _mergeProps(tip, {
                icon: _unref(icons).mdiRefresh,
                variant: "text",
                color: "secondary",
                size: "small",
                "aria-label": "刷新状态",
                loading: loading.value,
                onClick: refresh
              }), null, 16, ["icon", "loading"])
            ]),
            _: 1
          }),
          _createVNode(_component_VTooltip, { text: "关闭" }, {
            activator: _withCtx(({ props: tip }) => [
              _createVNode(_component_VBtn, _mergeProps(tip, {
                icon: _unref(icons).mdiClose,
                variant: "text",
                color: "secondary",
                size: "small",
                "aria-label": "关闭",
                onClick: _cache[1] || (_cache[1] = ($event) => emit("close"))
              }), null, 16, ["icon"])
            ]),
            _: 1
          })
        ]),
        error.value ? (_openBlock(), _createBlock(_component_VAlert, {
          key: 0,
          type: "error",
          variant: "tonal",
          density: "compact",
          class: "mb-4",
          closable: "",
          role: "alert",
          "onClick:close": _cache[2] || (_cache[2] = ($event) => error.value = "")
        }, {
          default: _withCtx(() => [
            _createTextVNode(_toDisplayString(error.value), 1)
          ]),
          _: 1
        })) : _createCommentVNode("", true),
        workflow.value ? (_openBlock(), _createElementBlock(_Fragment, { key: 1 }, [
          !valid.value ? (_openBlock(), _createBlock(_component_VAlert, {
            key: 0,
            type: "warning",
            variant: "tonal",
            density: "compact",
            class: "mb-4",
            role: "alert"
          }, {
            default: _withCtx(() => [
              _cache[16] || (_cache[16] = _createElementVNode("div", { class: "font-weight-medium" }, "完成配置后再生成预览", -1)),
              _createElementVNode("ul", _hoisted_3, [
                (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(workflow.value.configuration.errors, (e) => {
                  return _openBlock(), _createElementBlock("li", { key: e }, _toDisplayString(e), 1);
                }), 128))
              ]),
              _createVNode(_component_VBtn, {
                size: "small",
                variant: "tonal",
                onClick: _cache[3] || (_cache[3] = ($event) => emit("switch"))
              }, {
                default: _withCtx(() => [..._cache[15] || (_cache[15] = [
                  _createTextVNode("去配置", -1)
                ])]),
                _: 1
              })
            ]),
            _: 1
          })) : _createCommentVNode("", true),
          _createElementVNode("div", _hoisted_4, [
            _createVNode(_component_VChip, {
              color: connectionColor.value,
              size: "small",
              variant: "tonal",
              "prepend-icon": workflow.value.connection.ok === true ? _unref(icons).mdiCheckCircleOutline : _unref(icons).mdiCloudAlertOutline
            }, {
              default: _withCtx(() => [
                _createTextVNode(_toDisplayString(connectionLabel.value), 1)
              ]),
              _: 1
            }, 8, ["color", "prepend-icon"]),
            _createVNode(_component_VChip, {
              size: "small",
              color: "secondary",
              variant: "tonal",
              "prepend-icon": _unref(icons).mdiCalendarClock
            }, {
              default: _withCtx(() => [
                _createTextVNode(_toDisplayString(workflow.value.configuration.preview_only ? "定时仅预览" : "定时自动执行"), 1)
              ]),
              _: 1
            }, 8, ["prepend-icon"]),
            _createVNode(_component_VSpacer),
            _createVNode(_component_VBtn, {
              size: "small",
              color: "secondary",
              variant: "text",
              "append-icon": connectionDetails.value ? _unref(icons).mdiChevronUp : _unref(icons).mdiChevronDown,
              onClick: _cache[4] || (_cache[4] = ($event) => connectionDetails.value = !connectionDetails.value)
            }, {
              default: _withCtx(() => [..._cache[17] || (_cache[17] = [
                _createTextVNode("连接详情", -1)
              ])]),
              _: 1
            }, 8, ["append-icon"])
          ]),
          ["login", "dependency", "network", "rate_limit"].includes(
            workflow.value.connection.kind
          ) ? (_openBlock(), _createBlock(_component_VAlert, {
            key: 1,
            type: connectionColor.value === "error" ? "error" : "warning",
            variant: "tonal",
            density: "compact",
            class: "mb-4"
          }, {
            default: _withCtx(() => [
              _createTextVNode(_toDisplayString(workflow.value.connection.message), 1)
            ]),
            _: 1
          }, 8, ["type"])) : _createCommentVNode("", true),
          connectionDetails.value ? (_openBlock(), _createBlock(_component_VCard, {
            key: 2,
            variant: "tonal",
            class: "mb-4"
          }, {
            default: _withCtx(() => [
              _createVNode(_component_VCardText, { class: "pa-4" }, {
                default: _withCtx(() => [
                  _createElementVNode("div", _hoisted_5, _toDisplayString(workflow.value.connection.message), 1),
                  _createElementVNode("div", _hoisted_6, _toDisplayString(workflow.value.configuration.cookie_mode === "text" ? "使用 Cookie 文本" : "使用 Cookie 文件") + " · 客户端 " + _toDisplayString(workflow.value.versions.p115client || "未安装") + " · 并发库 " + _toDisplayString(workflow.value.versions["python-concurrenttools"] || "未安装"), 1),
                  (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(workflow.value.path_checks || [], (r) => {
                    return _openBlock(), _createElementBlock("div", {
                      key: r.path,
                      class: "d-flex align-start ga-2 mb-2 text-body-2"
                    }, [
                      _createVNode(_component_VIcon, {
                        icon: r.ok ? _unref(icons).mdiCheckCircleOutline : _unref(icons).mdiAlertCircleOutline,
                        color: r.ok ? "success" : "warning",
                        size: "18"
                      }, null, 8, ["icon", "color"]),
                      _createElementVNode("span", _hoisted_7, _toDisplayString(r.path) + " " + _toDisplayString(r.message || ""), 1)
                    ]);
                  }), 128)),
                  _createVNode(_component_VBtn, {
                    variant: "tonal",
                    size: "small",
                    "prepend-icon": _unref(icons).mdiConnection,
                    disabled: !valid.value || !canMutate.value,
                    loading: submitting.value,
                    onClick: _cache[5] || (_cache[5] = ($event) => run("tasks/start", { kind: "check" }))
                  }, {
                    default: _withCtx(() => [..._cache[18] || (_cache[18] = [
                      _createTextVNode("检查连接与目录", -1)
                    ])]),
                    _: 1
                  }, 8, ["prepend-icon", "disabled", "loading"])
                ]),
                _: 1
              })
            ]),
            _: 1
          })) : _createCommentVNode("", true),
          _createVNode(_component_VRow, {
            dense: "",
            class: "mb-4"
          }, {
            default: _withCtx(() => [
              _createVNode(_component_VCol, { cols: "4" }, {
                default: _withCtx(() => [
                  _createElementVNode("div", _hoisted_8, [
                    _cache[19] || (_cache[19] = _createElementVNode("div", { class: "text-caption text-medium-emphasis" }, "待执行", -1)),
                    _createElementVNode("div", _hoisted_9, _toDisplayString(currentPlan.value?.executable || 0), 1)
                  ])
                ]),
                _: 1
              }),
              _createVNode(_component_VCol, { cols: "4" }, {
                default: _withCtx(() => [
                  _createElementVNode("div", _hoisted_10, [
                    _cache[20] || (_cache[20] = _createElementVNode("div", { class: "text-caption text-medium-emphasis" }, "已完成", -1)),
                    _createElementVNode("div", _hoisted_11, _toDisplayString(currentPlan.value?.counts?.executed || 0), 1)
                  ])
                ]),
                _: 1
              }),
              _createVNode(_component_VCol, { cols: "4" }, {
                default: _withCtx(() => [
                  _createElementVNode("div", _hoisted_12, [
                    _cache[21] || (_cache[21] = _createElementVNode("div", { class: "text-caption text-medium-emphasis" }, "需处理", -1)),
                    _createElementVNode("div", {
                      class: _normalizeClass(["text-h5", currentPlan.value?.counts?.failed || 0 ? "text-warning" : ""])
                    }, _toDisplayString(currentPlan.value?.counts?.failed || 0), 3)
                  ])
                ]),
                _: 1
              })
            ]),
            _: 1
          }),
          _createElementVNode("div", _hoisted_13, [
            _createVNode(_component_VBtn, {
              color: "primary",
              variant: "flat",
              "prepend-icon": hasPlan.value ? _unref(icons).mdiPlayOutline : _unref(icons).mdiFileSearchOutline,
              loading: submitting.value,
              disabled: !valid.value || !canMutate.value,
              onClick: primaryAction
            }, {
              default: _withCtx(() => [
                _createTextVNode(_toDisplayString(hasPlan.value ? `确认执行 ${currentPlan.value.executable} 个文件` : currentPlan.value?.count ? "重新生成预览" : "生成预览"), 1)
              ]),
              _: 1
            }, 8, ["prepend-icon", "loading", "disabled"]),
            hasPlan.value ? (_openBlock(), _createBlock(_component_VBtn, {
              key: 0,
              variant: "tonal",
              color: "secondary",
              "prepend-icon": _unref(icons).mdiRefresh,
              disabled: !canMutate.value,
              onClick: _cache[6] || (_cache[6] = ($event) => run("tasks/start", { kind: "scan" }))
            }, {
              default: _withCtx(() => [..._cache[22] || (_cache[22] = [
                _createTextVNode("重新生成预览", -1)
              ])]),
              _: 1
            }, 8, ["prepend-icon", "disabled"])) : _createCommentVNode("", true),
            !valid.value ? (_openBlock(), _createElementBlock("span", _hoisted_14, "配置 → 预览 → 确认")) : _createCommentVNode("", true)
          ]),
          currentPlan.value?.count && !currentPlan.value.valid ? (_openBlock(), _createElementBlock("p", _hoisted_15, _toDisplayString(currentPlan.value.reason), 1)) : currentPlan.value?.valid ? (_openBlock(), _createElementBlock("p", _hoisted_16, " 生成于 " + _toDisplayString(currentPlan.value.created_at) + " · 有效至 " + _toDisplayString(timeLabel(currentPlan.value.expires_at)) + "。执行全部有效项目，不仅是当前页。 ", 1)) : (_openBlock(), _createElementBlock("p", _hoisted_17, " 先生成预览，核对名称与目标目录，再确认执行。 ")),
          prepared.value && !_unref(confirm) ? (_openBlock(), _createBlock(_component_VCard, {
            key: 6,
            variant: "tonal",
            color: "warning",
            class: "mb-4",
            role: "alertdialog",
            "aria-label": "执行确认"
          }, {
            default: _withCtx(() => [
              _createVNode(_component_VCardText, null, {
                default: _withCtx(() => [
                  _cache[23] || (_cache[23] = _createElementVNode("div", { class: "text-subtitle-1 font-weight-medium mb-2" }, "执行前确认", -1)),
                  _createElementVNode("p", null, " 执行 " + _toDisplayString(prepared.value.count) + " 个文件，含失败重试 " + _toDisplayString(prepared.value.retry_count) + " 个；跳过 " + _toDisplayString(prepared.value.skip_count) + " 个。 ", 1),
                  _createElementVNode("p", _hoisted_18, " 目标：" + _toDisplayString(prepared.value.targets.join("、")) + "。" + _toDisplayString(prepared.value.delete_empty_dirs ? "将清理成功整理来源中的空目录。" : "不清理空目录。"), 1),
                  _cache[24] || (_cache[24] = _createElementVNode("p", { class: "text-caption mt-2" }, " 已开始的移动无法一键撤销；定时运行模式不会改变。 ", -1))
                ]),
                _: 1
              }),
              _createVNode(_component_VCardActions, null, {
                default: _withCtx(() => [
                  _createVNode(_component_VSpacer),
                  _createVNode(_component_VBtn, {
                    variant: "text",
                    color: "secondary",
                    onClick: _cache[7] || (_cache[7] = ($event) => prepared.value = null)
                  }, {
                    default: _withCtx(() => [..._cache[25] || (_cache[25] = [
                      _createTextVNode("取消", -1)
                    ])]),
                    _: 1
                  }),
                  _createVNode(_component_VBtn, {
                    color: "primary",
                    variant: "flat",
                    loading: submitting.value,
                    onClick: execute
                  }, {
                    default: _withCtx(() => [..._cache[26] || (_cache[26] = [
                      _createTextVNode("我已核对，确认执行", -1)
                    ])]),
                    _: 1
                  }, 8, ["loading"])
                ]),
                _: 1
              })
            ]),
            _: 1
          })) : _createCommentVNode("", true),
          busy.value || ["failed", "cancelled"].includes(workflow.value.task.status) ? (_openBlock(), _createBlock(_component_VCard, {
            key: 7,
            variant: "tonal",
            class: "mb-4",
            "aria-live": "polite"
          }, {
            default: _withCtx(() => [
              _createVNode(_component_VCardText, null, {
                default: _withCtx(() => [
                  _createElementVNode("div", _hoisted_19, [
                    _createVNode(_component_VChip, {
                      size: "small",
                      color: workflow.value.task.status === "failed" ? "error" : "primary"
                    }, {
                      default: _withCtx(() => [
                        _createTextVNode(_toDisplayString(_unref(stateLabels)[workflow.value.task.status] || workflow.value.task.status), 1)
                      ]),
                      _: 1
                    }, 8, ["color"]),
                    _createElementVNode("span", _hoisted_20, _toDisplayString(workflow.value.task.message), 1)
                  ]),
                  busy.value ? (_openBlock(), _createBlock(_component_VProgressLinear, {
                    key: 0,
                    "model-value": progress.value || 0,
                    indeterminate: progress.value === null,
                    color: "primary",
                    rounded: "",
                    height: "6",
                    class: "my-3",
                    "aria-label": `任务进度 ${progress.value ?? 0}%`
                  }, null, 8, ["model-value", "indeterminate", "aria-label"])) : _createCommentVNode("", true),
                  _createElementVNode("div", _hoisted_21, [
                    _createElementVNode("span", _hoisted_22, "最近活动 " + _toDisplayString(timeLabel(workflow.value.task.updated_at)) + _toDisplayString(workflow.value.task.discovered ? ` · 已检查 ${workflow.value.task.discovered} 条` : ""), 1),
                    _createVNode(_component_VSpacer),
                    busy.value ? (_openBlock(), _createBlock(_component_VBtn, {
                      key: 0,
                      variant: "text",
                      color: "warning",
                      size: "small",
                      "prepend-icon": _unref(icons).mdiStopCircleOutline,
                      disabled: submitting.value || workflow.value.task.status === "stopping",
                      onClick: _cache[8] || (_cache[8] = ($event) => run("tasks/stop"))
                    }, {
                      default: _withCtx(() => [..._cache[27] || (_cache[27] = [
                        _createTextVNode("完成当前批次后停止", -1)
                      ])]),
                      _: 1
                    }, 8, ["prepend-icon", "disabled"])) : _createCommentVNode("", true)
                  ]),
                  busy.value ? (_openBlock(), _createElementBlock("div", _hoisted_23, " 可关闭页面，任务仍在后台运行；停止会保留已完成项目。 ")) : _createCommentVNode("", true)
                ]),
                _: 1
              })
            ]),
            _: 1
          })) : workflow.value.task.status === "completed" ? (_openBlock(), _createElementBlock("div", _hoisted_24, [
            _createVNode(_component_VIcon, {
              icon: _unref(icons).mdiCheckCircleOutline,
              color: "success",
              size: "16",
              class: "me-1"
            }, null, 8, ["icon"]),
            _createTextVNode(_toDisplayString(workflow.value.task.message), 1)
          ])) : _createCommentVNode("", true),
          workflow.value.scan_summary.limit_reached ? (_openBlock(), _createBlock(_component_VAlert, {
            key: 9,
            type: "info",
            variant: "tonal",
            density: "compact",
            class: "mb-4"
          }, {
            default: _withCtx(() => [..._cache[28] || (_cache[28] = [
              _createTextVNode("本次达到扫描上限，后面的文件可能尚未检查；整理后可再次生成预览。", -1)
            ])]),
            _: 1
          })) : _createCommentVNode("", true),
          _createVNode(_component_VTabs, {
            modelValue: kind.value,
            "onUpdate:modelValue": _cache[9] || (_cache[9] = ($event) => kind.value = $event),
            density: "comfortable",
            "show-arrows": "",
            class: "mb-4"
          }, {
            default: _withCtx(() => [
              (_openBlock(), _createElementBlock(_Fragment, null, _renderList(tabs, (tab) => {
                return _createVNode(_component_VTab, {
                  key: tab.value,
                  value: tab.value
                }, {
                  default: _withCtx(() => [
                    _createTextVNode(_toDisplayString(tab.title), 1)
                  ]),
                  _: 2
                }, 1032, ["value"]);
              }), 64))
            ]),
            _: 1
          }, 8, ["modelValue"]),
          _createVNode(_component_VRow, {
            dense: "",
            class: "mb-3"
          }, {
            default: _withCtx(() => [
              _createVNode(_component_VCol, {
                cols: "12",
                sm: "8"
              }, {
                default: _withCtx(() => [
                  _createVNode(_component_VTextField, {
                    modelValue: query.value,
                    "onUpdate:modelValue": _cache[10] || (_cache[10] = ($event) => query.value = $event),
                    density: "compact",
                    label: "搜索记录",
                    placeholder: "文件名、路径、错误或批次 ID",
                    "prepend-inner-icon": _unref(icons).mdiMagnify,
                    clearable: "",
                    "hide-details": "",
                    "onClick:clear": _cache[11] || (_cache[11] = ($event) => query.value = "")
                  }, null, 8, ["modelValue", "prepend-inner-icon"])
                ]),
                _: 1
              }),
              _createVNode(_component_VCol, {
                cols: "12",
                sm: "4"
              }, {
                default: _withCtx(() => [
                  _createVNode(_component_VSelect, {
                    modelValue: filter.value,
                    "onUpdate:modelValue": _cache[12] || (_cache[12] = ($event) => filter.value = $event),
                    items: statusOptions,
                    label: "状态",
                    density: "compact",
                    "hide-details": ""
                  }, null, 8, ["modelValue"])
                ]),
                _: 1
              })
            ]),
            _: 1
          }),
          kind.value === "scan" && workflow.value.scan_summary.record_count ? (_openBlock(), _createBlock(_component_VExpansionPanels, {
            key: 10,
            variant: "accordion",
            class: "mb-4"
          }, {
            default: _withCtx(() => [
              _createVNode(_component_VExpansionPanel, { title: "扫描统计" }, {
                default: _withCtx(() => [
                  _createVNode(_component_VExpansionPanelText, null, {
                    default: _withCtx(() => [
                      _createElementVNode("div", _hoisted_25, [
                        (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(workflow.value.scan_summary.counts, (count, reason) => {
                          return _openBlock(), _createBlock(_component_VChip, {
                            key: reason,
                            size: "small",
                            variant: "tonal"
                          }, {
                            default: _withCtx(() => [
                              _createTextVNode(_toDisplayString(reason) + " · " + _toDisplayString(count), 1)
                            ]),
                            _: 2
                          }, 1024);
                        }), 128))
                      ]),
                      _cache[29] || (_cache[29] = _createElementVNode("p", { class: "text-caption text-medium-emphasis" }, " 诊断最多保留 5000 条，汇总计数覆盖全部。 ", -1))
                    ]),
                    _: 1
                  })
                ]),
                _: 1
              })
            ]),
            _: 1
          })) : _createCommentVNode("", true),
          _createVNode(RecordList, {
            records: records.value,
            kind: kind.value
          }, null, 8, ["records", "kind"]),
          _createElementVNode("div", _hoisted_26, [
            _createElementVNode("span", _hoisted_27, "共 " + _toDisplayString(pagination.value.total) + " 条 · 第 " + _toDisplayString(pagination.value.page) + " / " + _toDisplayString(pagination.value.total_pages || 1) + " 页", 1),
            _createVNode(_component_VPagination, {
              modelValue: page.value,
              "onUpdate:modelValue": _cache[13] || (_cache[13] = ($event) => page.value = $event),
              length: pagination.value.total_pages || 1,
              "total-visible": 3,
              density: "compact",
              disabled: loading.value,
              "aria-label": "记录分页"
            }, null, 8, ["modelValue", "length", "disabled"])
          ]),
          result.value?.run_id ? (_openBlock(), _createElementBlock("div", _hoisted_28, " 上次执行：成功 " + _toDisplayString(result.value.success) + " · 失败 " + _toDisplayString(result.value.failed) + " · 跳过 " + _toDisplayString(result.value.skipped) + " · 剩余 " + _toDisplayString(result.value.remaining || 0), 1)) : _createCommentVNode("", true)
        ], 64)) : (_openBlock(), _createElementBlock("div", _hoisted_29, [
          _createVNode(_component_VProgressCircular, {
            indeterminate: "",
            size: "24",
            width: "2",
            color: "primary"
          }),
          _cache[30] || (_cache[30] = _createElementVNode("span", { class: "text-body-2 text-medium-emphasis" }, "正在读取插件状态…", -1))
        ]))
      ]);
    };
  }
});

const Page = /* @__PURE__ */ _export_sfc(_sfc_main, [["__scopeId", "data-v-6bc1f89e"]]);

export { Page as default };
