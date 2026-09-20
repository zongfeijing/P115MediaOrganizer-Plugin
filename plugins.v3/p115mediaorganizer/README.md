# 115云端媒体整理（MoviePilot V3）

将 115 待处理目录中的电影和电视剧直接在云端识别、分类、重命名并移动到媒体库；不下载文件，也不创建 STRM。

## V3 适配说明

- 使用 MoviePilot V3 的稳定 SDK 读取配置、日志、媒体服务、媒体元数据和分类能力。
- 计划数据使用 `media_source` + `media_id` 记录统一媒体身份，不再把 TMDB ID 当作通用主键。
- 优先读取 V3 的 `library_category`，并通过统一分类服务执行兜底分类。
- 通过文件管理模块公开的 `recommend_name()` 生成与 MoviePilot 当前模板一致的目标名称。
- 第三方依赖由 `pyproject.toml` 声明并在安装/更新插件时由 MoviePilot 统一安装；V3 版本不再从插件运行时触发 pip。

## 依赖

插件依赖 `p115client==0.0.9.6.5.1`。若依赖安装失败，请检查 MoviePilot 的 PIP 镜像和网络配置，然后在插件市场中重新安装或更新插件。

## 配置要点

- `cookie_path`：MoviePilot 容器内的 115 Cookie 文件路径，例如 `/config/115-cookies.txt`。
- `cookie_text`：无法挂载文件时可直接填写 Cookie。
- `source_mappings`：配置电影/电视剧的 115 来源路径和媒体库目标根路径。
- `target_cids`：可选高级覆盖；通常保持分类 CID 为空，让插件按 `{target_root_path}/{MoviePilot分类名}` 自动解析。
- `category_mapping`：可选分类别名映射。
- `dry_run`：建议先保持开启，确认计划后再执行。

执行成功后，插件可按本次涉及的分类刷新 MoviePilot 中已连接的 Plex 媒体库。
