# 115云端媒体整理

将 115 网盘「最近接收」中的电影、电视剧文件在云端直接整理到媒体库目录。

## 功能

- 扫描 `/最近接收/Movie` 与 `/最近接收/TV` 对应的 115 CID。
- 支持通过 `source_mappings` 配置多个来源目录，例如 workspace 的 `Incoming/Movie` -> `movie`、`Incoming/TV` -> `tv`。
- 默认递归展开目录，只处理视频文件。
- 使用 MoviePilot 内部识别链路识别媒体信息与分类。
- 根据分类映射移动到电影或电视剧目标分类目录。
- 支持 dry-run 先生成计划，再执行最近一次保存的计划。
- 执行前校验 profile、分类映射、目标 CID 等配置快照。

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

- `profile=workspace`
- `dry_run=true`
- `allow_production_execute=false`
- 未识别项目跳过
- 目标重名跳过

执行生产目录整理必须同时满足：

- `dry_run=false`
- `profile=production`
- `allow_production_execute=true`
- 最近一次计划的配置快照与当前配置完全一致

## 推荐流程

1. 保持 `profile=workspace` 和 `dry_run=true`。
2. 调用 dry-run API 或使用立即运行生成计划。
3. 在插件详情页检查前 50 条计划和 warning。
4. 确认无误后设置 `dry_run=false`，执行最近一次计划。
5. workspace 验证完成后，再切到 production 并重新 dry-run。

## 注意事项

- 目标 CID 与个人 115 网盘强绑定，请在高级配置中按需覆盖 `target_cids`。
- 来源目录与个人 115 网盘强绑定，请在高级配置中按需覆盖 `source_mappings`。
- 默认会在执行后删除来源根目录下面的空目录，但不会删除来源根目录本身。
- 如果 115 返回 `errno=990009` 或类似「操作尚未执行完成」，插件会记录失败，不会无限重试。
- 电视剧未识别到明确季集时会保留源文件名并添加 warning。

## 来源映射示例

```json
[
  {
    "name": "workspace电影待处理",
    "media_type": "movie",
    "source_cid": "你的电影待处理目录CID",
    "source_path": "/你的媒体库/_Workspace/Incoming/Movie"
  },
  {
    "name": "workspace电视剧待处理",
    "media_type": "tv",
    "source_cid": "你的电视剧待处理目录CID",
    "source_path": "/你的媒体库/_Workspace/Incoming/TV"
  }
]
```
