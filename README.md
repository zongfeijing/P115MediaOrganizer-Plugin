# P115MediaOrganizer

MoviePilot V2 plugin for organizing media files directly inside 115 cloud drive.

This plugin scans configured 115 source folders, uses MoviePilot recognition and category rules, then moves/renames files in 115 to the matching media library folders. It does not download files and does not create STRM files.

## Install In MoviePilot

Use this repository URL as a third-party plugin market/source in MoviePilot, then install `115云端媒体整理`.

```text
https://github.com/zongfeijing/P115MediaOrganizer-Plugin
```

The V2 plugin index is `package.v2.json`, and the plugin code is under:

```text
plugins.v2/p115mediaorganizer
```

## Configuration

### 115 Connection

The plugin uses `p115client`, so it needs a 115 web cookie.

Cookie options:

- `cookie_path`: point it to a cookie file mounted inside the MoviePilot container, for example `/config/115-cookies.txt`.
- `cookie_text`: paste a cookie directly when the file path is unavailable or invalid.

### Directory Mapping

Common usage only needs 115 paths. Each source mapping has:

- `media_type`: `movie` or `tv`
- `source_path`: folder to scan
- `target_root_path`: media library root for that media type

Example:

```json
[
  {
    "name": "电影来源",
    "media_type": "movie",
    "source_path": "/待整理/Movie",
    "target_root_path": "/媒体库/Movie"
  },
  {
    "name": "电视剧来源",
    "media_type": "tv",
    "source_path": "/待整理/TV",
    "target_root_path": "/媒体库/TV"
  }
]
```

The plugin resolves target folders as:

```text
{target_root_path}/{MoviePilot分类名}
```

For example, if MoviePilot classifies a TV item as `欧美剧`, the plugin resolves `/媒体库/TV/欧美剧` and moves the file there. Keep those category folder names aligned with MoviePilot's generated media library structure.

### Naming

The plugin uses MoviePilot's current movie/TV rename templates and rename event hook when building dry-run plans. If that path is unavailable, it falls back to MoviePilot's default style, for example `剧名 (年份)/Season 1/剧名 - S01E01 - 第 1 集.mkv`.

### Plex Refresh

After a successful organize run, the plugin can refresh Plex through MoviePilot's configured media server services.

- `refresh_plex_after_execute`: enabled by default.
- `plex_mediaservers`: optional Plex server name list. Leave empty to refresh every configured and connected Plex server.

Refreshes are deduplicated by `media_type + target_category`, so one run refreshes each touched category directory once.

### Advanced Overrides

- `target_cids`: optional advanced override. Leave category CID values empty when using path-based mapping.
- `category_mapping`: optional alias map only. Use it when MoviePilot's category name needs to be mapped to a different folder name.


## Trigger From OpenClaw

OpenClaw can trigger organizing after a 115 transfer finishes by calling the plugin API:

```bash
curl -X POST \
  "http://MOVIEPILOT_HOST:3001/api/v1/plugin/P115MediaOrganizer/trigger?apikey=YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"source":"openclaw","execute":true}'
```

Behavior:

- When `dry_run=true`, the trigger only generates a plan unless `force_execute=true` is also sent.
- When `dry_run=false` and `execute=true`, the trigger generates a fresh plan and executes it.
- When `execute=false`, it only generates a fresh plan.

## Details Page

The plugin details page shows:

- p115client connection status
- source mappings
- latest dry-run plan
- execution result and errors
- recent run summaries and history details
- cleaned empty source directory count

## Safety Notes

- Defaults to dry-run.
- Empty source directory cleanup only runs under configured source roots.
- Keep real cookies, CIDs, and private 115 paths out of this public repository.
