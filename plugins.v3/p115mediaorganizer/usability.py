"""Interactive workflow APIs. No cloud mutation occurs until a confirmed execute task."""

from __future__ import annotations

import hashlib
import json
import secrets
import threading
import time
from collections import Counter
from importlib.metadata import PackageNotFoundError, version

from fastapi import HTTPException, Request

from app import schemas

from .configuration import check_configuration, connection_mode
from .execution import executable_plan_items, validate_plan
from .task_state import TaskCancelled


class UsabilityMixin:
    @staticmethod
    def _require_admin_session(request: Request):
        # A fixed API key is not an interactive administrator's confirmation.
        from app.sdk.security import decode_access_token

        authorization = request.headers.get("Authorization", "")
        scheme, _, token = authorization.partition(" ")
        try:
            payload = (
                decode_access_token(token)
                if scheme.lower() == "bearer" and token
                else None
            )
            if not payload or not payload.super_user:
                raise ValueError("not admin")
        except Exception as error:
            raise HTTPException(
                403, "请使用管理员登录会话确认执行；API Key 不能代替手动确认"
            ) from error

    def _configuration(self, draft=None):
        config = (
            dict(self._effective_config or self.get_config() or self._default_config())
            if draft is None
            else dict(draft)
        )
        # Normalize old installations without changing their stored configuration.
        config.setdefault("cookie_mode", connection_mode(config))
        return config

    def validate_config_api(self, data: dict | None = None):
        draft = (data or {}).get("config")
        if draft is not None and not isinstance(draft, dict):
            return schemas.Response(success=False, message="配置必须是对象")
        config = self._configuration(draft)
        check = check_configuration(config)
        cron = str(config.get("cron") or "").strip()
        if cron:
            try:
                from apscheduler.triggers.cron import CronTrigger

                CronTrigger.from_crontab(cron)
            except (ValueError, TypeError):
                check.errors.append("定时表达式无效，请使用五段 CRON，例如 0 3 * * *")
        return schemas.Response(
            success=check.valid,
            message="配置检查通过" if check.valid else "请修正配置后保存",
            data={
                "valid": check.valid,
                "errors": check.errors,
                "warnings": check.warnings,
                "sources": check.sources,
            },
        )

    def _progress(self, **changes):
        state = self._task.snapshot()
        if state.get("status") in ("queued", "running", "stopping"):
            self._task.update(**changes)

    def _checkpoint(self):
        self._task.checkpoint()

    def _run_background_task(self):
        state = self._task.snapshot()
        terminal = {"status": "failed", "message": "任务未完成，请查看插件日志"}
        try:
            self._checkpoint()
            self._task.update(status="running")
            self._task_owner_thread = threading.get_ident()
            if state["kind"] == "scan":
                response = self.dry_run_all()
            elif state["kind"] == "check":
                response = self._run_exclusive("check", self._check_connections)
            else:
                expected = state.get("plan_digest")

                def execute():
                    if expected != self._plan_digest(self.get_data("last_plan") or []):
                        return schemas.Response(
                            success=False, message="排队期间计划发生变化，请重新确认"
                        )
                    return self._execute_last_plan(
                        trigger_source="manual_confirmed", allow_dry_run=True
                    )

                response = self._run_exclusive("execute_confirmed", execute)
            terminal = {
                "status": "cancelled"
                if self._task.cancel.is_set()
                else ("completed" if response.success else "failed"),
                "message": response.message or "任务已完成",
            }
        except TaskCancelled as error:
            terminal = {"status": "cancelled", "message": str(error)}
        except Exception:
            from app.sdk.logging import logger

            logger.error("【115云端媒体整理】后台任务异常，详情请查看插件日志")
            terminal = {
                "status": "failed",
                "message": "任务异常中止，请查看插件日志；已完成的项目保留",
            }
        finally:
            # Publish terminal state only after cleanup. A new submission cannot race with old-task cleanup.
            with self._operation_lock:
                self._task_owner_thread = None
                self._confirmation = None
                self._execution_plan = None
                self._task.update(**terminal, finished_at=time.time())

    def _submit_task(self, kind: str):
        if self._active_operation:
            return schemas.Response(
                success=False, message="已有任务正在运行，请等待结束"
            )
        state = None
        try:
            state = self._task.reserve(kind)
            from app.sdk import scheduler as scheduler_sdk

            added = scheduler_sdk.add_plugin_once_job(
                self._instance_id(),
                "interactive_task",
                self._run_background_task,
                "115云端媒体整理交互任务",
                delay_seconds=1,
            )
            if not added:
                raise ValueError("宿主调度器未运行，请稍后重试")
        except Exception as error:
            # A duplicate submission must not overwrite the existing task's running state.
            if state is not None:
                self._task.update(
                    status="failed", message="任务调度失败，请确认宿主调度器正在运行"
                )
            return schemas.Response(success=False, message=str(error))
        return schemas.Response(
            success=True,
            message="任务已提交，可以关闭页面，稍后回来查看进度",
            data=state,
        )

    def start_task_api(self, data: dict | None = None):
        kind = (data or {}).get("kind", "scan")
        if kind not in ("scan", "check"):
            return schemas.Response(success=False, message="执行任务需先取得确认摘要")
        validation = self.validate_config_api()
        if not validation.success:
            return validation
        if self._active_operation or self._task.snapshot().get("status") in (
            "queued",
            "running",
            "stopping",
        ):
            return schemas.Response(
                success=False, message="已有任务正在运行，请等待结束"
            )
        with self._operation_lock:
            return self._submit_task(kind)

    def stop_task_api(self):
        stopped = self._task.request_stop()
        return schemas.Response(
            success=True,
            message="已请求在安全边界停止" if stopped else "当前没有运行中的任务",
        )

    def _plan_digest(self, plan):
        return hashlib.sha256(
            json.dumps(
                {"plan": plan, "config": self._config_snapshot()},
                sort_keys=True,
                ensure_ascii=False,
            ).encode()
        ).hexdigest()

    def prepare_execute_api(self, request: Request):
        self._require_admin_session(request)
        if self._active_operation:
            return schemas.Response(success=False, message="任务运行中，请等待结束")
        with self._operation_lock:
            if self._task.snapshot().get("status") in ("queued", "running", "stopping"):
                return schemas.Response(success=False, message="任务运行中，请等待结束")
            guard = self._execute_guard(allow_dry_run=True)
            if guard:
                return guard
            plan = self.get_data("last_plan") or []
            token = secrets.token_urlsafe(32)
            self._confirmation = {
                "token": token,
                "expires_at": time.time() + 120,
                "digest": self._plan_digest(plan),
            }
            items = executable_plan_items(plan)
            return schemas.Response(
                success=True,
                data={
                    "token": token,
                    "plan_id": plan[0]["plan_id"],
                    "count": len(items),
                    "retry_count": sum(i.get("status") == "failed" for i in items),
                    "skip_count": len(plan) - len(items),
                    "expires_in": 120,
                    "delete_empty_dirs": self._delete_empty_source_dirs,
                    "scheduled_preview_only": self._dry_run,
                    "targets": sorted(
                        {
                            (
                                f"115 目录 CID {i.get('target_parent_cid')}"
                                if i.get("target_path", "").startswith("115://")
                                else i.get("target_root_path")
                                or i.get("target_path", "")
                            )
                            for i in items
                        }
                    ),
                },
            )

    def confirm_execute_api(self, request: Request, data: dict | None = None):
        self._require_admin_session(request)
        if self._active_operation:
            return schemas.Response(success=False, message="任务运行中，请等待结束")
        with self._operation_lock:
            receipt = self._confirmation
            token = str((data or {}).get("token") or "")
            plan = self.get_data("last_plan") or []
            if (
                not receipt
                or not token
                or not secrets.compare_digest(token, receipt["token"])
                or receipt["expires_at"] < time.time()
                or receipt["digest"] != self._plan_digest(plan)
            ):
                return schemas.Response(
                    success=False, message="执行确认已失效或计划已变化，请重新确认"
                )
            guard = self._execute_guard(allow_dry_run=True)
            if guard:
                return guard
            self._confirmation = None  # one-use, never persist a confirmation token
            response = self._submit_task("execute")
            if response.success:
                self._task.update(plan_digest=receipt["digest"])
            return response

    def _instance_id(self):
        # The host gives clone instances distinct class names, matching SDK get_config()/save_data().
        return self.__class__.__name__

    def _check_connections(self):
        p115 = self._p115_ops()
        health = p115.health_check(force=True)
        self.save_data("connection_health", health)
        paths = []
        check = check_configuration(self._configuration())
        if health.get("ok"):
            for row in check.sources:
                for key in ("source_path", "target_root_path"):
                    self._checkpoint()
                    path = row[key]
                    self._progress(phase="checking", message=f"检查目录：{path}")
                    try:
                        cid = p115.resolve_path(path)
                        paths.append({"path": path, "ok": True, "cid": cid})
                    except Exception:
                        paths.append(
                            {
                                "path": path,
                                "ok": False,
                                "message": "目录无法访问，请检查路径、网络与账号权限",
                            }
                        )
        self.save_data("path_checks", paths)
        valid = bool(
            check.valid and health.get("ok", False) and all(p["ok"] for p in paths)
        )
        return schemas.Response(
            success=valid,
            message="连接与目录检查通过"
            if valid
            else "检查未通过，请查看连接状态和目录提示",
        )

    def workflow_status_api(self):
        plan = self.get_data("last_plan") or []
        check = check_configuration(self._configuration())
        config_validation = self.validate_config_api()
        check.errors = list(config_validation.data.get("errors", check.errors))
        validation = validate_plan(plan, self._config_snapshot(), self._plan_ttl_hours)
        health = self.get_data("connection_health") or {
            "kind": "unknown",
            "message": "尚未检查连接",
            "ok": None,
        }
        connection_blocked = health.get("kind") in ("login", "dependency")
        try:
            versions = {n: version(n) for n in ("p115client", "python-concurrenttools")}
        except PackageNotFoundError:
            versions = {}
        task = self._task.snapshot()
        task.pop("plan_digest", None)
        if self._active_operation and task.get("status") == "idle":
            task.update(status="running", message="后台任务正在运行")
        return schemas.Response(
            success=True,
            data={
                "task": task,
                "busy": task.get("status") in ("queued", "running", "stopping")
                or bool(self._active_operation),
                "configuration": {
                    "valid": check.valid,
                    "errors": check.errors,
                    "sources": check.sources,
                    "cookie_mode": connection_mode(self._configuration()),
                    "preview_only": self._dry_run,
                },
                "connection": health,
                "path_checks": self.get_data("path_checks") or [],
                "versions": versions,
                "plan": {
                    "count": len(plan),
                    "executable": len(executable_plan_items(plan)),
                    "valid": validation.valid
                    and check.valid
                    and not connection_blocked,
                    "reason": "请先修复连接并重新检查"
                    if connection_blocked
                    else validation.message,
                    "created_at": plan[0].get("created_at") if plan else None,
                    "expires_at": min(
                        (float(i.get("created_at_epoch") or 0) for i in plan), default=0
                    )
                    + self._plan_ttl_hours * 3600,
                    "counts": dict(Counter(i.get("status") for i in plan)),
                },
                "scan_summary": self.get_data("scan_summary") or {},
                "last_result": {
                    k: v
                    for k, v in (self.get_data("last_result") or {}).items()
                    if k
                    in (
                        "run_id",
                        "success",
                        "failed",
                        "skipped",
                        "remaining",
                        "cancelled",
                        "started_at",
                        "finished_at",
                    )
                },
            },
        )

    def records_api(
        self,
        page: int = 1,
        page_size: int = 20,
        kind: str = "plan",
        status: str = "",
        query: str = "",
        run_id: str = "",
    ):
        if kind not in ("plan", "history", "runs", "scan"):
            return schemas.Response(success=False, message="未知记录类型")
        key = {
            "plan": "last_plan",
            "history": "history",
            "runs": "runs",
            "scan": "scan_records",
        }[kind]
        rows = list(self.get_data(key) or [])
        if kind in ("history", "runs"):
            rows.reverse()
        if kind == "runs":
            rows = [
                {
                    **r,
                    "status": "cancelled"
                    if r.get("cancelled")
                    else ("failed" if r.get("failed") else "executed"),
                }
                for r in rows
            ]
        if status:
            rows = [r for r in rows if r.get("status") == status]
        if run_id:
            rows = [r for r in rows if r.get("run_id") == run_id]
        query = query.strip().lower()[:200]
        fields = (
            "source_name",
            "target_name",
            "target_path",
            "path_hint",
            "reason",
            "warnings",
            "error",
            "run_id",
            "title",
        )
        if query:
            rows = [
                r
                for r in rows
                if query in " ".join(str(r.get(k, "")) for k in fields).lower()
            ]
        items, meta = self._paginate(rows, max(1, page), min(100, max(1, page_size)))
        # config_snapshot contains no cookies, but the interactive list doesn't need it or internal IDs.
        safe_fields = set(fields) | {
            "status",
            "media_type",
            "year",
            "season",
            "episode",
            "media_source",
            "media_id",
            "time",
            "created_at",
            "target_category",
            "source_size",
            "total",
            "success",
            "failed",
            "skipped",
        }
        return schemas.Response(
            success=True,
            data={
                "items": [
                    {k: v for k, v in i.items() if k in safe_fields} for i in items
                ],
                "pagination": meta,
            },
        )
