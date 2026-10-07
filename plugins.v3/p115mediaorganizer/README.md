# 115云端媒体整理（MoviePilot V3）

将 115 待处理目录中的电影和电视剧直接在云端识别、分类、重命名并移动到媒体库；不下载文件，也不创建 STRM。

## V3 适配说明

- 使用 MoviePilot V3 的稳定 SDK 读取配置、日志、媒体服务、媒体元数据和分类能力。
- 计划数据使用 `media_source` + `media_id` 记录统一媒体身份，不再把 TMDB ID 当作通用主键。
- 优先读取 V3 的 `library_category`，并通过统一分类服务执行兜底分类。
- 通过文件管理模块公开的 `recommend_name()` 生成与 MoviePilot 当前模板一致的目标名称。
- 第三方依赖由 `pyproject.toml` 声明并在安装/更新插件时由 MoviePilot 统一安装；V3 版本不再从插件运行时触发 pip。

## 依赖

插件固定使用 `p115client==0.0.9.7.2` 和 `python-concurrenttools==0.1.9`，两者需要配套升级。旧版 `p115client==0.0.9.6.5.1` 仍导入 `threadpool_map` / `taskgroup_map`，不能与 `python-concurrenttools==0.1.9` 混用。

若依赖安装失败，请检查 MoviePilot 的 PIP 镜像和网络配置，然后在插件市场中重新安装或更新插件。

## 配置要点

- `cookie_path`：MoviePilot 容器内的 115 Cookie 文件路径，例如 `/config/115-cookies.txt`。
- `cookie_text`：无法挂载文件时可直接填写 Cookie。
- `source_mappings`：配置电影/电视剧的 115 来源路径和媒体库目标根路径。
- `target_cids`：可选高级覆盖；通常保持分类 CID 为空，让插件按 `{target_root_path}/{MoviePilot分类名}` 自动解析。
- `category_mapping`：可选分类别名映射。
- `dry_run`：建议先保持开启，确认计划后再执行。

V3 通过 `P115Client(cookies=...)` 使用现有 Cookie，不再传入新版客户端已移除的 `check_for_relogin`。Cookie 失效时会明确报错并停止，不保证自动续期或在后台发起扫码登录。

执行成功后，插件可按本次涉及的分类刷新 MoviePilot 中已连接的 Plex 媒体库。

## 依赖兼容性测试

普通合同测试不要求安装第三方客户端：

```sh
python -m unittest discover -s tests -v
```

在 Python 3.12+ 的独立环境中安装上述固定依赖后，可以运行真实客户端测试：

```sh
P115_REQUIRE_DEPENDENCY_TESTS=1 python -m unittest tests.v3.p115mediaorganizer.test_dependencies -v
```

测试使用虚构 Cookie，拦截网络连接并记录客户端请求，不连接真实 115 账号，也不移动、重命名或删除云端文件。

## v1.3.0 使用流程与边界

1. **配置**：选择 Cookie 文本或文件，添加来源卡片并填写完整 115 路径。可保留旧 JSON 配置；写错、空数组或缺字段会明确报错，不再启用示例目录。支持可视化编辑和高级 JSON 两种方式。
2. **检查**：保存后在详情页检查连接与目录。目录选择器使用已经保存的 Cookie，首次安装可以先手动填路径保存；不会将未保存的 Cookie 发送给目录接口。
3. **生成预览**：后台扫描并识别，多个来源共享一个计划 ID。未识别、已处理、小文件和目录读取失败等情况都有诊断记录，不再只显示“0 条”。达到扫描上限会明确提示。
4. **确认执行**：预览展示识别结果和完整目标路径。手动执行需要管理员登录会话和 120 秒内有效的一次性确认，不能用 API Key 替代；执行全部有效项目，而不是仅当前页。它不会修改定时服务的“仅生成预览”设置。
5. **进度与停止**：任务通过宿主一次性调度器运行，关闭页面不会中断任务。停止扫描在读取/识别边界生效；停止执行会完成当前批次再停，跳过后续清理/刷新，保留已完成项目。已开始的移动/重命名不可一键撤销，不提供回滚承诺。
6. **查记录**：计划、扫描诊断、历史和批次均可分页、按状态筛选、按文件名/路径/错误/批次 ID 搜索。手机不再只能看前 20 条；扫描诊断保留上限 5000 条，汇总计数覆盖全部。

### 升级注意

- 需要支持 Vue 联邦插件与 `app.sdk.scheduler.add_plugin_once_job` 的 MoviePilot V3；本次目标宿主为 v3.1.1。保留旧配置/历史，不更改 V2。
- 不再给定时服务自建调度器。调度器不可用时明确报错，不退化为失控的后台线程。
- 健康检查区分依赖错误、配置错误、Cookie 失效、限频及网络失败。网络失败时 Cookie 有效性为“未知”，不要贸然更换 Cookie。
- 页面加载读取缓存的健康状态，不同步访问 115；点击检查才刷新状态。
- 新扫描失败/取消时旧计划失效，避免误执行旧预览。已执行结果逐项存档；主程序重启不自动续跑任务，需人工检查剩余项目并重新确认。
- 分类目录仍需实际存在，不在仅预览阶段创建目录。高级 CID 覆盖时应自行确认对应目录；未识别 CID 模式显示 CID 目标，而不伪造完整路径。
- 选择部分项目执行、手动改识别结果属于后续阶段，本次未提供。

### 前端开发与验证

`frontend/` 使用宿主传入的实例作用域 `api`，共享宿主 Vue，不打包 Vuetify/MDI 全局样式；发布必须包含 `dist/assets/remoteEntry.js` 及所有同目录构建产物。

```sh
cd frontend
npm ci
npm test
npm run build
```

本地无账号预览：`node node_modules/vite/bin/vite.js --config vite.preview.config.ts`，打开 localhost 的 `/preview.html`。该预览 API 是纯虚构数据，不连接 NAS 或 115。


### MP 原生界面（v1.3.1）

详情页采用当前阶段主操作、原生状态 Chip/Tabs/分页，桌面表格和手机卡片共享全部记录。配置页分为连接与目录、自动化、高级；正常执行使用主题主色，风险通过确认摘要表达。

远程组件直接使用宿主已注册的 Vuetify，不导入全局样式或创建主题。`vuetify` 开发依赖仅供独立预览和组件测试。少量 MDI SVG 路径随插件打包，不需要在线加载图标。`npm run build` 会检查生产 CSS 作用域与 UI 运行时隔离。
