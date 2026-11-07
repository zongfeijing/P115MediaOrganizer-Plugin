"""Run reports: files that need a person's attention, and the organize notification text."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List, Optional

# Skips that are expected and need no action: already organized, or ignored by configuration.
ROUTINE_SKIP_MARKERS = ("此前已成功整理",)
ATTENTION_LIMIT = 200
NOTIFY_TITLE_LIMIT = 8


def attention_items(plan: Iterable[Dict[str, Any]], existing: Optional[List[Dict[str, Any]]] = None,
                    complete_scan: bool = True, limit: int = ATTENTION_LIMIT) -> List[Dict[str, Any]]:
    """Merge this plan's problem files into the persisted follow-up list.

    An entry is dropped only when the problem is known to be gone: the file was organized, or a
    complete scan no longer finds it (moved, renamed or deleted). Problems found only at execution
    time (target already exists, failures, held files) therefore stay listed across later preview
    scans, where the same file looks fine until it is tried again. A new reason replaces the old.
    """
    previous = {row.get("key"): row for row in existing or [] if row.get("key")}
    seen: Dict[str, Dict[str, Any]] = {}
    for item in plan or []:
        key = str(item.get("item_id") or item.get("source_fid") or item.get("source_name") or "")
        if key:
            seen[key] = item
    merged: Dict[str, Dict[str, Any]] = {}
    for key, row in previous.items():
        item = seen.get(key)
        if item is None:
            if not complete_scan:
                merged[key] = row
        elif item.get("status") != "executed":
            merged[key] = row
    for key, item in seen.items():
        reason = attention_reason(item)
        if not reason:
            continue
        held = bool(item.get("held_reason")) and item.get("status") == "planned"
        merged[key] = {
            "key": key,
            "source_name": item.get("source_name") or "",
            "path_hint": item.get("path_hint") or "",
            "media_type": item.get("media_type") or "",
            "title": item.get("title") or "",
            "year": item.get("year") or "",
            "status": "held" if held else item.get("status") or "",
            "reason": reason,
            "target_path": item.get("target_path") or "",
            "first_seen": previous.get(key, {}).get("first_seen") or "",
        }
    return list(merged.values())[-limit:]


def attention_reason(item: Dict[str, Any]) -> str:
    """Why a person should look at this file, or "" if nothing needs doing."""
    status = item.get("status") or ""
    warnings = [w for w in item.get("warnings") or [] if w]
    error = item.get("error") or ""
    if status == "failed":
        return error or "执行失败"
    if status == "planned" and item.get("held_reason"):
        return f"已保留待确认：{item['held_reason']}"
    if status == "skipped" or item.get("action") == "skip":
        text = error or "；".join(warnings) or "已跳过"
        return "" if any(marker in text for marker in ROUTINE_SKIP_MARKERS) else text
    return ""


def stamp_first_seen(rows: List[Dict[str, Any]], now: str) -> List[Dict[str, Any]]:
    return [{**row, "first_seen": row.get("first_seen") or now} for row in rows]


def organize_titles(items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Group organized files by title for the notification: one line per movie / show season."""
    groups: Dict[tuple, Dict[str, Any]] = {}
    for item in items or []:
        title = item.get("title") or item.get("target_name") or item.get("source_name") or ""
        year = item.get("year") or ""
        key = (item.get("media_type"), title, year, item.get("target_category"))
        group = groups.setdefault(key, {
            "media_type": item.get("media_type") or "",
            "title": title,
            "year": year,
            "category": item.get("target_category") or "",
            "count": 0,
            "episodes": [],
            "image": "",
        })
        group["count"] += 1
        if item.get("episode"):
            group["episodes"].append((item.get("season") or 1, item.get("episode")))
        group["image"] = group["image"] or item.get("image") or ""
    return list(groups.values())


def format_episodes(episodes: List[tuple]) -> str:
    """[(1,1),(1,2),(1,3),(1,5)] -> 'S01E01-E03、E05'"""
    if not episodes:
        return ""
    parts = []
    for season in sorted({s for s, _ in episodes}):
        numbers = sorted({e for s, e in episodes if s == season})
        ranges, start, prev = [], numbers[0], numbers[0]
        for n in numbers[1:] + [None]:
            if n is not None and n == prev + 1:
                prev = n
                continue
            ranges.append(f"E{start:02d}" if start == prev else f"E{start:02d}-E{prev:02d}")
            if n is not None:
                start = prev = n
        parts.append(f"S{season:02d}" + "、".join(ranges))
    return " ".join(parts)


def attention_message(new_rows: List[Dict[str, Any]], total: int) -> Dict[str, str]:
    """Notification for files that newly need attention when nothing was organized."""
    lines = [f"· {row.get('source_name')}：{row.get('reason')}" for row in new_rows[:5]]
    if len(new_rows) > 5:
        lines.append(f"· 另有 {len(new_rows) - 5} 个")
    if total > len(new_rows):
        lines.append(f"需处理列表共 {total} 个")
    lines.append("请在插件详情页「需处理」中查看。")
    return {"title": f"115 整理：{len(new_rows)} 个文件需处理", "text": "\n".join(lines)}


def organize_message(result: Dict[str, Any], success_items: List[Dict[str, Any]],
                     attention: List[Dict[str, Any]], plex_text: str = "") -> Dict[str, str]:
    """Build the run notification: title, text and an image from the first organized title."""
    titles = organize_titles(success_items)
    cancelled = bool(result.get("cancelled"))
    success, failed, skipped = result.get("success", 0), result.get("failed", 0), result.get("skipped", 0)
    held = result.get("held", 0)
    if cancelled:
        title = f"115 整理已停止：完成 {success} 个文件"
    elif titles:
        head = titles[0]
        name = f"{head['title']} ({head['year']})" if head["year"] else head["title"]
        title = f"115 整理入库：{name}" + (f" 等 {len(titles)} 部" if len(titles) > 1 else "")
    else:
        title = "115 整理完成：没有新入库"
    lines = []
    for group in titles[:NOTIFY_TITLE_LIMIT]:
        name = f"{group['title']} ({group['year']})" if group["year"] else group["title"]
        detail = format_episodes(group["episodes"]) or (f"{group['count']} 个文件" if group["count"] > 1 else "")
        lines.append("· " + " ".join(p for p in (name, detail, f"→ {group['category']}" if group["category"] else "") if p))
    if len(titles) > NOTIFY_TITLE_LIMIT:
        lines.append(f"· 另有 {len(titles) - NOTIFY_TITLE_LIMIT} 部")
    counts = f"成功 {success}，失败 {failed}，跳过 {skipped}"
    if held:
        counts += f"，保留待确认 {held}"
    lines.append(counts)
    reasons = Counter(row.get("reason") for row in attention if row.get("reason"))
    if reasons:
        top = "；".join(f"{reason}（{n}）" if n > 1 else reason for reason, n in reasons.most_common(3))
        lines.append(f"需处理 {sum(reasons.values())} 个：{top}")
    for error in (result.get("errors") or [])[:3]:
        lines.append(f"失败：{error.get('source')}：{error.get('error')}")
    if result.get("deleted_subtitles"):
        lines.append(f"已删除来源字幕 {len(result['deleted_subtitles'])} 个")
    if plex_text:
        lines.append(plex_text)
    image = next((group["image"] for group in titles if group["image"]), "")
    return {"title": title, "text": "\n".join(lines), "image": image}
