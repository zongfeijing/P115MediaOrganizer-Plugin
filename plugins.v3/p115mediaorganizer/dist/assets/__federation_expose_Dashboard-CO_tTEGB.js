import { importShared } from './__federation_fn_import-JrT3xvdd.js';
import { c as client, i as icons, _ as _export_sfc } from './_plugin-vue_export-helper-CZk8cyVf.js';

const {defineComponent:_defineComponent} = await importShared('vue');

const {unref:_unref,resolveComponent:_resolveComponent,createVNode:_createVNode,createElementVNode:_createElementVNode,toDisplayString:_toDisplayString,createTextVNode:_createTextVNode,withCtx:_withCtx,openBlock:_openBlock,createBlock:_createBlock,createCommentVNode:_createCommentVNode,Fragment:_Fragment,createElementBlock:_createElementBlock} = await importShared('vue');

const _hoisted_1 = { class: "p115-dashboard pa-4" };
const _hoisted_2 = { class: "d-flex align-center ga-2 mb-3" };
const _hoisted_3 = { class: "d-flex align-center justify-space-between mb-2" };
const _hoisted_4 = { class: "text-h6 text-primary" };
const _hoisted_5 = { class: "text-caption text-medium-emphasis mt-3 p115-wrap" };
const {onMounted,ref} = await importShared('vue');
const _sfc_main = /* @__PURE__ */ _defineComponent({
  __name: "Dashboard",
  props: {
    api: {},
    pluginId: {},
    sourcePluginId: {}
  },
  setup(__props) {
    const props = __props;
    const state = ref(null), error = ref("");
    onMounted(async () => {
      try {
        state.value = await client(props).get("workflow");
      } catch (e) {
        error.value = e.message;
      }
    });
    return (_ctx, _cache) => {
      const _component_VIcon = _resolveComponent("VIcon");
      const _component_VAlert = _resolveComponent("VAlert");
      const _component_VChip = _resolveComponent("VChip");
      const _component_VProgressLinear = _resolveComponent("VProgressLinear");
      return _openBlock(), _createElementBlock("section", _hoisted_1, [
        _createElementVNode("div", _hoisted_2, [
          _createVNode(_component_VIcon, {
            icon: _unref(icons).mdiCloudCheckOutline,
            color: "primary",
            size: "22"
          }, null, 8, ["icon"]),
          _cache[0] || (_cache[0] = _createElementVNode("span", { class: "text-subtitle-2" }, "115 云端媒体整理", -1))
        ]),
        error.value ? (_openBlock(), _createBlock(_component_VAlert, {
          key: 0,
          type: "warning",
          variant: "tonal",
          density: "compact"
        }, {
          default: _withCtx(() => [
            _createTextVNode(_toDisplayString(error.value), 1)
          ]),
          _: 1
        })) : _createCommentVNode("", true),
        state.value ? (_openBlock(), _createElementBlock(_Fragment, { key: 1 }, [
          _createElementVNode("div", _hoisted_3, [
            _cache[1] || (_cache[1] = _createElementVNode("span", { class: "text-caption text-medium-emphasis" }, "待执行", -1)),
            _createElementVNode("span", _hoisted_4, _toDisplayString(state.value.plan.executable), 1)
          ]),
          _createVNode(_component_VChip, {
            size: "x-small",
            variant: "tonal",
            color: state.value.connection.ok === true ? "success" : "warning"
          }, {
            default: _withCtx(() => [
              _createTextVNode(_toDisplayString(state.value.connection.ok === true ? "连接正常" : "连接待检查"), 1)
            ]),
            _: 1
          }, 8, ["color"]),
          _createElementVNode("p", _hoisted_5, _toDisplayString(state.value.task.message), 1)
        ], 64)) : !error.value ? (_openBlock(), _createBlock(_component_VProgressLinear, {
          key: 2,
          indeterminate: "",
          color: "primary",
          rounded: ""
        })) : _createCommentVNode("", true)
      ]);
    };
  }
});

const Dashboard = /* @__PURE__ */ _export_sfc(_sfc_main, [["__scopeId", "data-v-2df5e73b"]]);

export { Dashboard as default };
