"""Strict configuration parsing shared by the JSON fallback and Vue editor."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any

from .execution import source_contains_target


@dataclass
class ConfigurationCheck:
    sources: list[dict[str, str]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors


def parse_json(value: Any, expected: type, label: str):
    if isinstance(value, expected):
        return value
    try:
        parsed = json.loads(value or ("[]" if expected is list else "{}"))
    except (ValueError, TypeError) as error:
        raise ValueError(f"{label}不是有效 JSON：{error}") from error
    if not isinstance(parsed, expected):
        raise ValueError(f"{label}必须是{'数组' if expected is list else '对象'}")
    return parsed


def normalize_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip().startswith("/"):
        raise ValueError(f"{label}必须是以 / 开头的 115 完整路径")
    path = value.strip()
    if any(part in (".", "..") for part in path.split("/")) or "\x00" in path:
        raise ValueError(f"{label}不能包含 .、.. 或空字符")
    return "/" + str(PurePosixPath(path)).lstrip("/")


def check_configuration(config: dict[str, Any]) -> ConfigurationCheck:
    result = ConfigurationCheck()
    try:
        rows = parse_json(config.get("source_mappings"), list, "来源映射")
    except ValueError as error:
        result.errors.append(str(error))
        rows = []
    if not rows and not result.errors:
        result.errors.append("尚未配置来源，请添加至少一个来源目录和目标媒体库目录")
    seen = set()
    for index, row in enumerate(rows, 1):
        label = f"第 {index} 个来源"
        try:
            if not isinstance(row, dict):
                raise ValueError(f"{label}必须是对象")
            media_type = str(row.get("media_type") or "").strip().lower()
            if media_type not in ("movie", "tv"):
                raise ValueError(f"{label}的类型必须是电影或电视剧")
            source = normalize_path(row.get("source_path"), f"{label}的来源目录")
            target = normalize_path(row.get("target_root_path"), f"{label}的目标目录")
            if source == "/":
                raise ValueError(f"{label}不能扫描网盘根目录，请选择专用待整理目录")
            if source in seen:
                raise ValueError(f"{label}的来源目录重复：{source}")
            seen.add(source)
            result.sources.append(
                {
                    "name": str(row.get("name") or source).strip(),
                    "media_type": media_type,
                    "source_path": source,
                    "target_root_path": target,
                }
            )
        except ValueError as error:
            result.errors.append(str(error))
    # Protect every scan tree, not only the row that owns a destination.
    for row in result.sources:
        for other in result.sources:
            if source_contains_target(other["source_path"], row["target_root_path"]):
                result.errors.append(
                    f"目标目录不能位于任何来源目录内：{other['source_path']} → {row['target_root_path']}"
                )
    for index, row in enumerate(result.sources):
        for other in result.sources[index + 1 :]:
            if source_contains_target(
                row["source_path"], other["source_path"]
            ) or source_contains_target(other["source_path"], row["source_path"]):
                result.errors.append(
                    f"来源目录不能互相包含，避免重复扫描：{row['source_path']}、{other['source_path']}"
                )
    mode = connection_mode(config)
    if mode == "text" and not str(config.get("cookie_text") or "").strip():
        result.errors.append("请填写 Cookie 文本，或切换为 Cookie 文件方式")
    if (
        mode == "file"
        and "cookie_path" in config
        and not str(config.get("cookie_path") or "").strip()
    ):
        result.errors.append("请填写容器内 Cookie 文件路径")
    for field_name, label in (
        ("category_mapping", "分类别名映射"),
        ("target_cids", "目标 CID"),
    ):
        try:
            parsed = parse_json(config.get(field_name), dict, label)
            if any(
                not isinstance(parsed.get(key, {}), dict) for key in ("movie", "tv")
            ):
                raise ValueError(f"{label}的 movie、tv 字段必须是对象")
            if any(
                not isinstance(v, (str, int))
                for key in ("movie", "tv")
                for v in parsed.get(key, {}).values()
            ):
                raise ValueError(f"{label}的分类值必须是文本或数字")
        except ValueError as error:
            result.errors.append(str(error))
    for key, allowed in (
        ("conflict_strategy", ("skip", "rename_with_suffix")),
        ("unrecognized_action", ("skip", "move_to_unrecognized")),
    ):
        if key in config and config[key] not in allowed:
            result.errors.append(f"{key}包含不支持的选项")
    if config.get("unrecognized_action") == "move_to_unrecognized":
        try:
            if not str(
                parse_json(config.get("target_cids"), dict, "目标 CID").get(
                    "unrecognized"
                )
                or ""
            ).strip():
                result.errors.append("选择移动未识别文件时，请先配置未识别目录 CID")
        except ValueError:
            pass
    ranges = {
        "max_depth": (0, 30),
        "max_items_per_run": (0, 10000),
        "min_file_size_mb": (0, 1000000),
        "batch_size": (1, 100),
        "sleep_between_batches": (0, 120),
        "plan_ttl_hours": (1, 720),
        "min_request_interval_ms": (0, 60000),
        "max_retries": (0, 10),
        "retry_base_seconds": (0.1, 120),
        "jitter_ratio": (0, 1),
        "list_page_size": (50, 1000),
    }
    for key, (low, high) in ranges.items():
        if key not in config:
            continue
        try:
            value = float(config[key])
            if not low <= value <= high:
                raise ValueError()
            if (
                key
                not in ("sleep_between_batches", "retry_base_seconds", "jitter_ratio")
                and not value.is_integer()
            ):
                raise ValueError()
        except (TypeError, ValueError):
            result.errors.append(f"{key}应为 {low}～{high} 之间的数字")
    return result


def connection_mode(config: dict[str, Any]) -> str:
    # Preserve legacy text-first behavior until the user makes an explicit choice.
    mode = config.get("cookie_mode")
    return (
        mode
        if mode in ("text", "file")
        else ("text" if config.get("cookie_text") else "file")
    )
