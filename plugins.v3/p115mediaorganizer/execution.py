from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any


TERMINAL_PLAN_STATUSES = {"executed", "skipped"}


@dataclass(frozen=True)
class PlanValidation:
    valid: bool
    message: str = ""


def executable_plan_items(plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """返回仍可执行的计划项；已成功或主动跳过的项目不会再次执行。"""
    return [
        item
        for item in plan
        if item.get("action") != "skip"
        and str(item.get("status") or "planned") not in TERMINAL_PLAN_STATUSES
    ]


def validate_plan(
    plan: list[dict[str, Any]],
    config_snapshot: dict[str, Any],
    ttl_hours: int,
    now_epoch: float | None = None,
) -> PlanValidation:
    """校验计划完整性、配置快照、计划 ID 与有效期。"""
    if not plan:
        return PlanValidation(False, "没有可执行的last_plan")

    plan_ids = {str(item.get("plan_id") or "").strip() for item in plan}
    if "" in plan_ids or len(plan_ids) != 1:
        return PlanValidation(False, "last_plan包含无效或不一致的plan_id，请重新dry-run")

    for item in plan:
        if item.get("config_snapshot") != config_snapshot:
            return PlanValidation(False, "last_plan配置快照与当前配置不一致，请重新dry-run")

    if not executable_plan_items(plan):
        return PlanValidation(False, "最近一次计划已全部执行或跳过，请重新dry-run")

    ttl_seconds = max(1, int(ttl_hours)) * 3600
    created_epochs = [_created_epoch(item) for item in plan]
    if not all(created_epochs):
        return PlanValidation(False, "last_plan缺少有效创建时间，请重新dry-run")
    now_epoch = time.time() if now_epoch is None else now_epoch
    if now_epoch - min(created_epochs) > ttl_seconds:
        return PlanValidation(False, f"last_plan已超过{max(1, int(ttl_hours))}小时，请重新dry-run")
    return PlanValidation(True)


def source_entry_matches_plan(
    item: dict[str, Any],
    *,
    current_name: str,
    current_size: int,
) -> PlanValidation:
    """确认执行前的源文件名称和大小仍与 dry-run 快照一致。"""
    expected_name = str(item.get("source_name") or "")
    if current_name != expected_name:
        return PlanValidation(False, f"源文件名称已变化：{expected_name} -> {current_name}")
    if not item.get("source_is_dir"):
        expected_size = int(item.get("source_size") or 0)
        if expected_size and current_size != expected_size:
            return PlanValidation(False, f"源文件大小已变化：{expected_size} -> {current_size}")
    return PlanValidation(True)


def _created_epoch(item: dict[str, Any]) -> float:
    value = item.get("created_at_epoch")
    try:
        if value is not None and float(value) > 0:
            return float(value)
    except (TypeError, ValueError):
        pass
    text = str(item.get("created_at") or "").strip()
    if not text:
        return 0
    try:
        return datetime.strptime(text, "%Y-%m-%d %H:%M:%S").timestamp()
    except ValueError:
        return 0


def resolve_target_cids_for_source(
    target_cids: dict[str, Any],
    source: dict[str, Any],
    resolve_path,
) -> tuple[dict[str, Any], list[str]]:
    """仅使用当前来源的目标根目录解析分类 CID。"""
    resolved = {
        "movie": dict(target_cids.get("movie", {})),
        "tv": dict(target_cids.get("tv", {})),
        "unrecognized": target_cids.get("unrecognized", ""),
    }
    errors: list[str] = []
    media_type = source.get("media_type")
    target_root_path = str(source.get("target_root_path") or "").rstrip("/")
    if media_type not in ("movie", "tv") or not target_root_path:
        return resolved, errors
    for category, configured_cid in list(resolved.get(media_type, {}).items()):
        if configured_cid:
            continue
        target_path = f"{target_root_path}/{category}"
        try:
            resolved[media_type][category] = resolve_path(target_path)
        except Exception as err:
            errors.append(f"{target_path}：{err}")
    return resolved, errors
