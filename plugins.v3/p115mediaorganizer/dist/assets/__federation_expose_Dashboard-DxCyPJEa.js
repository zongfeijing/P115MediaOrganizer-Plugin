import { importShared } from './__federation_fn_import-JrT3xvdd.js';
import { c as client, _ as _export_sfc } from './_plugin-vue_export-helper-Dt9Z4jcE.js';

const {defineComponent:_defineComponent} = await importShared('vue');

const {createElementVNode:_createElementVNode,toDisplayString:_toDisplayString,openBlock:_openBlock,createElementBlock:_createElementBlock,createCommentVNode:_createCommentVNode,Fragment:_Fragment} = await importShared('vue');

const _hoisted_1 = { class: "p115-dashboard" };
const _hoisted_2 = { key: 0 };
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
      return _openBlock(), _createElementBlock("section", _hoisted_1, [
        _cache[0] || (_cache[0] = _createElementVNode("b", null, "115 云端媒体整理", -1)),
        error.value ? (_openBlock(), _createElementBlock("p", _hoisted_2, _toDisplayString(error.value), 1)) : _createCommentVNode("", true),
        state.value ? (_openBlock(), _createElementBlock(_Fragment, { key: 1 }, [
          _createElementVNode("p", null, _toDisplayString(state.value.task.message), 1),
          _createElementVNode("p", null, " 待执行 " + _toDisplayString(state.value.plan.executable) + " · " + _toDisplayString(state.value.connection.message), 1)
        ], 64)) : _createCommentVNode("", true)
      ]);
    };
  }
});

const Dashboard = /* @__PURE__ */ _export_sfc(_sfc_main, [["__scopeId", "data-v-f970f3df"]]);

export { Dashboard as default };
