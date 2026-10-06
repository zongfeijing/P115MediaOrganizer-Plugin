import { importShared } from './__federation_fn_import-JrT3xvdd.js';
import { c as client, _ as _export_sfc } from './_plugin-vue_export-helper-Dt9Z4jcE.js';

const {defineComponent:_defineComponent} = await importShared('vue');

const {createElementVNode:_createElementVNode,renderList:_renderList,Fragment:_Fragment,openBlock:_openBlock,createElementBlock:_createElementBlock,toDisplayString:_toDisplayString,createCommentVNode:_createCommentVNode,vModelSelect:_vModelSelect,withDirectives:_withDirectives,createTextVNode:_createTextVNode,vModelText:_vModelText,vModelCheckbox:_vModelCheckbox} = await importShared('vue');

const _hoisted_1 = { class: "p115-config" };
const _hoisted_2 = {
  key: 0,
  class: "notice error",
  role: "alert"
};
const _hoisted_3 = {
  key: 1,
  class: "notice"
};
const _hoisted_4 = { key: 0 };
const _hoisted_5 = { key: 1 };
const _hoisted_6 = { class: "row" };
const _hoisted_7 = ["onUpdate:modelValue"];
const _hoisted_8 = ["onUpdate:modelValue"];
const _hoisted_9 = ["onClick"];
const _hoisted_10 = { class: "row" };
const _hoisted_11 = ["onUpdate:modelValue"];
const _hoisted_12 = ["onClick"];
const _hoisted_13 = { class: "row" };
const _hoisted_14 = ["onUpdate:modelValue"];
const _hoisted_15 = ["onClick"];
const _hoisted_16 = {
  key: 2,
  class: "directory-picker",
  role: "region",
  "aria-label": "115 目录选择"
};
const _hoisted_17 = {
  key: 0,
  role: "alert"
};
const _hoisted_18 = { class: "row" };
const _hoisted_19 = ["disabled"];
const _hoisted_20 = ["disabled"];
const _hoisted_21 = ["onClick", "disabled"];
const _hoisted_22 = { key: 1 };
const _hoisted_23 = { class: "row" };
const _hoisted_24 = { class: "check" };
const _hoisted_25 = { class: "check" };
const _hoisted_26 = { class: "check" };
const _hoisted_27 = { class: "row" };
const _hoisted_28 = { class: "check" };
const _hoisted_29 = { class: "check" };
const _hoisted_30 = { class: "row" };
const _hoisted_31 = { key: 2 };
const _hoisted_32 = { class: "check" };
const _hoisted_33 = { class: "row" };
const _hoisted_34 = { class: "row" };
const _hoisted_35 = { class: "row" };
const _hoisted_36 = { class: "row" };
const _hoisted_37 = ["disabled"];
const _hoisted_38 = ["disabled"];
const {computed,onMounted,ref} = await importShared('vue');
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
    const advanced = ref(false), rawSources = ref(String(config.value.source_mappings || "[]"));
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
    const canSave = computed(() => !validating.value && !browser.value);
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
      validating.value = true;
      checked.value = false;
      errors.value = [];
      try {
        const data = await api.post("validate_config", { config: payload() });
        errors.value = data.errors || [];
        checked.value = data.valid;
        if (save && data.valid) emit("save", payload());
      } catch (e) {
        errors.value = e.details?.errors || [e.message || "配置检查失败"];
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
      return _openBlock(), _createElementBlock("section", _hoisted_1, [
        _cache[84] || (_cache[84] = _createElementVNode("header", null, [
          _createElementVNode("h2", null, "配置 115 云端媒体整理"),
          _createElementVNode("p", null, " 先设置连接和来源，再生成预览。保存不会自动执行，除非明确勾选“立即运行一次”。 ")
        ], -1)),
        errors.value.length ? (_openBlock(), _createElementBlock("div", _hoisted_2, [
          _createElementVNode("ul", null, [
            (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(errors.value, (e) => {
              return _openBlock(), _createElementBlock("li", { key: e }, _toDisplayString(e), 1);
            }), 128))
          ])
        ])) : _createCommentVNode("", true),
        checked.value ? (_openBlock(), _createElementBlock("p", _hoisted_3, " 配置格式检查通过。连接与实际目录请保存后在详情页检查。 ")) : _createCommentVNode("", true),
        _createElementVNode("fieldset", null, [
          _cache[41] || (_cache[41] = _createElementVNode("legend", null, "1. 115 连接", -1)),
          _createElementVNode("label", null, [
            _cache[38] || (_cache[38] = _createTextVNode("连接方式", -1)),
            _withDirectives(_createElementVNode("select", {
              "onUpdate:modelValue": _cache[0] || (_cache[0] = ($event) => config.value.cookie_mode = $event)
            }, [..._cache[37] || (_cache[37] = [
              _createElementVNode("option", { value: "text" }, "粘贴 Cookie", -1),
              _createElementVNode("option", { value: "file" }, "使用 Cookie 文件", -1)
            ])], 512), [
              [_vModelSelect, config.value.cookie_mode]
            ])
          ]),
          config.value.cookie_mode === "text" ? (_openBlock(), _createElementBlock("label", _hoisted_4, [
            _cache[39] || (_cache[39] = _createTextVNode("Cookie 文本", -1)),
            _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": _cache[1] || (_cache[1] = ($event) => config.value.cookie_text = $event),
              type: "password",
              autocomplete: "off"
            }, null, 512), [
              [_vModelText, config.value.cookie_text]
            ])
          ])) : (_openBlock(), _createElementBlock("label", _hoisted_5, [
            _cache[40] || (_cache[40] = _createTextVNode("容器内 Cookie 文件路径", -1)),
            _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": _cache[2] || (_cache[2] = ($event) => config.value.cookie_path = $event),
              placeholder: "/config/115-cookies.txt"
            }, null, 512), [
              [_vModelText, config.value.cookie_path]
            ])
          ])),
          _cache[42] || (_cache[42] = _createElementVNode("p", null, " 只使用你选择的方式，另一种不会覆盖它。Cookie 不会出现在进度或诊断记录中。 ", -1))
        ]),
        _createElementVNode("fieldset", null, [
          _cache[50] || (_cache[50] = _createElementVNode("legend", null, "2. 来源与目标目录", -1)),
          _createElementVNode("button", { onClick: switchMode }, _toDisplayString(mode.value === "visual" ? "高级 JSON 编辑" : "切换可视化编辑"), 1),
          mode.value === "json" ? _withDirectives((_openBlock(), _createElementBlock("textarea", {
            key: 0,
            "onUpdate:modelValue": _cache[3] || (_cache[3] = ($event) => rawSources.value = $event),
            rows: "12",
            "aria-label": "来源映射 JSON"
          }, null, 512)), [
            [_vModelText, rawSources.value]
          ]) : (_openBlock(), _createElementBlock(_Fragment, { key: 1 }, [
            (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(sources.value, (s, i) => {
              return _openBlock(), _createElementBlock("article", {
                key: i,
                class: "source-card"
              }, [
                _createElementVNode("div", _hoisted_6, [
                  _createElementVNode("label", null, [
                    _cache[43] || (_cache[43] = _createTextVNode("名称", -1)),
                    _withDirectives(_createElementVNode("input", {
                      "onUpdate:modelValue": ($event) => s.name = $event
                    }, null, 8, _hoisted_7), [
                      [_vModelText, s.name]
                    ])
                  ]),
                  _createElementVNode("label", null, [
                    _cache[45] || (_cache[45] = _createTextVNode("媒体类型", -1)),
                    _withDirectives(_createElementVNode("select", {
                      "onUpdate:modelValue": ($event) => s.media_type = $event
                    }, [..._cache[44] || (_cache[44] = [
                      _createElementVNode("option", { value: "movie" }, "电影", -1),
                      _createElementVNode("option", { value: "tv" }, "电视剧", -1)
                    ])], 8, _hoisted_8), [
                      [_vModelSelect, s.media_type]
                    ])
                  ]),
                  _createElementVNode("button", {
                    onClick: ($event) => sources.value.splice(i, 1),
                    "aria-label": "删除来源"
                  }, " 删除 ", 8, _hoisted_9)
                ]),
                _createElementVNode("div", _hoisted_10, [
                  _createElementVNode("label", null, [
                    _cache[46] || (_cache[46] = _createTextVNode("115 待整理来源", -1)),
                    _withDirectives(_createElementVNode("input", {
                      "onUpdate:modelValue": ($event) => s.source_path = $event,
                      placeholder: "/待整理/Movie"
                    }, null, 8, _hoisted_11), [
                      [_vModelText, s.source_path]
                    ])
                  ]),
                  _createElementVNode("button", {
                    onClick: ($event) => openBrowser(i, "source_path")
                  }, "选择目录", 8, _hoisted_12)
                ]),
                _createElementVNode("div", _hoisted_13, [
                  _createElementVNode("label", null, [
                    _cache[47] || (_cache[47] = _createTextVNode("目标媒体库根目录", -1)),
                    _withDirectives(_createElementVNode("input", {
                      "onUpdate:modelValue": ($event) => s.target_root_path = $event,
                      placeholder: "/媒体库/Movie"
                    }, null, 8, _hoisted_14), [
                      [_vModelText, s.target_root_path]
                    ])
                  ]),
                  _createElementVNode("button", {
                    onClick: ($event) => openBrowser(i, "target_root_path")
                  }, " 选择目录 ", 8, _hoisted_15)
                ]),
                _cache[48] || (_cache[48] = _createElementVNode("p", null, " 目标不能位于任何来源目录内。目标根目录下的分类目录需与 MoviePilot 分类匹配。 ", -1))
              ]);
            }), 128)),
            _createElementVNode("button", { onClick: add }, "＋ 添加来源")
          ], 64)),
          browser.value ? (_openBlock(), _createElementBlock("div", _hoisted_16, [
            _createElementVNode("b", null, "选择目录：" + _toDisplayString(browser.value.path), 1),
            _cache[49] || (_cache[49] = _createElementVNode("p", null, " 使用已保存的连接。首次配置请先保存 Cookie 和路径，再打开目录选择。 ", -1)),
            browser.value.message ? (_openBlock(), _createElementBlock("p", _hoisted_17, _toDisplayString(browser.value.message), 1)) : _createCommentVNode("", true),
            _createElementVNode("div", _hoisted_18, [
              _createElementVNode("button", {
                onClick: _cache[4] || (_cache[4] = ($event) => browse(parent())),
                disabled: browsersLoading.value || browser.value.path === "/"
              }, " 上一级", 8, _hoisted_19),
              _createElementVNode("button", {
                onClick: selectDirectory,
                disabled: browsersLoading.value
              }, " 使用当前目录", 8, _hoisted_20),
              _createElementVNode("button", {
                onClick: _cache[5] || (_cache[5] = ($event) => browser.value = null)
              }, "取消")
            ]),
            _createElementVNode("ul", null, [
              (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(browser.value.items, (d) => {
                return _openBlock(), _createElementBlock("li", {
                  key: d.cid
                }, [
                  _createElementVNode("button", {
                    onClick: ($event) => browse(child(d.name)),
                    disabled: browsersLoading.value
                  }, " 📁 " + _toDisplayString(d.name), 9, _hoisted_21)
                ]);
              }), 128))
            ]),
            !browser.value.items.length && !browsersLoading.value ? (_openBlock(), _createElementBlock("p", _hoisted_22, "暂无子目录。")) : _createCommentVNode("", true)
          ])) : _createCommentVNode("", true)
        ]),
        _createElementVNode("fieldset", null, [
          _cache[68] || (_cache[68] = _createElementVNode("legend", null, "3. 自动运行与整理策略", -1)),
          _createElementVNode("div", _hoisted_23, [
            _createElementVNode("label", _hoisted_24, [
              _withDirectives(_createElementVNode("input", {
                "onUpdate:modelValue": _cache[6] || (_cache[6] = ($event) => config.value.enabled = $event),
                type: "checkbox"
              }, null, 512), [
                [_vModelCheckbox, config.value.enabled]
              ]),
              _cache[51] || (_cache[51] = _createTextVNode("启用定时服务", -1))
            ]),
            _createElementVNode("label", _hoisted_25, [
              _withDirectives(_createElementVNode("input", {
                "onUpdate:modelValue": _cache[7] || (_cache[7] = ($event) => config.value.notify = $event),
                type: "checkbox"
              }, null, 512), [
                [_vModelCheckbox, config.value.notify]
              ]),
              _cache[52] || (_cache[52] = _createTextVNode("发送结果通知", -1))
            ])
          ]),
          _createElementVNode("label", null, [
            _cache[54] || (_cache[54] = _createTextVNode("定时模式", -1)),
            _withDirectives(_createElementVNode("select", {
              "onUpdate:modelValue": _cache[8] || (_cache[8] = ($event) => config.value.dry_run = $event)
            }, [..._cache[53] || (_cache[53] = [
              _createElementVNode("option", { value: true }, "仅生成预览（推荐）", -1),
              _createElementVNode("option", { value: false }, "生成后自动执行", -1)
            ])], 512), [
              [_vModelSelect, config.value.dry_run]
            ])
          ]),
          _cache[69] || (_cache[69] = _createElementVNode("p", null, "手动执行始终需要确认摘要；无需为手动执行关闭“仅生成预览”。", -1)),
          _createElementVNode("label", null, [
            _cache[56] || (_cache[56] = _createTextVNode("运行时间", -1)),
            _createElementVNode("select", {
              onChange: _cache[9] || (_cache[9] = ($event) => config.value.cron = $event.target.value)
            }, [..._cache[55] || (_cache[55] = [
              _createElementVNode("option", { value: "" }, "选择常用时间", -1),
              _createElementVNode("option", { value: "0 3 * * *" }, "每天凌晨 3 点", -1),
              _createElementVNode("option", { value: "0 */6 * * *" }, "每 6 小时", -1),
              _createElementVNode("option", { value: "0 3 * * 0" }, "每周日凌晨 3 点", -1)
            ])], 32)
          ]),
          _createElementVNode("label", null, [
            _cache[57] || (_cache[57] = _createTextVNode("五段 CRON（留空不自动运行）", -1)),
            _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": _cache[10] || (_cache[10] = ($event) => config.value.cron = $event),
              placeholder: "0 3 * * *"
            }, null, 512), [
              [_vModelText, config.value.cron]
            ])
          ]),
          _createElementVNode("label", _hoisted_26, [
            _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": _cache[11] || (_cache[11] = ($event) => config.value.onlyonce = $event),
              type: "checkbox"
            }, null, 512), [
              [_vModelCheckbox, config.value.onlyonce]
            ]),
            _cache[58] || (_cache[58] = _createTextVNode("保存后立即运行一次（遵循定时模式）", -1))
          ]),
          _createElementVNode("div", _hoisted_27, [
            _createElementVNode("label", _hoisted_28, [
              _withDirectives(_createElementVNode("input", {
                "onUpdate:modelValue": _cache[12] || (_cache[12] = ($event) => config.value.delete_empty_source_dirs = $event),
                type: "checkbox"
              }, null, 512), [
                [_vModelCheckbox, config.value.delete_empty_source_dirs]
              ]),
              _cache[59] || (_cache[59] = _createTextVNode("整理后清理空来源目录", -1))
            ]),
            _createElementVNode("label", _hoisted_29, [
              _withDirectives(_createElementVNode("input", {
                "onUpdate:modelValue": _cache[13] || (_cache[13] = ($event) => config.value.refresh_plex_after_execute = $event),
                type: "checkbox"
              }, null, 512), [
                [_vModelCheckbox, config.value.refresh_plex_after_execute]
              ]),
              _cache[60] || (_cache[60] = _createTextVNode("整理后刷新 Plex", -1))
            ])
          ]),
          _createElementVNode("div", _hoisted_30, [
            _createElementVNode("label", null, [
              _cache[61] || (_cache[61] = _createTextVNode("单次扫描最多文件（0 不限）", -1)),
              _withDirectives(_createElementVNode("input", {
                "onUpdate:modelValue": _cache[14] || (_cache[14] = ($event) => config.value.max_items_per_run = $event),
                type: "number",
                min: "0",
                max: "10000"
              }, null, 512), [
                [
                  _vModelText,
                  config.value.max_items_per_run,
                  void 0,
                  { number: true }
                ]
              ])
            ]),
            _createElementVNode("label", null, [
              _cache[62] || (_cache[62] = _createTextVNode("最小文件体积（MB）", -1)),
              _withDirectives(_createElementVNode("input", {
                "onUpdate:modelValue": _cache[15] || (_cache[15] = ($event) => config.value.min_file_size_mb = $event),
                type: "number",
                min: "0"
              }, null, 512), [
                [
                  _vModelText,
                  config.value.min_file_size_mb,
                  void 0,
                  { number: true }
                ]
              ])
            ]),
            _createElementVNode("label", null, [
              _cache[63] || (_cache[63] = _createTextVNode("扫描深度", -1)),
              _withDirectives(_createElementVNode("input", {
                "onUpdate:modelValue": _cache[16] || (_cache[16] = ($event) => config.value.max_depth = $event),
                type: "number",
                min: "0",
                max: "30"
              }, null, 512), [
                [
                  _vModelText,
                  config.value.max_depth,
                  void 0,
                  { number: true }
                ]
              ])
            ])
          ]),
          _createElementVNode("label", null, [
            _cache[65] || (_cache[65] = _createTextVNode("重名策略", -1)),
            _withDirectives(_createElementVNode("select", {
              "onUpdate:modelValue": _cache[17] || (_cache[17] = ($event) => config.value.conflict_strategy = $event)
            }, [..._cache[64] || (_cache[64] = [
              _createElementVNode("option", { value: "skip" }, "跳过，不覆盖", -1),
              _createElementVNode("option", { value: "rename_with_suffix" }, "自动添加后缀", -1)
            ])], 512), [
              [_vModelSelect, config.value.conflict_strategy]
            ])
          ]),
          _createElementVNode("label", null, [
            _cache[67] || (_cache[67] = _createTextVNode("无法识别的文件", -1)),
            _withDirectives(_createElementVNode("select", {
              "onUpdate:modelValue": _cache[18] || (_cache[18] = ($event) => config.value.unrecognized_action = $event)
            }, [..._cache[66] || (_cache[66] = [
              _createElementVNode("option", { value: "skip" }, "跳过并显示原因", -1),
              _createElementVNode("option", { value: "move_to_unrecognized" }, " 移动到未识别 CID（须在高级项配置） ", -1)
            ])], 512), [
              [_vModelSelect, config.value.unrecognized_action]
            ])
          ])
        ]),
        _createElementVNode("button", {
          onClick: _cache[19] || (_cache[19] = ($event) => advanced.value = !advanced.value)
        }, _toDisplayString(advanced.value ? "收起" : "展开") + "高级设置 ", 1),
        advanced.value ? (_openBlock(), _createElementBlock("fieldset", _hoisted_31, [
          _cache[83] || (_cache[83] = _createElementVNode("legend", null, "高级设置", -1)),
          _createElementVNode("label", null, [
            _cache[70] || (_cache[70] = _createTextVNode("目标 CID 覆盖 JSON", -1)),
            _withDirectives(_createElementVNode("textarea", {
              "onUpdate:modelValue": _cache[20] || (_cache[20] = ($event) => config.value.target_cids = $event),
              rows: "5"
            }, null, 512), [
              [_vModelText, config.value.target_cids]
            ])
          ]),
          _createElementVNode("label", null, [
            _cache[71] || (_cache[71] = _createTextVNode("分类别名 JSON", -1)),
            _withDirectives(_createElementVNode("textarea", {
              "onUpdate:modelValue": _cache[21] || (_cache[21] = ($event) => config.value.category_mapping = $event),
              rows: "5"
            }, null, 512), [
              [_vModelText, config.value.category_mapping]
            ])
          ]),
          _createElementVNode("label", null, [
            _cache[72] || (_cache[72] = _createTextVNode("排除关键词（逗号分隔）", -1)),
            _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": _cache[22] || (_cache[22] = ($event) => config.value.exclude_keywords = $event)
            }, null, 512), [
              [_vModelText, config.value.exclude_keywords]
            ])
          ]),
          _createElementVNode("label", _hoisted_32, [
            _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": _cache[23] || (_cache[23] = ($event) => config.value.allow_external_execute = $event),
              type: "checkbox"
            }, null, 512), [
              [_vModelCheckbox, config.value.allow_external_execute]
            ]),
            _cache[73] || (_cache[73] = _createTextVNode("允许 API Key 外部自动执行（默认关闭）", -1))
          ]),
          _createElementVNode("div", _hoisted_33, [
            _createElementVNode("label", null, [
              _cache[74] || (_cache[74] = _createTextVNode("批大小", -1)),
              _withDirectives(_createElementVNode("input", {
                "onUpdate:modelValue": _cache[24] || (_cache[24] = ($event) => config.value.batch_size = $event),
                type: "number",
                min: "1",
                max: "100"
              }, null, 512), [
                [
                  _vModelText,
                  config.value.batch_size,
                  void 0,
                  { number: true }
                ]
              ])
            ]),
            _createElementVNode("label", null, [
              _cache[75] || (_cache[75] = _createTextVNode("批间隔（秒）", -1)),
              _withDirectives(_createElementVNode("input", {
                "onUpdate:modelValue": _cache[25] || (_cache[25] = ($event) => config.value.sleep_between_batches = $event),
                type: "number",
                min: "0",
                max: "120",
                step: "0.1"
              }, null, 512), [
                [
                  _vModelText,
                  config.value.sleep_between_batches,
                  void 0,
                  { number: true }
                ]
              ])
            ]),
            _createElementVNode("label", null, [
              _cache[76] || (_cache[76] = _createTextVNode("计划有效期（小时）", -1)),
              _withDirectives(_createElementVNode("input", {
                "onUpdate:modelValue": _cache[26] || (_cache[26] = ($event) => config.value.plan_ttl_hours = $event),
                type: "number",
                min: "1",
                max: "720"
              }, null, 512), [
                [
                  _vModelText,
                  config.value.plan_ttl_hours,
                  void 0,
                  { number: true }
                ]
              ])
            ])
          ]),
          _createElementVNode("div", _hoisted_34, [
            _createElementVNode("label", null, [
              _cache[77] || (_cache[77] = _createTextVNode("请求间隔（毫秒）", -1)),
              _withDirectives(_createElementVNode("input", {
                "onUpdate:modelValue": _cache[27] || (_cache[27] = ($event) => config.value.min_request_interval_ms = $event),
                type: "number",
                min: "0"
              }, null, 512), [
                [
                  _vModelText,
                  config.value.min_request_interval_ms,
                  void 0,
                  { number: true }
                ]
              ])
            ]),
            _createElementVNode("label", null, [
              _cache[78] || (_cache[78] = _createTextVNode("重试次数", -1)),
              _withDirectives(_createElementVNode("input", {
                "onUpdate:modelValue": _cache[28] || (_cache[28] = ($event) => config.value.max_retries = $event),
                type: "number",
                min: "0",
                max: "10"
              }, null, 512), [
                [
                  _vModelText,
                  config.value.max_retries,
                  void 0,
                  { number: true }
                ]
              ])
            ]),
            _createElementVNode("label", null, [
              _cache[79] || (_cache[79] = _createTextVNode("退避基数（秒）", -1)),
              _withDirectives(_createElementVNode("input", {
                "onUpdate:modelValue": _cache[29] || (_cache[29] = ($event) => config.value.retry_base_seconds = $event),
                type: "number",
                min: "0.1",
                step: "0.1"
              }, null, 512), [
                [
                  _vModelText,
                  config.value.retry_base_seconds,
                  void 0,
                  { number: true }
                ]
              ])
            ])
          ]),
          _createElementVNode("div", _hoisted_35, [
            _createElementVNode("label", null, [
              _cache[80] || (_cache[80] = _createTextVNode("抖动比例", -1)),
              _withDirectives(_createElementVNode("input", {
                "onUpdate:modelValue": _cache[30] || (_cache[30] = ($event) => config.value.jitter_ratio = $event),
                type: "number",
                min: "0",
                max: "1",
                step: "0.1"
              }, null, 512), [
                [
                  _vModelText,
                  config.value.jitter_ratio,
                  void 0,
                  { number: true }
                ]
              ])
            ]),
            _createElementVNode("label", null, [
              _cache[81] || (_cache[81] = _createTextVNode("目录分页大小", -1)),
              _withDirectives(_createElementVNode("input", {
                "onUpdate:modelValue": _cache[31] || (_cache[31] = ($event) => config.value.list_page_size = $event),
                type: "number",
                min: "50",
                max: "1000"
              }, null, 512), [
                [
                  _vModelText,
                  config.value.list_page_size,
                  void 0,
                  { number: true }
                ]
              ])
            ]),
            _createElementVNode("label", null, [
              _cache[82] || (_cache[82] = _createTextVNode("历史保留数", -1)),
              _withDirectives(_createElementVNode("input", {
                "onUpdate:modelValue": _cache[32] || (_cache[32] = ($event) => config.value.history_limit = $event),
                type: "number",
                min: "1"
              }, null, 512), [
                [
                  _vModelText,
                  config.value.history_limit,
                  void 0,
                  { number: true }
                ]
              ])
            ])
          ])
        ])) : _createCommentVNode("", true),
        _createElementVNode("footer", _hoisted_36, [
          _createElementVNode("button", {
            onClick: _cache[33] || (_cache[33] = ($event) => validate(false)),
            disabled: !canSave.value
          }, "检查配置格式", 8, _hoisted_37),
          _createElementVNode("button", {
            class: "primary",
            onClick: _cache[34] || (_cache[34] = ($event) => validate(true)),
            disabled: !canSave.value
          }, _toDisplayString(validating.value ? "检查中…" : "检查并保存"), 9, _hoisted_38),
          _createElementVNode("button", {
            onClick: _cache[35] || (_cache[35] = ($event) => emit("switch"))
          }, "查看详情"),
          _createElementVNode("button", {
            onClick: _cache[36] || (_cache[36] = ($event) => emit("close"))
          }, "关闭")
        ])
      ]);
    };
  }
});

const Config = /* @__PURE__ */ _export_sfc(_sfc_main, [["__scopeId", "data-v-ae6ba87d"]]);

export { Config as default };
