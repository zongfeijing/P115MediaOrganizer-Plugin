# P115MediaOrganizer

MoviePilot V2/V3 plugin for organizing media files directly inside 115 cloud drive.

This plugin scans configured 115 source folders, uses MoviePilot recognition and category rules, then moves/renames files in 115 to the matching media library folders. It does not download files and does not create STRM files.

## Install In MoviePilot

Use this repository URL as a third-party plugin market/source in MoviePilot, then install `115云端媒体整理`.

```text
https://github.com/zongfeijing/P115MediaOrganizer-Plugin
```

MoviePilot V2 uses `package.v2.json` and `plugins.v2/p115mediaorganizer`. MoviePilot V3 uses `package.v3.json` and `plugins.v3/p115mediaorganizer`.

## Configuration

### 115 Connection

MoviePilot installs `p115client` from the plugin dependency manifest:

- V2: `plugins.v2/p115mediaorganizer/requirements.txt`
- V3: `plugins.v3/p115mediaorganizer/pyproject.toml`

If dependency installation fails, configure a reliable `PIP_PROXY`, then reinstall or update the plugin from MoviePilot. The V3 implementation intentionally does not run pip from plugin code.

Cookie options:

- `cookie_path`: point it to a cookie file mounted inside the MoviePilot container, for example `/config/115-cookies.txt`.
- `cookie_text`: paste a cookie directly when the file path is unavailable or invalid.

`p115client` is constructed with `check_for_relogin=True` when supported, so it can re-trigger a QR login and write the cookie back when the existing one expires.

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
- full paginated history page linked from the details page
- cleaned empty source directory count

The page is mobile-aware: on narrow screens the history / batch / config tables switch to a card list (so long filenames no longer overflow horizontally), the header actions become a 2×2 button grid, and the status line is a row of scannable chips. When the last run had failures, the 失败项 panel is pinned to the top and expanded automatically.

## Anti-Throttling

The plugin paces and retries 115 API calls to reduce the chance of being rate-limited or flagged. All settings live under the "反封锁" tab in the plugin form.

- `min_request_interval_ms` (default `300`) — minimum gap between two 115 API calls, in milliseconds. With the default this caps the plugin at roughly 3 requests per second per account.
- `max_retries` (default `3`) — retries when 115 returns a known rate-limit / busy errno (e.g. `990009`, `990019`, `40140117`) or other transient `P115OperationalError`. A `P115LoginError` (cookie expired) is **never** retried — it is surfaced immediately. Side-effecting calls (`move`, `rename`, `delete`, `mkdir`) intentionally skip retries to avoid double-executing operations whose first attempt may have already taken effect on the 115 server; only read-only APIs (`list_entries`, `resolve_path`) consume this budget. The cookie health probe is capped at 1 retry so the UI button does not block for ~10s on transient errors.
- `retry_base_seconds` (default `1.5`) — base for exponential backoff. Retries sleep for `base * 2^attempt`, jittered.
- `jitter_ratio` (default `0.3`, range `0~1`) — every sleep (throttle gap, retry backoff, batch gap) is multiplied by `uniform(1 - r, 1 + r)` so the request rhythm does not look mechanical.
- `list_page_size` (default `200`) — page size used when calling `fs_files`. The plugin pages through directories explicitly to avoid huge single responses and to make sure large directories are not silently truncated.

A `POST /api/v1/plugin/P115MediaOrganizer/cookie_check` endpoint runs a lightweight `fs_space_info` (or `fs_files` fallback) probe and updates the "Cookie" badge in the details page header. The same check is also reused (with a 30s cache) when the details page is rendered.

When the plugin cannot list a directory after all retries, it now logs a warning and skips just that subtree instead of aborting the whole dry-run.

## Batch Execution

Since v0.4.0 the plugin executes the organize plan in **batches** grouped by target parent directory. For 30 files going into the same category, the typical write API count drops from ~60 (30 `fs_rename` + 30 `fs_move`) to ~2 (one `batch_rename` + one `batch_move`), which proportionally lowers exposure to 115 rate limiting.

- `batch_size` (default `30`) — maximum number of files in a single batch. A group larger than this gets sliced into multiple batches. Previously this knob was dead code in the UI; it is now the real chunking control.
- `sleep_between_batches` (default `1.0s`) — gap between batches. **Semantic change from older versions**: this used to be sleep-per-item; now it is sleep-per-batch (a batch can be 1 to `batch_size` files). With batches typically holding 10s of items, total wait time is dramatically lower than before.
- `BATCH_RENAME_MAX = 50` (internal constant) — additional safety cap on the `batch_rename` POST body. A group of 50+ renames is split into multiple `batch_rename` calls even when `batch_size` is larger.

On any batch failure (`batch_rename`, `batch_move`, or `batch_delete`) the plugin transparently falls back to per-item calls so each item still gets its own success / failure entry in the history page. The default cookie-expired path remains: a `P115LoginError` aborts the run instead of looping per item.

The empty-source-dir cleanup at the end of `execute_last_plan` also uses `batch_delete` with the same fallback behavior.

## Safety Notes

- Defaults to dry-run.
- Empty source directory cleanup only runs under configured source roots.
- Keep real cookies, CIDs, and private 115 paths out of this public repository.
