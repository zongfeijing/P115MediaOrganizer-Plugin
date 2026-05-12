# 115云端媒体整理

将 115 网盘「最近接收」中的电影、电视剧文件在云端直接整理到媒体库目录。

## 功能

- 扫描 `/最近接收/Movie` 与 `/最近接收/TV` 对应的 115 CID。
- 支持通过 `source_mappings` 配置多个来源目录，例如 `Incoming/Movie` -> `movie`、`Incoming/TV` -> `tv`。
- 默认递归展开目录，只处理视频文件。
- 使用 MoviePilot 内部识别链路识别媒体信息与分类。
- 默认按 MoviePilot 分类名移动到同名目标分类目录。
- 命名优先复用 MoviePilot 的重命名模板与智能重命名事件。
- 支持 dry-run 先生成计划，再执行最近一次保存的计划。
- 整理成功后可按本次涉及的分类目录刷新对应 Plex 媒体库。
- 历史页按执行批次展示摘要，并保留最近明细用于排错。
- 执行前校验 来源目录、目标目录等配置快照。

## 不做什么

- 不生成 STRM 文件。
- 不下载媒体到本地。
- 不调用外部脚本。
- v0.1.0 不覆盖目标目录中的同名文件。

## 依赖

插件依赖 `p115client`。如果依赖未安装或 Cookie 不可用，插件仍会加载，但页面和 API 会显示错误。

默认 Cookie 路径为：

```text
/config/115-cookies.txt
```

## 安全模型

默认配置为：

- `dry_run=true`
- 未识别项目跳过
- 目标重名跳过

执行整理必须满足：

- `dry_run=false`
- 最近一次计划的配置快照与当前配置完全一致

## 推荐流程

1. 保持 `dry_run=true`。
2. 调用 dry-run API 或使用立即运行生成计划。
3. 在插件详情页检查前 50 条计划和 warning。
4. 确认无误后设置 `dry_run=false`，执行最近一次计划。


## OpenClaw 触发示例

OpenClaw 转存完成后可以调用插件 API：

```bash
curl -X POST \
  "http://MOVIEPILOT_HOST:3001/api/v1/plugin/P115MediaOrganizer/trigger?apikey=YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"source":"openclaw","execute":true}'
```

- `dry_run=true` 时只生成计划，除非额外传 `force_execute=true`。
- `dry_run=false` 且 `execute=true` 时，会先生成最新计划，再执行移动。
- `execute=false` 时只生成计划。

## Plex 刷新

默认启用 `refresh_plex_after_execute`。执行整理后，插件会收集本次成功移动的项目，按 `media_type + target_category` 去重，并调用 MoviePilot 已配置的 Plex 媒体服务器刷新对应分类目录，例如：

```text
/媒体库/Movie/华语电影
/媒体库/TV/国产剧
```

- `plex_mediaservers` 留空时刷新全部已配置且可连接的 Plex 服务器。
- 配置了 `plex_mediaservers` 时只刷新选中的 Plex 服务器。
- 没有成功整理项目、Plex 不可用或未配置时，不影响 115 整理结果，只在日志与详情页记录刷新状态。

## 注意事项

- 路径配置会自动解析目标目录；只有需要手动覆盖时才配置 `target_cids`。
- 来源目录通过 `source_mappings` 配置 115 路径。
- `category_mapping` 是可选别名映射；如果 MoviePilot 分类名和目标目录名一致，可以保持默认空映射。
- 生成计划时会使用 MoviePilot 当前的电影/电视剧重命名模板；模板不可用时才使用内置兜底命名。
- `history_limit` 控制明细保留条数，`run_limit` 控制批次摘要保留数量。
- 默认会在执行后删除来源根目录下面的空目录，但不会删除来源根目录本身。
- 如果 115 返回 `errno=990009` 或类似「操作尚未执行完成」，插件会记录失败，不会无限重试。
- 电视剧未识别到明确季集时会保留源文件名并添加 warning。

## 来源映射示例

```json
[
  {
    "name": "电影待处理",
    "media_type": "movie",
    "source_path": "/待整理/Movie",
    "target_root_path": "/媒体库/Movie"
  },
  {
    "name": "电视剧待处理",
    "media_type": "tv",
    "source_path": "/待整理/TV",
    "target_root_path": "/媒体库/TV"
  }
]
```

## 分类别名映射示例

默认不需要配置。只有当 MoviePilot 分类名和你的目标分类目录名不一致时才需要填写，例如：

```json
{
  "tv": {
    "日番": "日韩剧"
  }
}
```
