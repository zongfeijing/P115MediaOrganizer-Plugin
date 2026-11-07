"""Plex 按目录精确刷新。

MoviePilot 的 Plex.refresh_library_by_items 只要有一个路径匹配不到 Plex 媒体库，就会改为刷新服务器上的
全部媒体库。插件拿到的是 115 网盘路径，通常与 Plex 通过挂载看到的路径不同，所以过去每次都会触发全库刷新。
这里由插件自己把 115 目录换算成 Plex 路径，只对匹配到的媒体库提交局部扫描；匹配不到时跳过并提示，
绝不退回全库刷新。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Iterable
from urllib.parse import quote_plus

MAPPING_SEPARATOR = "=>"
_WINDOWS_PREFIX = re.compile(r"^(?:[A-Za-z]:[\\/]|\\\\)")
_WINDOWS_ABSOLUTE = re.compile(r"^(?:[A-Za-z]:[\\/]|\\\\[^\\/]+[\\/][^\\/]+)")


@dataclass(frozen=True)
class PathMapping:
    """一条「115路径 => Plex路径」映射；同一 115 路径可映射到多个挂载（例如多台 Plex）。"""

    source: str
    target: str

    @property
    def source_parts(self) -> list[str]:
        return _parts(self.source)


@dataclass(frozen=True)
class PlexLibrary:
    key: str
    title: str
    locations: tuple[str, ...]


def parse_path_mappings(value: Any) -> tuple[list[PathMapping], list[str]]:
    """解析多行映射文本，返回 (映射, 错误)。空值表示只使用自动匹配。"""
    if value is None or value == "":
        return [], []
    if not isinstance(value, str):
        return [], ["Plex 路径映射必须是文本，每行一条「115路径 => Plex路径」"]
    mappings: list[PathMapping] = []
    errors: list[str] = []
    for number, raw in enumerate(value.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        label = f"Plex 路径映射第 {number} 行"
        source, separator, target = (part.strip() for part in line.partition(MAPPING_SEPARATOR))
        if not separator or not source or not target:
            errors.append(f"{label}格式应为「115路径 => Plex路径」，例如 /媒体库 => /CloudNAS/115/媒体库")
            continue
        if not source.startswith("/") or _has_dot_parts(source):
            errors.append(f"{label}的 115 路径必须以 / 开头，且不能包含 . 或 ..")
            continue
        if not (target.startswith("/") or _WINDOWS_ABSOLUTE.match(target)) or _has_dot_parts(target):
            errors.append(f"{label}的 Plex 路径必须是绝对路径，例如 /CloudNAS/115/媒体库 或 D:\\Media")
            continue
        mapping = PathMapping("/" + "/".join(_parts(source)), target)
        if mapping not in mappings:
            mappings.append(mapping)
    return mappings, errors


def refresh_folders(
    items: Iterable[dict[str, Any]],
    default_roots: dict[str, str] | None = None,
) -> list[dict[str, str]]:
    """把本次成功整理的项目归并为影片/剧集目录（115 路径），同一目录只刷新一次。"""
    default_roots = default_roots or {}
    folders: dict[str, dict[str, str]] = {}
    for item in items or []:
        media_type = str(item.get("media_type") or "").lower()
        category = str(item.get("target_category") or "").strip()
        if media_type not in ("movie", "tv") or not category:
            continue
        if str(item.get("target_path") or "").startswith("115://"):
            continue  # 未识别目录只有 CID，没有可换算的路径
        root = str(item.get("target_root_path") or default_roots.get(media_type) or "").strip()
        if not root.startswith("/"):
            continue
        path = str(PurePosixPath(root) / category / str(item.get("target_dir_name") or "").strip())
        folders.setdefault(path, {"path": path, "media_type": media_type, "category": category})
    return list(folders.values())


def load_plex_libraries(plex: Any) -> list[PlexLibrary]:
    """直接读取 /library/sections，避免宿主缓存的媒体库列表在新增媒体库后过期。"""
    container = plex.query("/library/sections")
    libraries: list[PlexLibrary] = []
    if container is None:
        return libraries
    for directory in container.iter("Directory"):
        key = str(directory.attrib.get("key") or "").strip()
        locations = tuple(
            location.attrib["path"]
            for location in directory.iter("Location")
            if location.attrib.get("path")
        )
        if key and locations:
            libraries.append(PlexLibrary(key, directory.attrib.get("title") or key, locations))
    return libraries


def refresh_endpoint(library_key: str, path: str) -> str:
    """Plex 局部扫描接口，与 plexapi LibrarySection.update(path=...) 相同。"""
    return f"/library/sections/{library_key}/refresh?path={quote_plus(path)}"


def resolve_refresh_targets(
    folder: str,
    mappings: Iterable[PathMapping],
    libraries: Iterable[PlexLibrary],
) -> tuple[list[tuple[PlexLibrary, str]], str]:
    """把 115 目录换算为 [(媒体库, Plex 路径)] 和匹配方式；空列表表示应跳过，不能退回全库刷新。"""
    libraries = list(libraries)
    folder_parts = _parts(folder)
    targets = _libraries_containing(_mapped_paths(folder_parts, list(mappings)), libraries)
    if targets:
        return targets, "路径映射"
    targets = _libraries_containing(_detected_paths(folder_parts, libraries), libraries)
    return targets, ("自动匹配" if targets else "")


def summarize_refresh(rows: Iterable[dict[str, Any]] | None) -> dict[str, int]:
    summary = {"refreshed": 0, "unmatched": 0, "failed": 0}
    for row in rows or []:
        status = row.get("status") or ("refreshed" if row.get("success") else "failed")
        if status in summary:
            summary[status] += 1
    return summary


def describe_refresh_summary(summary: dict[str, int] | None) -> str:
    summary = summary or {}
    if not any(summary.values()):
        return ""
    text = f"Plex：已刷新 {summary.get('refreshed', 0)} 个目录"
    if summary.get("unmatched"):
        text += f"，{summary['unmatched']} 个未匹配到媒体库（未刷新）"
    if summary.get("failed"):
        text += f"，{summary['failed']} 个失败"
    return text


def _mapped_paths(folder_parts: list[str], mappings: list[PathMapping]) -> list[str]:
    matched = [m for m in mappings if folder_parts[: len(m.source_parts)] == m.source_parts]
    if not matched:
        return []
    longest = max(len(m.source_parts) for m in matched)
    paths: list[str] = []
    for mapping in matched:
        if len(mapping.source_parts) == longest:
            path = _join(mapping.target, folder_parts[longest:])
            if path not in paths:
                paths.append(path)
    return paths


def _detected_paths(folder_parts: list[str], libraries: list[PlexLibrary]) -> list[str]:
    """Plex 目录末尾与 115 路径开头相同（如 /CloudNAS/115/媒体库/Movie ↔ /媒体库/Movie）时推断挂载前缀。

    重合段数最多的匹配胜出，避免偶然同名的单个目录抢先匹配。
    """
    best, paths = 0, []
    for library in libraries:
        for location in library.locations:
            windows = _is_windows(location)
            location_parts = _parts(location)
            folder_key = _comparable(folder_parts, windows)
            for start in range(len(location_parts)):
                tail = _comparable(location_parts[start:], windows)
                if folder_key[: len(tail)] != tail:
                    continue
                path = _join(location, folder_parts[len(tail):])
                if len(tail) > best:
                    best, paths = len(tail), [path]
                elif len(tail) == best and path not in paths:
                    paths.append(path)
                break
    return paths


def _libraries_containing(paths: list[str], libraries: list[PlexLibrary]) -> list[tuple[PlexLibrary, str]]:
    """返回包含各路径的媒体库；路径前缀改写为 Plex 记录的原样目录，避免大小写或分隔符差异。"""
    targets: list[tuple[PlexLibrary, str]] = []
    for path in paths:
        path_parts = _parts(path)
        for library in libraries:
            for location in library.locations:
                windows = _is_windows(location)
                location_parts = _parts(location)
                prefix = path_parts[: len(location_parts)]
                if location_parts and _comparable(prefix, windows) == _comparable(location_parts, windows):
                    target = (library, _join(location, path_parts[len(location_parts):]))
                    if target not in targets:
                        targets.append(target)
                    break
    return targets


def _is_windows(path: str) -> bool:
    return bool(_WINDOWS_PREFIX.match(path))


def _parts(path: str) -> list[str]:
    separators = r"[\\/]+" if _is_windows(path) else r"/+"
    return [part for part in re.split(separators, path) if part]


def _comparable(parts: list[str], windows: bool) -> list[str]:
    return [part.casefold() for part in parts] if windows else list(parts)


def _has_dot_parts(path: str) -> bool:
    return "\x00" in path or any(part in (".", "..") for part in _parts(path))


def _join(base: str, extra: list[str]) -> str:
    if not extra:
        return base
    separator = "\\" if _is_windows(base) and "\\" in base else "/"
    return base.rstrip("\\/") + separator + separator.join(extra)
