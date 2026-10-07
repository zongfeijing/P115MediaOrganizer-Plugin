import { importShared } from './__federation_fn_import-JrT3xvdd.js';
import { c as client, i as icons, _ as _export_sfc } from './_plugin-vue_export-helper-CZk8cyVf.js';

const {defineComponent:_defineComponent} = await importShared('vue');

const {unref:_unref,resolveComponent:_resolveComponent,createVNode:_createVNode,withCtx:_withCtx,createElementVNode:_createElementVNode,createTextVNode:_createTextVNode,renderList:_renderList,Fragment:_Fragment,openBlock:_openBlock,createElementBlock:_createElementBlock,toDisplayString:_toDisplayString,createBlock:_createBlock,createCommentVNode:_createCommentVNode,mergeProps:_mergeProps,withModifiers:_withModifiers} = await importShared('vue');

const _hoisted_1 = { class: "px-4 px-sm-6 pt-5 pb-4 d-flex align-center ga-3" };
const _hoisted_2 = { class: "pa-4 pa-sm-6" };
const _hoisted_3 = { class: "ps-4" };
const _hoisted_4 = { class: "d-flex align-center flex-wrap ga-2 mb-3" };
const _hoisted_5 = { class: "d-flex align-center ga-2 px-4 pt-3" };
const _hoisted_6 = { class: "text-subtitle-2 flex-grow-1" };
const _hoisted_7 = { class: "d-flex justify-end ga-2 mt-2" };
const _hoisted_8 = { class: "p115-wrap flex-grow-1" };
const _hoisted_9 = { class: "d-flex justify-end ga-2 mt-3" };
const _hoisted_10 = { class: "p115-config-footer" };
const {computed,inject,onMounted,ref} = await importShared('vue');
const _sfc_main = /* @__PURE__ */ _defineComponent({
  __name: "Config",
  props: {
    api: {},
    pluginId: {},
    sourcePluginId: {},
    initialConfig: {}
  },
  emits: ["save", "close", "switch"],
  setup(__props, { emit: __emit }) {
    const props = __props;
    const emit = __emit;
    const api = client(props);
    const config = ref({
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
      history_limit: 1e3,
      run_limit: 100,
      cookie_path: "/config/115-cookies.txt",
      cookie_text: "",
      exclude_keywords: "sample,trailer,花絮,预告",
      category_mapping: JSON.stringify({ movie: {}, tv: {} }, null, 2),
      target_cids: JSON.stringify(
        {
          movie: { 动画电影: "", 外语电影: "", 华语电影: "" },
          tv: { 未分类: "", 综艺: "", 日韩剧: "", 欧美剧: "", 国产剧: "" },
          unrecognized: ""
        },
        null,
        2
      ),
      ...props.initialConfig
    });
    config.value.cookie_mode ||= config.value.cookie_text ? "text" : "file";
    const sources = ref([]), errors = ref([]), validating = ref(false), checked = ref(false);
    const browser = ref(null);
    const tab = ref("connection");
    const revealCookie = ref(false);
    const rawSources = ref(String(config.value.source_mappings || "[]"));
    const hostConfirm = inject(
      "moviepilot:confirm",
      null
    );
    const deleteIndex = ref(null);
    const autoExecutePending = ref(false);
    const connectionOptions = [
      { title: "粘贴 Cookie", value: "text" },
      { title: "使用 Cookie 文件", value: "file" }
    ];
    const mediaOptions = [
      { title: "电影", value: "movie" },
      { title: "电视剧", value: "tv" }
    ];
    const conflictOptions = [
      { title: "跳过，不覆盖", value: "skip" },
      { title: "自动添加后缀", value: "rename_with_suffix" }
    ];
    const unrecognizedOptions = [
      { title: "跳过并显示原因", value: "skip" },
      { title: "移动到未识别目录 CID", value: "move_to_unrecognized" }
    ];
    const scheduleOptions = [
      { title: "不自动运行", value: "" },
      { title: "每天凌晨 3 点", value: "0 3 * * *" },
      { title: "每 6 小时", value: "0 */6 * * *" },
      { title: "每周日凌晨 3 点", value: "0 3 * * 0" }
    ];
    const batchFields = [
      { key: "batch_size", label: "批大小", min: 1, max: 100, step: 1 },
      {
        key: "sleep_between_batches",
        label: "批间隔（秒）",
        min: 0,
        max: 120,
        step: 0.1
      },
      {
        key: "plan_ttl_hours",
        label: "计划有效期（小时）",
        min: 1,
        max: 720,
        step: 1
      }
    ];
    const rateFields = [
      {
        key: "min_request_interval_ms",
        label: "请求间隔（毫秒）",
        min: 0,
        max: 6e4,
        step: 1
      },
      { key: "max_retries", label: "重试次数", min: 0, max: 10, step: 1 },
      {
        key: "retry_base_seconds",
        label: "退避基数（秒）",
        min: 0.1,
        max: 120,
        step: 0.1
      },
      { key: "jitter_ratio", label: "抖动比例", min: 0, max: 1, step: 0.1 },
      { key: "list_page_size", label: "目录分页大小", min: 50, max: 1e3, step: 1 },
      { key: "history_limit", label: "历史保留条数", min: 1, step: 1 }
    ];
    async function removeSource(index) {
      if (hostConfirm) {
        if (await hostConfirm({
          type: "warn",
          title: "移除来源",
          content: "仅删除此来源配置，不会删除网盘文件。",
          confirmText: "移除",
          cancelText: "取消"
        }))
          sources.value.splice(index, 1);
      } else deleteIndex.value = index;
    }
    async function setRunMode(previewOnly) {
      if (previewOnly) {
        config.value.dry_run = true;
        return;
      }
      if (config.value.dry_run === false) return;
      if (hostConfirm) {
        if (await hostConfirm({
          type: "warn",
          title: "开启自动执行",
          content: "定时或立即运行任务将自动移动和重命名文件，不会逐次弹出确认。请先用少量测试文件验证目录与规则。",
          confirmText: "开启自动执行",
          cancelText: "保持仅预览"
        }))
          config.value.dry_run = false;
      } else autoExecutePending.value = true;
    }
    const mode = ref("visual"), browsersLoading = ref(false);
    try {
      const rows = typeof config.value.source_mappings === "string" ? JSON.parse(config.value.source_mappings || "[]") : config.value.source_mappings || [];
      if (!Array.isArray(rows)) throw new Error();
      sources.value = rows.map(
        (row) => row && typeof row === "object" && !Array.isArray(row) ? row : {}
      );
    } catch {
      mode.value = "json";
      errors.value = ["旧来源映射 JSON 无效，请修正后再切换到可视化编辑"];
    }
    const canSave = computed(
      () => !validating.value && !browser.value && !autoExecutePending.value && deleteIndex.value === null
    );
    function payload() {
      return {
        ...config.value,
        source_mappings: mode.value === "json" ? rawSources.value : JSON.stringify(sources.value)
      };
    }
    function add() {
      sources.value.push({
        name: `来源 ${sources.value.length + 1}`,
        media_type: "movie",
        source_path: "",
        target_root_path: ""
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
        sources.value = rows.map(
          (row) => row && typeof row === "object" && !Array.isArray(row) ? row : {}
        );
        mode.value = "visual";
        errors.value = [];
      } catch {
        errors.value = ["来源映射必须是有效的 JSON 数组"];
      }
    }
    async function validate(save = false) {
      if (!canSave.value) return;
      validating.value = true;
      checked.value = false;
      errors.value = [];
      try {
        const data = await api.post("validate_config", { config: payload() });
        errors.value = data.errors || [];
        checked.value = data.valid;
        if (save && data.valid) emit("save", payload());
        if (!data.valid) tab.value = "connection";
      } catch (e) {
        errors.value = e.details?.errors || [e.message || "配置检查失败"];
        tab.value = "connection";
      } finally {
        validating.value = false;
      }
    }
    async function openBrowser(index, field) {
      browser.value = {
        index,
        field,
        path: sources.value[index][field] || "/",
        items: [],
        message: ""
      };
      await browse(browser.value.path);
    }
    async function browse(path) {
      if (!browser.value) return;
      const selection = browser.value;
      browsersLoading.value = true;
      browser.value.message = "";
      try {
        const data = await api.post("list_dir", { path });
        if (browser.value === selection) {
          browser.value.path = path;
          browser.value.items = data.items.filter((r) => r.is_dir);
        }
      } catch (e) {
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
    function child(name) {
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
    return (_ctx, _cache) => {
      const _component_VIcon = _resolveComponent("VIcon");
      const _component_VAvatar = _resolveComponent("VAvatar");
      const _component_VBtn = _resolveComponent("VBtn");
      const _component_VTab = _resolveComponent("VTab");
      const _component_VTabs = _resolveComponent("VTabs");
      const _component_VDivider = _resolveComponent("VDivider");
      const _component_VAlert = _resolveComponent("VAlert");
      const _component_VSelect = _resolveComponent("VSelect");
      const _component_VCol = _resolveComponent("VCol");
      const _component_VTextField = _resolveComponent("VTextField");
      const _component_VRow = _resolveComponent("VRow");
      const _component_VTextarea = _resolveComponent("VTextarea");
      const _component_VTooltip = _resolveComponent("VTooltip");
      const _component_VCardText = _resolveComponent("VCardText");
      const _component_VCard = _resolveComponent("VCard");
      const _component_VSheet = _resolveComponent("VSheet");
      const _component_VCardTitle = _resolveComponent("VCardTitle");
      const _component_VProgressLinear = _resolveComponent("VProgressLinear");
      const _component_VListItem = _resolveComponent("VListItem");
      const _component_VList = _resolveComponent("VList");
      const _component_VSpacer = _resolveComponent("VSpacer");
      const _component_VCardActions = _resolveComponent("VCardActions");
      const _component_VWindowItem = _resolveComponent("VWindowItem");
      const _component_VSwitch = _resolveComponent("VSwitch");
      const _component_VExpansionPanelText = _resolveComponent("VExpansionPanelText");
      const _component_VExpansionPanel = _resolveComponent("VExpansionPanel");
      const _component_VCombobox = _resolveComponent("VCombobox");
      const _component_VExpansionPanels = _resolveComponent("VExpansionPanels");
      const _component_VWindow = _resolveComponent("VWindow");
      const _component_VForm = _resolveComponent("VForm");
      return _openBlock(), _createBlock(_component_VForm, {
        class: "p115-config",
        onSubmit: _cache[33] || (_cache[33] = _withModifiers(($event) => validate(true), ["prevent"]))
      }, {
        default: _withCtx(() => [
          _createElementVNode("div", _hoisted_1, [
            _createVNode(_component_VAvatar, {
              color: "primary",
              variant: "tonal",
              rounded: "lg",
              size: "42"
            }, {
              default: _withCtx(() => [
                _createVNode(_component_VIcon, {
                  icon: _unref(icons).mdiTuneVariant
                }, null, 8, ["icon"])
              ]),
              _: 1
            }),
            _cache[34] || (_cache[34] = _createElementVNode("div", { class: "flex-grow-1 min-width-0" }, [
              _createElementVNode("h2", { class: "text-h6" }, "配置云端整理"),
              _createElementVNode("div", { class: "text-caption text-medium-emphasis" }, " 先连接 115，再设置来源和运行方式 ")
            ], -1)),
            _createVNode(_component_VBtn, {
              icon: _unref(icons).mdiClose,
              variant: "text",
              color: "secondary",
              size: "small",
              "aria-label": "关闭配置",
              onClick: _cache[0] || (_cache[0] = ($event) => emit("close"))
            }, null, 8, ["icon"])
          ]),
          _createVNode(_component_VTabs, {
            modelValue: tab.value,
            "onUpdate:modelValue": _cache[1] || (_cache[1] = ($event) => tab.value = $event),
            class: "px-4 px-sm-6",
            "show-arrows": ""
          }, {
            default: _withCtx(() => [
              _createVNode(_component_VTab, {
                value: "connection",
                "prepend-icon": _unref(icons).mdiFolderCogOutline
              }, {
                default: _withCtx(() => [..._cache[35] || (_cache[35] = [
                  _createTextVNode("连接与目录", -1)
                ])]),
                _: 1
              }, 8, ["prepend-icon"]),
              _createVNode(_component_VTab, {
                value: "automation",
                "prepend-icon": _unref(icons).mdiCalendarClock
              }, {
                default: _withCtx(() => [..._cache[36] || (_cache[36] = [
                  _createTextVNode("自动化", -1)
                ])]),
                _: 1
              }, 8, ["prepend-icon"]),
              _createVNode(_component_VTab, {
                value: "advanced",
                "prepend-icon": _unref(icons).mdiTune
              }, {
                default: _withCtx(() => [..._cache[37] || (_cache[37] = [
                  _createTextVNode("高级", -1)
                ])]),
                _: 1
              }, 8, ["prepend-icon"])
            ]),
            _: 1
          }, 8, ["modelValue"]),
          _createVNode(_component_VDivider),
          _createElementVNode("div", _hoisted_2, [
            errors.value.length ? (_openBlock(), _createBlock(_component_VAlert, {
              key: 0,
              type: "error",
              variant: "tonal",
              density: "compact",
              role: "alert",
              class: "mb-4"
            }, {
              default: _withCtx(() => [
                _createElementVNode("ul", _hoisted_3, [
                  (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(errors.value, (e) => {
                    return _openBlock(), _createElementBlock("li", { key: e }, _toDisplayString(e), 1);
                  }), 128))
                ])
              ]),
              _: 1
            })) : _createCommentVNode("", true),
            checked.value ? (_openBlock(), _createBlock(_component_VAlert, {
              key: 1,
              type: "success",
              variant: "tonal",
              density: "compact",
              class: "mb-4"
            }, {
              default: _withCtx(() => [..._cache[38] || (_cache[38] = [
                _createTextVNode("配置格式检查通过。保存后可在详情页检查实际连接与目录。", -1)
              ])]),
              _: 1
            })) : _createCommentVNode("", true),
            _createVNode(_component_VWindow, {
              modelValue: tab.value,
              "onUpdate:modelValue": _cache[30] || (_cache[30] = ($event) => tab.value = $event)
            }, {
              default: _withCtx(() => [
                _createVNode(_component_VWindowItem, { value: "connection" }, {
                  default: _withCtx(() => [
                    _cache[50] || (_cache[50] = _createElementVNode("div", { class: "text-subtitle-1 font-weight-medium mb-3" }, "115 连接", -1)),
                    _createVNode(_component_VRow, null, {
                      default: _withCtx(() => [
                        _createVNode(_component_VCol, {
                          cols: "12",
                          sm: "5"
                        }, {
                          default: _withCtx(() => [
                            _createVNode(_component_VSelect, {
                              modelValue: config.value.cookie_mode,
                              "onUpdate:modelValue": _cache[2] || (_cache[2] = ($event) => config.value.cookie_mode = $event),
                              items: connectionOptions,
                              label: "连接方式",
                              density: "comfortable",
                              "hide-details": ""
                            }, null, 8, ["modelValue"])
                          ]),
                          _: 1
                        }),
                        _createVNode(_component_VCol, {
                          cols: "12",
                          sm: "7"
                        }, {
                          default: _withCtx(() => [
                            config.value.cookie_mode === "text" ? (_openBlock(), _createBlock(_component_VTextField, {
                              key: 0,
                              modelValue: config.value.cookie_text,
                              "onUpdate:modelValue": _cache[3] || (_cache[3] = ($event) => config.value.cookie_text = $event),
                              type: revealCookie.value ? "text" : "password",
                              label: "Cookie 文本",
                              autocomplete: "off",
                              "append-inner-icon": revealCookie.value ? _unref(icons).mdiEyeOffOutline : _unref(icons).mdiEyeOutline,
                              "onClick:appendInner": _cache[4] || (_cache[4] = ($event) => revealCookie.value = !revealCookie.value),
                              "hide-details": ""
                            }, null, 8, ["modelValue", "type", "append-inner-icon"])) : (_openBlock(), _createBlock(_component_VTextField, {
                              key: 1,
                              modelValue: config.value.cookie_path,
                              "onUpdate:modelValue": _cache[5] || (_cache[5] = ($event) => config.value.cookie_path = $event),
                              label: "容器内 Cookie 文件路径",
                              placeholder: "/config/115-cookies.txt",
                              "prepend-inner-icon": _unref(icons).mdiFileKeyOutline,
                              "hide-details": ""
                            }, null, 8, ["modelValue", "prepend-inner-icon"]))
                          ]),
                          _: 1
                        })
                      ]),
                      _: 1
                    }),
                    _cache[51] || (_cache[51] = _createElementVNode("p", { class: "text-caption text-medium-emphasis mt-3 mb-6" }, " 只使用当前选择的方式。Cookie 不会出现在进度或诊断记录中。 ", -1)),
                    _createElementVNode("div", _hoisted_4, [
                      _cache[40] || (_cache[40] = _createElementVNode("div", { class: "text-subtitle-1 font-weight-medium flex-grow-1" }, " 来源与目标 ", -1)),
                      _createVNode(_component_VBtn, {
                        variant: "text",
                        color: "secondary",
                        size: "small",
                        "prepend-icon": _unref(icons).mdiCodeJson,
                        onClick: switchMode
                      }, {
                        default: _withCtx(() => [
                          _createTextVNode(_toDisplayString(mode.value === "visual" ? "JSON 编辑" : "可视化编辑"), 1)
                        ]),
                        _: 1
                      }, 8, ["prepend-icon"]),
                      mode.value === "visual" ? (_openBlock(), _createBlock(_component_VBtn, {
                        key: 0,
                        variant: "tonal",
                        size: "small",
                        "prepend-icon": _unref(icons).mdiPlus,
                        onClick: add
                      }, {
                        default: _withCtx(() => [..._cache[39] || (_cache[39] = [
                          _createTextVNode("添加来源", -1)
                        ])]),
                        _: 1
                      }, 8, ["prepend-icon"])) : _createCommentVNode("", true)
                    ]),
                    mode.value === "json" ? (_openBlock(), _createBlock(_component_VTextarea, {
                      key: 0,
                      modelValue: rawSources.value,
                      "onUpdate:modelValue": _cache[6] || (_cache[6] = ($event) => rawSources.value = $event),
                      label: "来源映射 JSON",
                      rows: "10",
                      "auto-grow": "",
                      class: "p115-json"
                    }, null, 8, ["modelValue"])) : (_openBlock(), _createElementBlock(_Fragment, { key: 1 }, [
                      (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(sources.value, (s, i) => {
                        return _openBlock(), _createBlock(_component_VCard, {
                          key: i,
                          variant: "tonal",
                          class: "mb-4 p115-source"
                        }, {
                          default: _withCtx(() => [
                            _createElementVNode("div", _hoisted_5, [
                              _createVNode(_component_VIcon, {
                                icon: s.media_type === "tv" ? _unref(icons).mdiTelevisionClassic : _unref(icons).mdiMovieOutline,
                                color: "primary",
                                size: "20"
                              }, null, 8, ["icon"]),
                              _createElementVNode("span", _hoisted_6, _toDisplayString(s.name || `来源 ${i + 1}`), 1),
                              _createVNode(_component_VTooltip, { text: "移除来源配置，不删除文件" }, {
                                activator: _withCtx(({ props: tip }) => [
                                  _createVNode(_component_VBtn, _mergeProps({ ref_for: true }, tip, {
                                    icon: _unref(icons).mdiTrashCanOutline,
                                    variant: "text",
                                    color: "secondary",
                                    size: "small",
                                    "aria-label": `移除来源 ${i + 1}`,
                                    onClick: ($event) => removeSource(i)
                                  }), null, 16, ["icon", "aria-label", "onClick"])
                                ]),
                                _: 2
                              }, 1024)
                            ]),
                            _createVNode(_component_VCardText, { class: "pt-2" }, {
                              default: _withCtx(() => [
                                _createVNode(_component_VRow, { dense: "" }, {
                                  default: _withCtx(() => [
                                    _createVNode(_component_VCol, {
                                      cols: "12",
                                      sm: "7"
                                    }, {
                                      default: _withCtx(() => [
                                        _createVNode(_component_VTextField, {
                                          modelValue: s.name,
                                          "onUpdate:modelValue": ($event) => s.name = $event,
                                          label: "名称",
                                          density: "compact",
                                          "hide-details": ""
                                        }, null, 8, ["modelValue", "onUpdate:modelValue"])
                                      ]),
                                      _: 2
                                    }, 1024),
                                    _createVNode(_component_VCol, {
                                      cols: "12",
                                      sm: "5"
                                    }, {
                                      default: _withCtx(() => [
                                        _createVNode(_component_VSelect, {
                                          modelValue: s.media_type,
                                          "onUpdate:modelValue": ($event) => s.media_type = $event,
                                          items: mediaOptions,
                                          label: "媒体类型",
                                          density: "compact",
                                          "hide-details": ""
                                        }, null, 8, ["modelValue", "onUpdate:modelValue"])
                                      ]),
                                      _: 2
                                    }, 1024),
                                    _createVNode(_component_VCol, { cols: "12" }, {
                                      default: _withCtx(() => [
                                        _createVNode(_component_VTextField, {
                                          modelValue: s.source_path,
                                          "onUpdate:modelValue": ($event) => s.source_path = $event,
                                          label: "115 待整理来源",
                                          placeholder: "/待整理/Movie",
                                          "append-inner-icon": _unref(icons).mdiFolderOpenOutline,
                                          density: "compact",
                                          "hide-details": "",
                                          "onClick:appendInner": ($event) => openBrowser(i, "source_path")
                                        }, null, 8, ["modelValue", "onUpdate:modelValue", "append-inner-icon", "onClick:appendInner"])
                                      ]),
                                      _: 2
                                    }, 1024),
                                    _createVNode(_component_VCol, { cols: "12" }, {
                                      default: _withCtx(() => [
                                        _createVNode(_component_VTextField, {
                                          modelValue: s.target_root_path,
                                          "onUpdate:modelValue": ($event) => s.target_root_path = $event,
                                          label: "目标媒体库根目录",
                                          placeholder: "/媒体库/Movie",
                                          "append-inner-icon": _unref(icons).mdiFolderOpenOutline,
                                          density: "compact",
                                          "hide-details": "",
                                          "onClick:appendInner": ($event) => openBrowser(i, "target_root_path")
                                        }, null, 8, ["modelValue", "onUpdate:modelValue", "append-inner-icon", "onClick:appendInner"])
                                      ]),
                                      _: 2
                                    }, 1024)
                                  ]),
                                  _: 2
                                }, 1024),
                                _cache[41] || (_cache[41] = _createElementVNode("div", { class: "text-caption text-medium-emphasis mt-3" }, " 目标不能位于任何来源目录内；分类目录需与 MP 分类匹配。 ", -1))
                              ]),
                              _: 2
                            }, 1024)
                          ]),
                          _: 2
                        }, 1024);
                      }), 128)),
                      !sources.value.length ? (_openBlock(), _createBlock(_component_VSheet, {
                        key: 0,
                        rounded: "lg",
                        class: "text-center pa-6"
                      }, {
                        default: _withCtx(() => [
                          _createVNode(_component_VIcon, {
                            icon: _unref(icons).mdiFolderPlusOutline,
                            color: "secondary",
                            size: "28"
                          }, null, 8, ["icon"]),
                          _cache[43] || (_cache[43] = _createElementVNode("p", { class: "text-body-2 mt-2 mb-3" }, "添加一个待整理来源开始配置", -1)),
                          _createVNode(_component_VBtn, {
                            variant: "tonal",
                            "prepend-icon": _unref(icons).mdiPlus,
                            onClick: add
                          }, {
                            default: _withCtx(() => [..._cache[42] || (_cache[42] = [
                              _createTextVNode("添加来源", -1)
                            ])]),
                            _: 1
                          }, 8, ["prepend-icon"])
                        ]),
                        _: 1
                      })) : _createCommentVNode("", true)
                    ], 64)),
                    deleteIndex.value !== null ? (_openBlock(), _createBlock(_component_VAlert, {
                      key: 2,
                      type: "warning",
                      variant: "tonal",
                      class: "mb-4"
                    }, {
                      default: _withCtx(() => [
                        _cache[46] || (_cache[46] = _createElementVNode("p", { class: "text-body-2" }, "移除此来源配置？不会删除网盘文件。", -1)),
                        _createElementVNode("div", _hoisted_7, [
                          _createVNode(_component_VBtn, {
                            variant: "text",
                            color: "secondary",
                            onClick: _cache[7] || (_cache[7] = ($event) => deleteIndex.value = null)
                          }, {
                            default: _withCtx(() => [..._cache[44] || (_cache[44] = [
                              _createTextVNode("取消", -1)
                            ])]),
                            _: 1
                          }),
                          _createVNode(_component_VBtn, {
                            variant: "tonal",
                            color: "warning",
                            onClick: _cache[8] || (_cache[8] = ($event) => {
                              sources.value.splice(deleteIndex.value, 1);
                              deleteIndex.value = null;
                            })
                          }, {
                            default: _withCtx(() => [..._cache[45] || (_cache[45] = [
                              _createTextVNode("确认移除", -1)
                            ])]),
                            _: 1
                          })
                        ])
                      ]),
                      _: 1
                    })) : _createCommentVNode("", true),
                    browser.value ? (_openBlock(), _createBlock(_component_VCard, {
                      key: 3,
                      variant: "outlined",
                      class: "p115-directory mb-4",
                      role: "region",
                      "aria-label": "115 目录选择"
                    }, {
                      default: _withCtx(() => [
                        _createVNode(_component_VCardTitle, { class: "d-flex align-center ga-2 text-subtitle-1" }, {
                          default: _withCtx(() => [
                            _createVNode(_component_VIcon, {
                              icon: _unref(icons).mdiFolderOpenOutline,
                              color: "primary",
                              size: "20"
                            }, null, 8, ["icon"]),
                            _createElementVNode("span", _hoisted_8, _toDisplayString(browser.value.path), 1),
                            _createVNode(_component_VBtn, {
                              icon: _unref(icons).mdiClose,
                              size: "small",
                              color: "secondary",
                              variant: "text",
                              "aria-label": "取消目录选择",
                              onClick: _cache[9] || (_cache[9] = ($event) => browser.value = null)
                            }, null, 8, ["icon"])
                          ]),
                          _: 1
                        }),
                        _createVNode(_component_VCardText, null, {
                          default: _withCtx(() => [
                            _cache[47] || (_cache[47] = _createElementVNode("div", { class: "text-caption text-medium-emphasis mb-3" }, " 使用已经保存的连接。首次配置可先填写路径并保存，再浏览目录。 ", -1)),
                            browser.value.message ? (_openBlock(), _createBlock(_component_VAlert, {
                              key: 0,
                              type: "warning",
                              variant: "tonal",
                              density: "compact",
                              role: "alert",
                              class: "mb-3"
                            }, {
                              default: _withCtx(() => [
                                _createTextVNode(_toDisplayString(browser.value.message), 1)
                              ]),
                              _: 1
                            })) : _createCommentVNode("", true),
                            browsersLoading.value ? (_openBlock(), _createBlock(_component_VProgressLinear, {
                              key: 1,
                              indeterminate: "",
                              color: "primary",
                              class: "mb-2"
                            })) : _createCommentVNode("", true),
                            _createVNode(_component_VList, {
                              class: "p115-directory-list",
                              density: "compact",
                              "bg-color": "transparent"
                            }, {
                              default: _withCtx(() => [
                                (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(browser.value.items, (d) => {
                                  return _openBlock(), _createBlock(_component_VListItem, {
                                    key: d.cid,
                                    title: d.name,
                                    "prepend-icon": _unref(icons).mdiFolderOutline,
                                    "append-icon": _unref(icons).mdiChevronRight,
                                    disabled: browsersLoading.value,
                                    onClick: ($event) => browse(child(d.name))
                                  }, null, 8, ["title", "prepend-icon", "append-icon", "disabled", "onClick"]);
                                }), 128)),
                                !browser.value.items.length && !browsersLoading.value ? (_openBlock(), _createBlock(_component_VListItem, {
                                  key: 0,
                                  title: "暂无子目录"
                                })) : _createCommentVNode("", true)
                              ]),
                              _: 1
                            })
                          ]),
                          _: 1
                        }),
                        _createVNode(_component_VCardActions, null, {
                          default: _withCtx(() => [
                            _createVNode(_component_VBtn, {
                              variant: "text",
                              color: "secondary",
                              "prepend-icon": _unref(icons).mdiArrowUp,
                              disabled: browsersLoading.value || browser.value.path === "/",
                              onClick: _cache[10] || (_cache[10] = ($event) => browse(parent()))
                            }, {
                              default: _withCtx(() => [..._cache[48] || (_cache[48] = [
                                _createTextVNode("上一级", -1)
                              ])]),
                              _: 1
                            }, 8, ["prepend-icon", "disabled"]),
                            _createVNode(_component_VSpacer),
                            _createVNode(_component_VBtn, {
                              variant: "tonal",
                              disabled: browsersLoading.value || !!browser.value.message,
                              onClick: selectDirectory
                            }, {
                              default: _withCtx(() => [..._cache[49] || (_cache[49] = [
                                _createTextVNode("使用当前目录", -1)
                              ])]),
                              _: 1
                            }, 8, ["disabled"])
                          ]),
                          _: 1
                        })
                      ]),
                      _: 1
                    })) : _createCommentVNode("", true)
                  ]),
                  _: 1
                }),
                _createVNode(_component_VWindowItem, { value: "automation" }, {
                  default: _withCtx(() => [
                    _cache[56] || (_cache[56] = _createElementVNode("div", { class: "text-subtitle-1 font-weight-medium mb-3" }, "运行方式", -1)),
                    _createVNode(_component_VRow, { dense: "" }, {
                      default: _withCtx(() => [
                        _createVNode(_component_VCol, {
                          cols: "12",
                          sm: "6"
                        }, {
                          default: _withCtx(() => [
                            _createVNode(_component_VSwitch, {
                              modelValue: config.value.enabled,
                              "onUpdate:modelValue": _cache[11] || (_cache[11] = ($event) => config.value.enabled = $event),
                              label: "启用定时服务"
                            }, null, 8, ["modelValue"])
                          ]),
                          _: 1
                        }),
                        _createVNode(_component_VCol, {
                          cols: "12",
                          sm: "6"
                        }, {
                          default: _withCtx(() => [
                            _createVNode(_component_VSwitch, {
                              modelValue: config.value.notify,
                              "onUpdate:modelValue": _cache[12] || (_cache[12] = ($event) => config.value.notify = $event),
                              label: "发送结果通知"
                            }, null, 8, ["modelValue"])
                          ]),
                          _: 1
                        })
                      ]),
                      _: 1
                    }),
                    _createVNode(_component_VSelect, {
                      "model-value": config.value.dry_run,
                      items: [
                        { title: "仅生成预览（推荐）", value: true },
                        { title: "生成后自动执行", value: false }
                      ],
                      label: "定时与立即运行模式",
                      "onUpdate:modelValue": setRunMode,
                      "hide-details": ""
                    }, null, 8, ["model-value"]),
                    _cache[57] || (_cache[57] = _createElementVNode("div", { class: "text-caption text-medium-emphasis mt-2 mb-4" }, " 手动执行始终需要确认摘要，无需关闭“仅生成预览”。 ", -1)),
                    config.value.dry_run === false ? (_openBlock(), _createBlock(_component_VAlert, {
                      key: 0,
                      type: "warning",
                      variant: "tonal",
                      density: "compact",
                      class: "mb-4"
                    }, {
                      default: _withCtx(() => [..._cache[52] || (_cache[52] = [
                        _createTextVNode("自动运行会直接移动和重命名文件，不会逐次弹出确认。请先验证目录与规则。", -1)
                      ])]),
                      _: 1
                    })) : _createCommentVNode("", true),
                    autoExecutePending.value ? (_openBlock(), _createBlock(_component_VAlert, {
                      key: 1,
                      type: "warning",
                      variant: "tonal",
                      class: "mb-4"
                    }, {
                      default: _withCtx(() => [
                        _cache[55] || (_cache[55] = _createElementVNode("p", { class: "text-body-2" }, " 开启自动执行后，定时或立即运行任务将直接移动和重命名文件。是否继续？ ", -1)),
                        _createElementVNode("div", _hoisted_9, [
                          _createVNode(_component_VBtn, {
                            variant: "text",
                            color: "secondary",
                            onClick: _cache[13] || (_cache[13] = ($event) => autoExecutePending.value = false)
                          }, {
                            default: _withCtx(() => [..._cache[53] || (_cache[53] = [
                              _createTextVNode("保持仅预览", -1)
                            ])]),
                            _: 1
                          }),
                          _createVNode(_component_VBtn, {
                            variant: "tonal",
                            color: "warning",
                            onClick: _cache[14] || (_cache[14] = ($event) => {
                              config.value.dry_run = false;
                              autoExecutePending.value = false;
                            })
                          }, {
                            default: _withCtx(() => [..._cache[54] || (_cache[54] = [
                              _createTextVNode("开启自动执行", -1)
                            ])]),
                            _: 1
                          })
                        ])
                      ]),
                      _: 1
                    })) : _createCommentVNode("", true),
                    _createVNode(_component_VRow, null, {
                      default: _withCtx(() => [
                        _createVNode(_component_VCol, {
                          cols: "12",
                          sm: "6"
                        }, {
                          default: _withCtx(() => [
                            _createVNode(_component_VSelect, {
                              items: scheduleOptions,
                              label: "常用运行时间",
                              placeholder: "选择后填入 CRON",
                              "onUpdate:modelValue": _cache[15] || (_cache[15] = ($event) => config.value.cron = $event),
                              "hide-details": ""
                            })
                          ]),
                          _: 1
                        }),
                        _createVNode(_component_VCol, {
                          cols: "12",
                          sm: "6"
                        }, {
                          default: _withCtx(() => [
                            _createVNode(_component_VTextField, {
                              modelValue: config.value.cron,
                              "onUpdate:modelValue": _cache[16] || (_cache[16] = ($event) => config.value.cron = $event),
                              label: "五段 CRON",
                              placeholder: "0 3 * * *",
                              hint: "留空不自动运行",
                              "persistent-hint": ""
                            }, null, 8, ["modelValue"])
                          ]),
                          _: 1
                        })
                      ]),
                      _: 1
                    }),
                    _createVNode(_component_VSwitch, {
                      modelValue: config.value.onlyonce,
                      "onUpdate:modelValue": _cache[17] || (_cache[17] = ($event) => config.value.onlyonce = $event),
                      label: "保存后立即运行一次",
                      hint: "遵循上面的运行模式；仅预览模式不会自动执行",
                      "persistent-hint": "",
                      class: "mb-4"
                    }, null, 8, ["modelValue"]),
                    _createVNode(_component_VDivider, { class: "my-5" }),
                    _cache[58] || (_cache[58] = _createElementVNode("div", { class: "text-subtitle-1 font-weight-medium mb-3" }, "整理策略", -1)),
                    _createVNode(_component_VRow, { dense: "" }, {
                      default: _withCtx(() => [
                        _createVNode(_component_VCol, {
                          cols: "12",
                          sm: "6"
                        }, {
                          default: _withCtx(() => [
                            _createVNode(_component_VSwitch, {
                              modelValue: config.value.delete_empty_source_dirs,
                              "onUpdate:modelValue": _cache[18] || (_cache[18] = ($event) => config.value.delete_empty_source_dirs = $event),
                              label: "整理后清理空来源目录"
                            }, null, 8, ["modelValue"])
                          ]),
                          _: 1
                        }),
                        _createVNode(_component_VCol, {
                          cols: "12",
                          sm: "6"
                        }, {
                          default: _withCtx(() => [
                            _createVNode(_component_VSwitch, {
                              modelValue: config.value.refresh_plex_after_execute,
                              "onUpdate:modelValue": _cache[19] || (_cache[19] = ($event) => config.value.refresh_plex_after_execute = $event),
                              label: "整理后刷新 Plex"
                            }, null, 8, ["modelValue"])
                          ]),
                          _: 1
                        }),
                        _createVNode(_component_VCol, {
                          cols: "12",
                          sm: "6"
                        }, {
                          default: _withCtx(() => [
                            _createVNode(_component_VSelect, {
                              modelValue: config.value.conflict_strategy,
                              "onUpdate:modelValue": _cache[20] || (_cache[20] = ($event) => config.value.conflict_strategy = $event),
                              items: conflictOptions,
                              label: "重名策略",
                              "hide-details": ""
                            }, null, 8, ["modelValue"])
                          ]),
                          _: 1
                        }),
                        _createVNode(_component_VCol, {
                          cols: "12",
                          sm: "6"
                        }, {
                          default: _withCtx(() => [
                            _createVNode(_component_VSelect, {
                              modelValue: config.value.unrecognized_action,
                              "onUpdate:modelValue": _cache[21] || (_cache[21] = ($event) => config.value.unrecognized_action = $event),
                              items: unrecognizedOptions,
                              label: "无法识别的文件",
                              "hide-details": ""
                            }, null, 8, ["modelValue"])
                          ]),
                          _: 1
                        }),
                        _createVNode(_component_VCol, {
                          cols: "12",
                          sm: "4"
                        }, {
                          default: _withCtx(() => [
                            _createVNode(_component_VTextField, {
                              modelValue: config.value.max_items_per_run,
                              "onUpdate:modelValue": _cache[22] || (_cache[22] = ($event) => config.value.max_items_per_run = $event),
                              modelModifiers: { number: true },
                              type: "number",
                              label: "单次最多文件",
                              min: 0,
                              max: 1e4,
                              hint: "0 表示不限",
                              "persistent-hint": ""
                            }, null, 8, ["modelValue"])
                          ]),
                          _: 1
                        }),
                        _createVNode(_component_VCol, {
                          cols: "12",
                          sm: "4"
                        }, {
                          default: _withCtx(() => [
                            _createVNode(_component_VTextField, {
                              modelValue: config.value.min_file_size_mb,
                              "onUpdate:modelValue": _cache[23] || (_cache[23] = ($event) => config.value.min_file_size_mb = $event),
                              modelModifiers: { number: true },
                              type: "number",
                              label: "最小文件体积（MB）",
                              min: 0,
                              "hide-details": ""
                            }, null, 8, ["modelValue"])
                          ]),
                          _: 1
                        }),
                        _createVNode(_component_VCol, {
                          cols: "12",
                          sm: "4"
                        }, {
                          default: _withCtx(() => [
                            _createVNode(_component_VTextField, {
                              modelValue: config.value.max_depth,
                              "onUpdate:modelValue": _cache[24] || (_cache[24] = ($event) => config.value.max_depth = $event),
                              modelModifiers: { number: true },
                              type: "number",
                              label: "扫描深度",
                              min: 0,
                              max: 30,
                              "hide-details": ""
                            }, null, 8, ["modelValue"])
                          ]),
                          _: 1
                        })
                      ]),
                      _: 1
                    })
                  ]),
                  _: 1
                }),
                _createVNode(_component_VWindowItem, { value: "advanced" }, {
                  default: _withCtx(() => [
                    _createVNode(_component_VAlert, {
                      type: "info",
                      variant: "tonal",
                      density: "compact",
                      class: "mb-4"
                    }, {
                      default: _withCtx(() => [..._cache[59] || (_cache[59] = [
                        _createTextVNode("通常无需修改。CID 覆盖和分类别名只在高级场景使用。", -1)
                      ])]),
                      _: 1
                    }),
                    _createVNode(_component_VExpansionPanels, {
                      variant: "accordion",
                      multiple: ""
                    }, {
                      default: _withCtx(() => [
                        _createVNode(_component_VExpansionPanel, { title: "目录与分类覆盖" }, {
                          default: _withCtx(() => [
                            _createVNode(_component_VExpansionPanelText, null, {
                              default: _withCtx(() => [
                                _createVNode(_component_VTextarea, {
                                  modelValue: config.value.target_cids,
                                  "onUpdate:modelValue": _cache[25] || (_cache[25] = ($event) => config.value.target_cids = $event),
                                  label: "目标 CID 覆盖 JSON",
                                  rows: "5",
                                  class: "p115-json mb-3"
                                }, null, 8, ["modelValue"]),
                                _createVNode(_component_VTextarea, {
                                  modelValue: config.value.category_mapping,
                                  "onUpdate:modelValue": _cache[26] || (_cache[26] = ($event) => config.value.category_mapping = $event),
                                  label: "分类别名 JSON",
                                  rows: "4",
                                  class: "p115-json"
                                }, null, 8, ["modelValue"]),
                                _createVNode(_component_VTextField, {
                                  modelValue: config.value.exclude_keywords,
                                  "onUpdate:modelValue": _cache[27] || (_cache[27] = ($event) => config.value.exclude_keywords = $event),
                                  label: "排除关键词",
                                  hint: "逗号分隔",
                                  "persistent-hint": "",
                                  class: "mt-3"
                                }, null, 8, ["modelValue"])
                              ]),
                              _: 1
                            })
                          ]),
                          _: 1
                        }),
                        _createVNode(_component_VExpansionPanel, { title: "批次与有效期" }, {
                          default: _withCtx(() => [
                            _createVNode(_component_VExpansionPanelText, null, {
                              default: _withCtx(() => [
                                _createVNode(_component_VRow, { dense: "" }, {
                                  default: _withCtx(() => [
                                    (_openBlock(), _createElementBlock(_Fragment, null, _renderList(batchFields, (field) => {
                                      return _createVNode(_component_VCol, {
                                        key: field.key,
                                        cols: "12",
                                        sm: "4"
                                      }, {
                                        default: _withCtx(() => [
                                          _createVNode(_component_VTextField, {
                                            modelValue: config.value[field.key],
                                            "onUpdate:modelValue": ($event) => config.value[field.key] = $event,
                                            modelModifiers: { number: true },
                                            label: field.label,
                                            type: "number",
                                            min: field.min,
                                            max: field.max,
                                            step: field.step,
                                            "hide-details": ""
                                          }, null, 8, ["modelValue", "onUpdate:modelValue", "label", "min", "max", "step"])
                                        ]),
                                        _: 2
                                      }, 1024);
                                    }), 64))
                                  ]),
                                  _: 1
                                })
                              ]),
                              _: 1
                            })
                          ]),
                          _: 1
                        }),
                        _createVNode(_component_VExpansionPanel, { title: "请求节奏与历史" }, {
                          default: _withCtx(() => [
                            _createVNode(_component_VExpansionPanelText, null, {
                              default: _withCtx(() => [
                                _createVNode(_component_VRow, { dense: "" }, {
                                  default: _withCtx(() => [
                                    (_openBlock(), _createElementBlock(_Fragment, null, _renderList(rateFields, (field) => {
                                      return _createVNode(_component_VCol, {
                                        key: field.key,
                                        cols: "12",
                                        sm: "4"
                                      }, {
                                        default: _withCtx(() => [
                                          _createVNode(_component_VTextField, {
                                            modelValue: config.value[field.key],
                                            "onUpdate:modelValue": ($event) => config.value[field.key] = $event,
                                            modelModifiers: { number: true },
                                            label: field.label,
                                            type: "number",
                                            min: field.min,
                                            max: field.max,
                                            step: field.step,
                                            "hide-details": ""
                                          }, null, 8, ["modelValue", "onUpdate:modelValue", "label", "min", "max", "step"])
                                        ]),
                                        _: 2
                                      }, 1024);
                                    }), 64))
                                  ]),
                                  _: 1
                                })
                              ]),
                              _: 1
                            })
                          ]),
                          _: 1
                        }),
                        _createVNode(_component_VExpansionPanel, { title: "外部执行与 Plex" }, {
                          default: _withCtx(() => [
                            _createVNode(_component_VExpansionPanelText, null, {
                              default: _withCtx(() => [
                                _createVNode(_component_VSwitch, {
                                  modelValue: config.value.allow_external_execute,
                                  "onUpdate:modelValue": _cache[28] || (_cache[28] = ($event) => config.value.allow_external_execute = $event),
                                  label: "允许 API Key 外部自动执行",
                                  hint: "默认关闭；不会替代手动确认",
                                  "persistent-hint": ""
                                }, null, 8, ["modelValue"]),
                                _createVNode(_component_VCombobox, {
                                  modelValue: config.value.plex_mediaservers,
                                  "onUpdate:modelValue": _cache[29] || (_cache[29] = ($event) => config.value.plex_mediaservers = $event),
                                  label: "Plex 服务器名称",
                                  multiple: "",
                                  chips: "",
                                  "closable-chips": "",
                                  hint: "留空刷新全部已配置 Plex 服务器",
                                  "persistent-hint": "",
                                  class: "mt-4"
                                }, null, 8, ["modelValue"])
                              ]),
                              _: 1
                            })
                          ]),
                          _: 1
                        })
                      ]),
                      _: 1
                    })
                  ]),
                  _: 1
                })
              ]),
              _: 1
            }, 8, ["modelValue"])
          ]),
          _createElementVNode("div", _hoisted_10, [
            _createVNode(_component_VDivider),
            _createVNode(_component_VCardActions, { class: "px-4 px-sm-6 py-3 ga-2" }, {
              default: _withCtx(() => [
                _createVNode(_component_VBtn, {
                  variant: "text",
                  color: "secondary",
                  "prepend-icon": _unref(icons).mdiArrowLeft,
                  onClick: _cache[31] || (_cache[31] = ($event) => emit("switch"))
                }, {
                  default: _withCtx(() => [..._cache[60] || (_cache[60] = [
                    _createTextVNode("查看详情", -1)
                  ])]),
                  _: 1
                }, 8, ["prepend-icon"]),
                _createVNode(_component_VSpacer),
                _createVNode(_component_VBtn, {
                  variant: "text",
                  color: "secondary",
                  onClick: _cache[32] || (_cache[32] = ($event) => emit("close"))
                }, {
                  default: _withCtx(() => [..._cache[61] || (_cache[61] = [
                    _createTextVNode("取消", -1)
                  ])]),
                  _: 1
                }),
                _createVNode(_component_VBtn, {
                  color: "primary",
                  variant: "flat",
                  "prepend-icon": _unref(icons).mdiContentSaveOutline,
                  loading: validating.value,
                  disabled: !canSave.value,
                  type: "submit"
                }, {
                  default: _withCtx(() => [..._cache[62] || (_cache[62] = [
                    _createTextVNode("检查并保存", -1)
                  ])]),
                  _: 1
                }, 8, ["prepend-icon", "loading", "disabled"])
              ]),
              _: 1
            })
          ])
        ]),
        _: 1
      });
    };
  }
});

const Config = /* @__PURE__ */ _export_sfc(_sfc_main, [["__scopeId", "data-v-4eed2c1a"]]);

export { Config as default };
