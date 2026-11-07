import json
import random
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from apscheduler.triggers.cron import CronTrigger

from app import schemas
from app.sdk.services import MediaServerHelper
from app.sdk.logging import logger
from app.sdk.plugin import _PluginBase
from app.schemas.types import MessageType

from .api_models import ListDirectoryRequest, ResolvePathRequest, TriggerRequest
from .category_mapper import DEFAULT_CATEGORY_MAPPING, CategoryMapper
from .execution import (
    AUTO_EXECUTE_POLICIES,
    auto_execute_hold_reason,
    executable_plan_items,
    resolve_target_cids_for_source,
    source_contains_target,
    source_entry_matches_plan,
    validate_plan,
)
from .configuration import check_configuration, connection_mode
from .task_state import TaskCancelled, TaskState
from .usability import UsabilityMixin
from .models import ExecuteResult
from .p115_ops import ANTI_BLOCK_DEFAULTS, BATCH_RENAME_MAX, SUBTITLE_EXTENSIONS, P115Ops, P115UnavailableError
from .planner import Planner, compute_batch_group_key
from .reporting import attention_items, attention_message, organize_message, stamp_first_seen
from .plex_refresh import (
    describe_refresh_summary,
    load_plex_libraries,
    parse_path_mappings,
    refresh_endpoint,
    refresh_folders,
    resolve_refresh_targets,
    summarize_refresh,
)


DEFAULT_SOURCE_MAPPINGS = [
    {
        "name": "电影来源",
        "media_type": "movie",
        "source_path": "/待整理/Movie",
        "target_root_path": "/媒体库/Movie",
    },
    {
        "name": "电视剧来源",
        "media_type": "tv",
        "source_path": "/待整理/TV",
        "target_root_path": "/媒体库/TV",
    },
]

DEFAULT_TARGET_CIDS = {
    "movie": {
        "动画电影": "",
        "外语电影": "",
        "华语电影": "",
    },
    "tv": {
        "未分类": "",
        "综艺": "",
        "日韩剧": "",
        "欧美剧": "",
        "国产剧": "",
    },
    "unrecognized": "",
}


class P115MediaOrganizer(UsabilityMixin, _PluginBase):
    plugin_name = "115云端媒体整理"
    plugin_desc = "将115最近接收中的媒体云端整理到媒体库。"
    plugin_icon = "clouddisk.png"
    plugin_version = "1.4.0"
    plugin_author = "Zongfei"
    author_url = "https://github.com/zongfeijing"
    plugin_config_prefix = "p115mediaorganizer_"
    plugin_order = 50
    auth_level = 2

    _enabled = False
    _notify = True
    _onlyonce = False
    _cron = ""
    _dry_run = True
    _delete_empty_source_dirs = True
    _refresh_plex_after_execute = True
    _allow_external_execute = False
    _auto_execute_policy = "confident"
    _plex_mediaservers = []
    _plex_path_mappings = ""
    _max_depth = 5
    _max_items_per_run = 200
    _min_file_size_mb = 100
    _batch_size = 30
    _sleep_between_batches = 1.0
    _conflict_strategy = "skip"
    _unrecognized_action = "skip"
    _exclude_keywords = "sample,trailer,花絮,预告"
    _cookie_path = "/config/115-cookies.txt"
    _cookie_text = ""
    _source_mappings = "[]"
    _category_mapping = json.dumps(DEFAULT_CATEGORY_MAPPING, ensure_ascii=False, indent=2)
    _target_cids = json.dumps(DEFAULT_TARGET_CIDS, ensure_ascii=False, indent=2)
    _min_request_interval_ms = ANTI_BLOCK_DEFAULTS["min_request_interval_ms"]
    _max_retries = ANTI_BLOCK_DEFAULTS["max_retries"]
    _retry_base_seconds = ANTI_BLOCK_DEFAULTS["retry_base_seconds"]
    _jitter_ratio = ANTI_BLOCK_DEFAULTS["jitter_ratio"]
    _list_page_size = ANTI_BLOCK_DEFAULTS["list_page_size"]
    _history_limit = 1000
    _run_limit = 100
    _history_page = 1
    _history_page_size = 50
    _plan_ttl_hours = 24
    _run_page = 1
    _run_page_size = 10
    _ops_instance = None

    def __init__(self):
        super().__init__()
        self._ops_instance = None
        self._operation_lock = threading.RLock()
        self._operation_depth = 0
        self._active_operation = ""
        self._task = TaskState()
        self._confirmation = None
        self._task_owner_thread = None
        self._scan_records = []
        self._scan_record_counts = {}
        self._scan_plan_id = ""
        self._cookie_mode = "file"
        self._effective_config = {}

    def init_plugin(self, config: dict = None):
        if self._active_operation:
            raise ValueError("任务运行中，请等待完成或停止后再修改配置")
        with self._operation_lock:
            if self._task.snapshot().get("status") in ("queued", "running", "stopping"):
                raise ValueError("任务运行中，停止或等待任务完成后再修改配置")
            return self._init_plugin(config)

    def _init_plugin(self, config: dict = None):
        self._stop_service()
        self._ops_instance = None  # 配置可能变了，重置缓存的 P115Ops 单例
        config = dict(config or {})
        self._effective_config = config
        self._confirmation = None
        self._task.cancel.clear()
        self.save_data("connection_health", {"ok": None, "kind": "unknown", "message": "配置已更新，请重新检查连接"})
        self.save_data("path_checks", [])
        self._enabled = self._safe_bool(config.get("enabled"), False)
        self._notify = self._safe_bool(config.get("notify"), True)
        self._onlyonce = self._safe_bool(config.get("onlyonce"), False)
        self._cron = str(config.get("cron") or "").strip()
        self._dry_run = self._safe_bool(config.get("dry_run"), True)
        self._delete_empty_source_dirs = self._safe_bool(config.get("delete_empty_source_dirs"), True)
        self._refresh_plex_after_execute = self._safe_bool(config.get("refresh_plex_after_execute"), True)
        self._allow_external_execute = self._safe_bool(config.get("allow_external_execute"), False)
        policy = str(config.get("auto_execute_policy") or "confident")
        self._auto_execute_policy = policy if policy in AUTO_EXECUTE_POLICIES else "confident"
        self._plex_mediaservers = config.get("plex_mediaservers") or []
        self._plex_path_mappings = str(config.get("plex_path_mappings") or "")
        self._max_depth = self._safe_int(config.get("max_depth"), 5)
        self._max_items_per_run = self._safe_int(config.get("max_items_per_run"), 200)
        self._min_file_size_mb = self._safe_int(config.get("min_file_size_mb"), 100)
        self._batch_size = self._safe_int(config.get("batch_size"), 30)
        self._sleep_between_batches = self._safe_float(config.get("sleep_between_batches"), 1.0)
        self._conflict_strategy = str(config.get("conflict_strategy") or "skip")
        self._unrecognized_action = str(config.get("unrecognized_action") or "skip")
        self._exclude_keywords = str(config.get("exclude_keywords") or "")
        self._cookie_path = str(config.get("cookie_path") or "/config/115-cookies.txt")
        self._cookie_text = str(config.get("cookie_text") or "")
        self._cookie_mode = connection_mode(config)
        self._source_mappings = config.get("source_mappings", "[]")
        self._category_mapping = config.get("category_mapping", json.dumps(DEFAULT_CATEGORY_MAPPING, ensure_ascii=False))
        if isinstance(self._category_mapping, dict):
            self._category_mapping = json.dumps(self._category_mapping, ensure_ascii=False)
        self._target_cids = config.get("target_cids", json.dumps(DEFAULT_TARGET_CIDS, ensure_ascii=False))
        if isinstance(self._target_cids, dict):
            self._target_cids = json.dumps(self._target_cids, ensure_ascii=False)
        self._min_request_interval_ms = max(0, self._safe_int(config.get("min_request_interval_ms"), ANTI_BLOCK_DEFAULTS["min_request_interval_ms"]))
        self._max_retries = max(0, self._safe_int(config.get("max_retries"), ANTI_BLOCK_DEFAULTS["max_retries"]))
        self._retry_base_seconds = max(0.1, self._safe_float(config.get("retry_base_seconds"), ANTI_BLOCK_DEFAULTS["retry_base_seconds"]))
        self._jitter_ratio = max(0.0, min(1.0, self._safe_float(config.get("jitter_ratio"), ANTI_BLOCK_DEFAULTS["jitter_ratio"])))
        self._list_page_size = max(50, self._safe_int(config.get("list_page_size"), ANTI_BLOCK_DEFAULTS["list_page_size"]))
        self._history_limit = self._safe_int(config.get("history_limit"), 1000)
        self._run_limit = self._safe_int(config.get("run_limit"), 100)
        self._history_page = max(1, self._safe_int(config.get("history_page"), 1))
        self._history_page_size = self._clamp_int(config.get("history_page_size"), 50, 10, 200)
        self._plan_ttl_hours = self._clamp_int(config.get("plan_ttl_hours"), 24, 1, 720)
        self._run_page = max(1, self._safe_int(config.get("run_page"), 1))
        self._run_page_size = self._clamp_int(config.get("run_page_size"), 10, 5, 100)
        logger.info(
            f"【115云端媒体整理】插件初始化：enabled={self._enabled}，dry_run={self._dry_run}，"
            f"onlyonce={self._onlyonce}，cron={self._cron or '未设置'}，来源映射={len(self._source_mapping_list())} 个"
        )

        # 升级路径：把已存档的旧 config 里缺失的反封锁字段回填默认值，
        # 让用户打开表单时能看到当前生效的默认值而不是空白
        missing = [k for k in ANTI_BLOCK_DEFAULTS if k not in config]
        if missing:
            for key in missing:
                config[key] = ANTI_BLOCK_DEFAULTS[key]
            logger.info(f"【115云端媒体整理】已为旧配置回填反封锁默认值：{missing}")
            self.update_config(config=config)

        if self._onlyonce:
            validation = self.validate_config_api()
            if validation.success:
                from app.sdk import scheduler as scheduler_sdk
                scheduled = scheduler_sdk.add_plugin_once_job(
                    self._instance_id(), "auto_once", self.auto_run,
                    "115云端媒体整理立即运行", delay_seconds=3)
                if not scheduled:
                    logger.warning("【115云端媒体整理】宿主调度器未运行，未安排立即运行")
            else:
                logger.warning("【115云端媒体整理】配置检查未通过，未安排立即运行")
            self._onlyonce = False
            config["onlyonce"] = False
            self.update_config(config=config)

    def get_state(self) -> bool:
        return bool(self._enabled)

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        return []

    @staticmethod
    def get_render_mode() -> Tuple[str, str]:
        return "vue", "dist/assets"

    def get_api(self) -> List[Dict[str, Any]]:
        response_model = schemas.Response
        return [
            {"path": "/workflow", "endpoint": self.workflow_status_api, "methods": ["GET"], "auth": "bear", "response_model": response_model},
            {"path": "/validate_config", "endpoint": self.validate_config_api, "methods": ["POST"], "auth": "bear", "response_model": response_model},
            {"path": "/tasks/start", "endpoint": self.start_task_api, "methods": ["POST"], "auth": "bear", "response_model": response_model},
            {"path": "/tasks/stop", "endpoint": self.stop_task_api, "methods": ["POST"], "auth": "bear", "response_model": response_model},
            {"path": "/execute/prepare", "endpoint": self.prepare_execute_api, "methods": ["POST"], "auth": "bear", "response_model": response_model},
            {"path": "/execute/confirm", "endpoint": self.confirm_execute_api, "methods": ["POST"], "auth": "bear", "response_model": response_model},
            {"path": "/records", "endpoint": self.records_api, "methods": ["GET"], "auth": "bear", "response_model": response_model},
            {"path": "/dry_run_movie", "endpoint": self.dry_run_movie, "methods": ["POST"], "auth": "bear", "response_model": response_model, "summary": "生成电影整理计划"},
            {"path": "/dry_run_tv", "endpoint": self.dry_run_tv, "methods": ["POST"], "auth": "bear", "response_model": response_model, "summary": "生成电视剧整理计划"},
            {"path": "/dry_run_all", "endpoint": self.dry_run_all, "methods": ["POST"], "auth": "bear", "response_model": response_model, "summary": "生成全部整理计划"},
            {"path": "/trigger", "endpoint": self.trigger_api, "methods": ["POST"], "auth": "apikey", "response_model": response_model, "summary": "外部触发整理"},
            {"path": "/execute_last_plan", "endpoint": self.execute_last_plan, "methods": ["POST"], "auth": "bear", "response_model": response_model, "summary": "执行最近一次整理计划"},
            {"path": "/history", "endpoint": self.history, "methods": ["GET"], "auth": "bear", "response_model": response_model, "summary": "查询整理历史"},
            {"path": "/clear_history", "endpoint": self.clear_history, "methods": ["POST"], "auth": "bear", "response_model": response_model, "summary": "清空整理历史"},
            {"path": "/resolve_path", "endpoint": self.resolve_path_api, "methods": ["POST"], "auth": "bear", "response_model": response_model, "summary": "解析115路径"},
            {"path": "/list_dir", "endpoint": self.list_dir_api, "methods": ["POST"], "auth": "bear", "response_model": response_model, "summary": "列出115目录"},
            {"path": "/cookie_check", "endpoint": self.cookie_check_api, "methods": ["POST", "GET"], "auth": "bear", "response_model": response_model, "summary": "检查115 Cookie健康状态"},
        ]

    def get_service(self) -> List[Dict[str, Any]]:
        if not self.get_state() or not self._cron or not self.validate_config_api().success:
            return []
        return [{
            "id": f"{self.__class__.__name__}.AutoRun",
            "name": "115云端媒体整理",
            "trigger": CronTrigger.from_crontab(self._cron),
            "func": self.auto_run,
            "kwargs": {},
        }]

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        # Vue 模式：宿主只读取默认配置，配置界面由 dist 中的 Config 组件渲染。
        return [], {**self._default_config(), "cookie_mode": self._cookie_mode}

    def get_page(self) -> List[dict]:
        # Vue 模式：详情页由 dist 中的 Page 组件渲染。
        return []

    def _run_exclusive(self, operation: str, callback):
        """One task per instance; nested automatic calls share the outer task."""
        state = self._task.snapshot()
        if state.get("status") in ("queued", "running", "stopping") and self._task_owner_thread != threading.get_ident():
            return schemas.Response(success=False, message="后台任务运行中，请等待结束或停止任务")
        if not self._operation_lock.acquire(blocking=False):
            return schemas.Response(success=False, message="已有任务正在运行，请稍后重试")
        outermost = self._operation_depth == 0
        owns_task = outermost and self._task_owner_thread != threading.get_ident()
        terminal = {"status": "failed", "message": "任务中止，请查看插件日志"}
        self._operation_depth += 1
        if outermost:
            self._active_operation = operation
        try:
            if owns_task:
                self._task.reserve(operation)
                self._task.update(status="running", message="任务正在运行")
                self._task_owner_thread = threading.get_ident()
            response = callback()
            terminal = {"status": "cancelled" if self._task.cancel.is_set() else ("completed" if response.success else "failed"),
                        "message": response.message}
            return response
        except TaskCancelled as error:
            terminal = {"status": "cancelled", "message": str(error)}
            if owns_task:
                return schemas.Response(success=False, message=str(error))
            raise
        finally:
            try:
                if self._ops_instance is not None and hasattr(self._ops_instance, "cached_health"):
                    self.save_data("connection_health", self._ops_instance.cached_health())
            except Exception:
                logger.warning("【115云端媒体整理】连接状态缓存保存失败，任务状态仍会正常释放")
            self._operation_depth -= 1
            if outermost:
                self._execution_plan = None
                self._active_operation = ""
            if owns_task:
                self._task_owner_thread = None
                self._task.update(**terminal, finished_at=time.time())
            self._operation_lock.release()

    def stop_service(self):
        self._task.request_stop()
        with self._operation_lock:
            return self._stop_service()

    def _stop_service(self):
        from app.sdk import scheduler as scheduler_sdk
        scheduler_sdk.remove_plugin_once_job(self._instance_id(), "interactive_task")
        scheduler_sdk.remove_plugin_once_job(self._instance_id(), "auto_once")
        if self._task.snapshot().get("status") in ("queued", "stopping") and not self._active_operation:
            self._task.update(status="cancelled", message="任务已取消", finished_at=time.time())
        self._confirmation = None

    def dry_run_movie(self):
        return self._run_exclusive("dry_run_movie", lambda: self._dry_run_for("movie"))

    def dry_run_tv(self):
        return self._run_exclusive("dry_run_tv", lambda: self._dry_run_for("tv"))

    def dry_run_all(self):
        return self._run_exclusive("dry_run_all", self._dry_run_all)

    def _dry_run_all(self):
        return self._generate_plan()

    def _generate_plan(self, media_type=None, save=True):
        validation = self.validate_config_api()
        if not validation.success:
            return validation
        sources = [s for s in self._source_mapping_list() if media_type is None or s["media_type"] == media_type]
        self._confirmation = None
        self._scan_plan_id = uuid4().hex
        self._scan_records = []
        self._scan_record_counts = {}
        # An old executable plan must not survive a failed or cancelled replacement scan.
        if save:
            self.save_data("last_plan", [])
        self.save_data("scan_summary", {})
        self.save_data("scan_records", [])
        plan = []
        remaining = self._max_items_per_run if self._max_items_per_run > 0 else None
        failure = None
        complete = False
        try:
            for index, source in enumerate(sources):
                self._checkpoint()
                if remaining is not None and remaining <= 0:
                    break
                self._progress(phase="scanning", message=f"扫描来源 {index + 1}/{len(sources)}：{source['name']}")
                response = self._dry_run_source(source, save=False, max_items=remaining or 0)
                if not response.success:
                    failure = response
                    break
                source_plan = response.data or []
                plan.extend(source_plan)
                if remaining is not None:
                    remaining -= len(source_plan)
                for item in source_plan:
                    self._report_scan({"source_name": item.get("source_name"), "path_hint": item.get("path_hint"),
                                       "status": item.get("status"), "reason": "；".join(item.get("warnings") or []) or "识别完成"})
            if save and failure is None:
                self.save_data("last_plan", plan)
            if failure:
                return failure
            complete = True
            if save:
                # 只有扫描了全部来源且没到上限，才能据此判断「文件已不在来源里」
                full_scan = media_type is None and not (remaining is not None and remaining <= 0)
                self._update_attention(plan, complete_scan=full_scan)
            ready = len(executable_plan_items(plan))
            return schemas.Response(success=True, message=f"预览已生成：待执行 {ready}，跳过 {len(plan) - ready}", data=plan)
        finally:
            summary = {"counts": self._scan_record_counts, "record_count": sum(self._scan_record_counts.values()),
                       "retained_records": len(self._scan_records), "limit_reached": remaining is not None and remaining <= 0,
                       "plan_count": len(plan), "completed": complete and not self._task.cancel.is_set()}
            self.save_data("scan_records", self._scan_records)
            self.save_data("scan_summary", summary)

    def _report_scan(self, record):
        reason = record.get("reason") or record.get("status") or "已发现"
        self._scan_record_counts[reason] = self._scan_record_counts.get(reason, 0) + 1
        if len(self._scan_records) < 5000:
            self._scan_records.append(record)
        self._progress(discovered=sum(self._scan_record_counts.values()))

    def trigger_api(self, data: TriggerRequest = None):
        return self._run_exclusive("external_trigger", lambda: self._trigger_api(data))

    def _trigger_api(self, data: TriggerRequest = None):
        data = data.model_dump() if isinstance(data, TriggerRequest) else (data or {})
        source = str(data.get("source") or "external").strip()
        execute = self._safe_bool(data.get("execute"), default=not self._dry_run)
        force_execute = self._safe_bool(data.get("force_execute"), default=False)
        logger.info(
            f"【115云端媒体整理】收到外部触发：source={source}，execute={execute}，"
            f"force_execute={force_execute}，dry_run={self._dry_run}"
        )

        known = self._attention_keys()
        dry_run_response = self.dry_run_all()
        if not dry_run_response.success:
            return dry_run_response

        plan = dry_run_response.data or []
        executable = executable_plan_items(plan)
        will_execute = bool(execute and self._allow_external_execute and executable
                            and (not self._dry_run or force_execute))
        if not will_execute:
            self._notify_new_attention(known)
        result = {
            "trigger_source": source,
            "dry_run": self._dry_run,
            "plan_count": len(plan),
            "executed": False,
            "execute_result": None,
        }

        if not execute:
            return schemas.Response(success=True, message=f"已触发 dry-run：{len(plan)} 条计划", data=result)
        if not self._allow_external_execute:
            return schemas.Response(
                success=False,
                message="外部执行未启用；本次仅生成计划，请由管理员在插件页面确认执行",
                data=result,
            )
        if self._dry_run and not force_execute:
            return schemas.Response(success=True, message=f"当前 dry_run=true，仅生成计划：{len(plan)} 条", data=result)
        if not executable:
            return schemas.Response(success=True, message="已触发整理：无可执行计划", data=result)

        execute_response = self._execute_last_plan(
            trigger_source=source,
            allow_dry_run=force_execute,
        )

        result["executed"] = bool(execute_response.success)
        result["execute_result"] = execute_response.data
        return schemas.Response(success=execute_response.success, message=execute_response.message, data=result)

    def execute_last_plan(self, trigger_source: str = "manual"):
        return self._run_exclusive(
            "execute_last_plan",
            lambda: self._execute_last_plan(trigger_source=trigger_source),
        )

    def _execute_last_plan(self, trigger_source: str = "manual", allow_dry_run: bool = False,
                           reviewed: bool = False):
        """执行最近的计划。

        reviewed=True 表示管理员已核对预览并确认，执行全部有效项目；否则是自动执行
        （定时、立即运行、外部触发），在保守策略下识别不明确的文件保留到人工确认。
        """
        guard = self._execute_guard(allow_dry_run=allow_dry_run)
        if guard:
            return guard
        plan = self.get_data("last_plan") or []
        run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + f"-{uuid4().hex[:6]}"
        started_at = datetime.now()
        logger.info(f"【115云端媒体整理】开始执行 last_plan：run_id={run_id}，计划 {len(plan)} 条")
        executable = executable_plan_items(plan)
        # 1. 只执行仍处于 planned/failed 的项目；executed/skipped 为终态，不重复处理。
        pending: List[Dict[str, Any]] = []
        held: List[Dict[str, Any]] = []
        for item in executable:
            item.pop("held_reason", None)
            reason = "" if reviewed or self._auto_execute_policy != "confident" else auto_execute_hold_reason(item)
            if reason:
                item["held_reason"] = reason
                held.append(item)
            else:
                pending.append(item)
        if held:
            logger.info(f"【115云端媒体整理】保守自动执行：{len(held)} 个文件识别不明确，保留到人工确认")
        self._confirmation = None
        self._execution_plan = plan
        self._progress(phase="executing", total=len(pending), completed=0, message="执行前校验文件与目标目录")
        result = ExecuteResult(
            plan_id=plan[0].get("plan_id") if plan else "",
            total=len(pending),
            held=len(held),
        )
        p115 = self._p115_ops()
        history = self.get_data("history") or []
        run_history: List[Dict[str, Any]] = []
        success_items: List[Dict[str, Any]] = []

        # 2. 按 batch_group_key 分组（旧 plan 缺字段时即时计算）
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for item in pending:
            key = item.get("batch_group_key") or compute_batch_group_key(item)
            groups.setdefault(key, []).append(item)

        batch_size = max(1, self._batch_size)
        logger.info(
            f"【115云端媒体整理】batch 分组完成：{len(groups)} 个 group，"
            f"待处理 {len(pending)} 个 item，batch_size={batch_size}"
        )

        # 3. 逐 group 执行；同 group 内按 batch_size 切片；批与批之间 sleep
        for group_key, items in groups.items():
            for offset in range(0, len(items), batch_size):
                if self._task.cancel.is_set():
                    break
                chunk = items[offset:offset + batch_size]
                self._execute_group(p115, chunk, run_id,
                                    history, run_history, result, success_items)
                self.save_data("last_plan", plan)
                self.save_data("history", history[-max(1, self._history_limit):])
                self._progress(completed=result.success + result.failed + result.skipped, success=result.success, failed=result.failed, message=f"已处理 {result.success + result.failed + result.skipped}/{len(pending)}")
                self._task.cancel.wait(self._jitter_sleep(self._sleep_between_batches))

        cleaned_dirs = []
        result_dict = result.to_dict()
        if self._delete_empty_source_dirs and not self._task.cancel.is_set():
            self._progress(phase="cleanup", message="清理已成功整理来源中的空目录和字幕")
            cleanup = self._cleanup_sources(p115, success_items)
            cleaned_dirs = cleanup["dirs"]
            result_dict["cleaned_empty_dirs"] = cleaned_dirs
            result_dict["deleted_subtitles"] = cleanup["subtitles"]
        result_dict["cancelled"] = self._task.cancel.is_set()
        result_dict["remaining"] = len(executable_plan_items(plan))
        result_dict["plex_refresh"] = [] if result_dict["cancelled"] else self._refresh_plex_after_success(success_items)
        result_dict["plex_refresh_summary"] = summarize_refresh(result_dict["plex_refresh"])
        result_dict["run_id"] = run_id
        result_dict["trigger_source"] = trigger_source or "manual"
        result_dict["started_at"] = started_at.strftime("%Y-%m-%d %H:%M:%S")
        finished_at = datetime.now()
        result_dict["finished_at"] = finished_at.strftime("%Y-%m-%d %H:%M:%S")
        result_dict["duration_seconds"] = round((finished_at - started_at).total_seconds(), 2)
        attention = self._update_attention(plan, complete_scan=False)
        result_dict["attention_count"] = len(attention)
        runs = self._append_run_summary(run_id, started_at, result_dict, run_history)
        history = history[-max(1, self._history_limit):]
        self.save_data("runs", runs)
        self.save_data("history", history)
        self.save_data("last_plan", plan)
        self.save_data("last_result", result_dict)
        logger.info(
            f"【115云端媒体整理】执行完成：总计 {result.total}，成功 {result.success}，"
            f"失败 {result.failed}，跳过 {result.skipped}，保留待确认 {result.held}，清理空目录 {len(cleaned_dirs)}"
        )
        plex_text = describe_refresh_summary(result_dict["plex_refresh_summary"])
        self._notify_run(result_dict, success_items, attention, plex_text)
        self._execution_plan = None
        prefix = "已安全停止" if result_dict["cancelled"] else "执行完成"
        message = f"{prefix}：成功 {result.success}，失败 {result.failed}，跳过 {result.skipped}，清理空目录 {len(cleaned_dirs)}"
        if result.held:
            message += f"；{result.held} 个识别不明确，已保留待确认"
        if plex_text:
            message += f"；{plex_text}"
        return schemas.Response(success=result.failed == 0, message=message, data=result_dict)

    def history(self, page: int = None, page_size: int = None, run_page: int = None, run_page_size: int = None):
        history = list(reversed(self.get_data("history") or []))
        runs = list(reversed(self.get_data("runs") or []))
        history_items, history_meta = self._paginate(
            history,
            self._safe_int(page, self._history_page),
            self._clamp_int(page_size, self._history_page_size, 1, 500),
        )
        run_items, run_meta = self._paginate(
            runs,
            self._safe_int(run_page, self._run_page),
            self._clamp_int(run_page_size, self._run_page_size, 1, 200),
        )
        return schemas.Response(success=True, data={
            "runs": run_items,
            "runs_pagination": run_meta,
            "history": history_items,
            "history_pagination": history_meta,
        })

    def clear_history(self):
        self.save_data("history", [])
        self.save_data("runs", [])
        return schemas.Response(success=True, message="历史已清空")

    def resolve_path_api(self, data: ResolvePathRequest):
        path = str(data.path or "").strip()
        if not path:
            return schemas.Response(success=False, message="path不能为空")
        p115 = self._p115_ops()
        if not p115.available:
            return schemas.Response(success=False, message=p115.import_error or "p115client不可用")
        try:
            return schemas.Response(success=True, data={"path": path, "cid": p115.resolve_path(path)})
        except Exception as err:
            return schemas.Response(success=False, message=str(err))

    def list_dir_api(self, data: ListDirectoryRequest):
        path = str(data.path or "").strip()
        cid = str(data.cid or "").strip()
        if self._active_operation or self._task.snapshot().get("status") in ("queued", "running", "stopping"):
            return schemas.Response(success=False, message="任务运行中，请等待结束再浏览目录")
        p115 = self._p115_ops()
        if not p115.available:
            return schemas.Response(success=False, message=p115.import_error or "p115client不可用")
        try:
            if not cid:
                cid = "0" if path in ("", "/") else p115.resolve_path(path)
            entries = [{
                "name": p115.entry_name(entry),
                "cid": p115.entry_cid(entry),
                "fid": p115.entry_fid(entry),
                "is_dir": p115.is_folder(entry),
                "size": p115.entry_size(entry),
            } for entry in p115.list_entries(cid)]
            return schemas.Response(success=True, data={"path": path or "/", "cid": cid, "items": entries})
        except Exception as err:
            return schemas.Response(success=False, message=str(err))

    def cookie_check_api(self, data: dict = None):
        if self._active_operation:
            return schemas.Response(success=False, message="任务运行中，请等待结束再检查连接")
        force = self._safe_bool((data or {}).get("force"), default=True)
        p115 = self._p115_ops()
        result = p115.health_check(force=force)
        self.save_data("connection_health", result)
        return schemas.Response(success=bool(result.get("ok")), message=result.get("message"), data=result)

    def auto_run(self):
        return self._run_exclusive("auto_run", self._auto_run)

    def _auto_run(self):
        logger.info(f"【115云端媒体整理】自动运行开始：dry_run={self._dry_run}")
        known = self._attention_keys()
        response = self.dry_run_all()
        if not response.success:
            logger.info(f"【115云端媒体整理】自动运行失败：{response.message}")
            self._notify_text("115云端媒体整理", response.message)
            return response
        ready = len(executable_plan_items(response.data or []))
        if not self._dry_run and ready:
            return self._execute_last_plan(trigger_source="auto")
        logger.info(f"【115云端媒体整理】自动运行完成：待执行 {ready}，未执行（{'仅预览' if self._dry_run else '无可执行文件'}）")
        if self._dry_run and ready:
            attention = self.get_data("attention") or []
            text = f"待确认执行 {ready} 个文件" + (f"，需处理 {len(attention)} 个" if attention else "")
            self._notify_text("115 整理预览已生成", text + "。请在插件页面核对后确认执行。")
        else:
            self._notify_new_attention(known)
        return response

    def _attention_keys(self) -> set:
        return {row.get("key") for row in self.get_data("attention") or []}

    def _notify_new_attention(self, known: set):
        """没有执行整理时，只为新出现的需处理文件通知一次，避免定时运行反复提醒同一批文件。"""
        attention = self.get_data("attention") or []
        new = [row for row in attention if row.get("key") not in known]
        if new:
            message = attention_message(new, len(attention))
            self._notify_text(message["title"], message["text"], mtype=MessageType.Manual)

    def _dry_run_for(self, media_type: str, save: bool = True):
        return self._generate_plan(media_type=media_type, save=save)

    def _dry_run_source(
        self,
        source: Dict[str, Any],
        save: bool = True,
        max_items: Optional[int] = None,
    ):
        try:
            p115 = self._p115_ops()
            if not p115.available:
                logger.info(f"【115云端媒体整理】p115client不可用：{p115.import_error}")
                return schemas.Response(success=False, message=p115.import_error or "p115client不可用")
            media_type = str(source.get("media_type") or "").lower()
            source_cid = str(source.get("source_cid") or "")
            source_path = str(source.get("source_path") or source_cid)
            target_root_path = str(source.get("target_root_path") or "")
            if source_contains_target(source_path, target_root_path):
                return schemas.Response(
                    success=False,
                    message=f"目标目录不能等于或位于来源目录内部：{source_path} -> {target_root_path}",
                )
            logger.info(f"【115云端媒体整理】开始扫描来源：类型={media_type}，路径={source_path}")
            if not source_cid and source_path:
                source_cid = p115.resolve_path(source_path)
                source = dict(source, source_cid=source_cid)
                logger.info(f"【115云端媒体整理】来源路径解析成功：{source_path} -> {source_cid}")
            target_cids = self._current_target_cids(source=source, p115=p115)
            if media_type not in ("movie", "tv") or not source_cid:
                return schemas.Response(success=False, message=f"来源映射无效：{source}")
            items = p115.walk_media_items(
                source_cid=source_cid,
                source_path=source_path,
                max_depth=max(0, self._max_depth),
                min_file_size=max(0, self._min_file_size_mb) * 1024 * 1024,
                exclude_keywords=self._exclude_list(),
                max_items=max(0, self._max_items_per_run if max_items is None else max_items),
                checkpoint=self._checkpoint, report=self._report_scan,
            )
            logger.info(f"【115云端媒体整理】来源扫描完成：{source_path}，候选视频 {len(items)} 个")
            mapper = CategoryMapper(self._category_mapping_dict())
            target_resolver = self._target_resolver_for_source(
                source=source,
                target_cids=target_cids,
                p115=p115,
            )
            planner = Planner(mapper, target_cids, target_resolver=target_resolver)
            plan = planner.build_plans(
                media_type,
                items,
                self._config_snapshot(),
                self.get_data("history") or [],
                self._unrecognized_action,
                source_root_cid=source_cid, plan_id=self._scan_plan_id,
                target_root_path=target_root_path, checkpoint=self._checkpoint,
                progress=lambda done, name: self._progress(phase="recognizing", completed=done, total=len(items), message=f"识别 {done + 1}/{len(items)}：{name}"),
            )
            if save:
                self.save_data("last_plan", plan)
            logger.info(f"【115云端媒体整理】来源计划生成完成：{source_path}，计划 {len(plan)} 条")
            return schemas.Response(success=True, message=f"已生成{media_type}整理计划：{len(plan)} 条", data=plan)
        except TaskCancelled:
            raise
        except Exception as err:
            logger.error(f"生成115整理计划失败：{err}\n{traceback.format_exc()}")
            return schemas.Response(success=False, message="生成预览失败，请查看扫描结果和插件日志；旧计划已失效")

    def _execute_guard(self, allow_dry_run: bool = False):
        validation_config = self.validate_config_api()
        if not validation_config.success:
            return validation_config
        if self._dry_run and not allow_dry_run:
            return schemas.Response(success=False, message="定时任务设置为仅生成预览；手动执行请在插件页面确认")
        plan = self.get_data("last_plan") or []
        validation = validate_plan(
            plan,
            config_snapshot=self._config_snapshot(),
            ttl_hours=self._plan_ttl_hours,
        )
        if not validation.valid:
            return schemas.Response(success=False, message=validation.message)
        p115 = self._p115_ops()
        if not p115.available:
            return schemas.Response(success=False, message=p115.import_error or "p115client不可用")
        health = self.get_data("connection_health") or {}
        if health.get("kind") in ("login", "dependency"):
            return schemas.Response(success=False, message="115 连接不可用，请更新 Cookie 或修复依赖后重新检查连接")
        return None

    def _config_snapshot(self) -> Dict[str, Any]:
        return {
            "source_mappings": self._source_mapping_list(),
            "category_mapping": self._category_mapping_dict(),
            "target_cids": self._target_cids_dict(),
            "conflict_strategy": self._conflict_strategy,
            "unrecognized_action": self._unrecognized_action,
            "delete_empty_source_dirs": self._delete_empty_source_dirs,
        }

    def _current_target_cids(
        self,
        source: Dict[str, Any],
        p115: P115Ops = None,
    ) -> Dict[str, Dict[str, str]]:
        """按当前来源的目标根目录解析分类 CID，避免同类型多来源串用目标目录。"""
        p115 = p115 or self._p115_ops()
        if not p115.available:
            return self._target_cids_dict()
        resolved, errors = resolve_target_cids_for_source(
            self._target_cids_dict(),
            source,
            p115.resolve_path,
        )
        for error in errors:
            logger.warning(f"【115云端媒体整理】目标分类路径解析失败：{error}")
        return resolved


    @staticmethod
    def _target_resolver_for_source(
        source: Dict[str, Any],
        target_cids: Dict[str, Any],
        p115: P115Ops,
    ):
        """按需解析 V3 分类路径，使自定义分类无需预先写入 target_cids。"""
        target_root = str(source.get("target_root_path") or "").rstrip("/")
        cache: Dict[str, str] = {}

        def resolve(media_type: str, category: str) -> str:
            configured = str(target_cids.get(media_type, {}).get(category) or "")
            if configured:
                return configured
            key = f"{media_type}:{category}"
            if key not in cache:
                cache[key] = p115.resolve_path(f"{target_root}/{category}")
            target_cids.setdefault(media_type, {})[category] = cache[key]
            return cache[key]

        return resolve

    def _category_mapping_dict(self) -> Dict[str, Dict[str, str]]:
        try:
            data = json.loads(self._category_mapping or "{}")
            return data if isinstance(data, dict) else {"movie": {}, "tv": {}}
        except (ValueError, TypeError):
            return {"movie": {}, "tv": {}}  # validate_config_api blocks malformed input

    def _target_cids_dict(self) -> Dict[str, Any]:
        try:
            data = json.loads(self._target_cids or "{}")
        except (ValueError, TypeError):
            data = {}
        if not isinstance(data, dict):
            data = {}
        return {"movie": dict(data.get("movie") or {}) if isinstance(data.get("movie", {}), dict) else {},
                "tv": dict(data.get("tv") or {}) if isinstance(data.get("tv", {}), dict) else {},
                "unrecognized": data.get("unrecognized") or ""}

    def _source_mapping_list(self) -> List[Dict[str, str]]:
        check = check_configuration({"source_mappings": self._source_mappings})
        return check.sources if check.valid else []

    def _record_outcome(self, item: Dict[str, Any], status: str, error: str,
                        run_id: str,
                        history: List[Dict[str, Any]],
                        run_history: List[Dict[str, Any]],
                        result: ExecuteResult,
                        success_items: Optional[List[Dict[str, Any]]] = None) -> None:
        """统一更新 item 字段 + 写 history 记录 + 累加 ExecuteResult。"""
        item["status"] = status
        if error:
            item["error"] = error
        elif status == "executed":
            item["error"] = None
        record = self._history_record(item, status, error or "", run_id=run_id)
        history.append(record)
        run_history.append(record)
        # Checkpoint each completed outcome, not only the end of a long task.
        if getattr(self, "_execution_plan", None) is not None:
            self.save_data("last_plan", self._execution_plan)
            self.save_data("history", history[-max(1, self._history_limit):])
        if status == "executed":
            result.success += 1
            if success_items is not None:
                success_items.append(dict(item))
            logger.info(f"【115云端媒体整理】执行成功：{item.get('source_name')} -> {item.get('target_path')}")
        elif status == "skipped":
            result.skipped += 1
            logger.info(f"【115云端媒体整理】执行跳过：{item.get('source_name')}，原因：{error}")
        elif status == "failed":
            result.failed += 1
            result.errors.append({"source": item.get("source_name"), "error": error or ""})
            logger.info(f"【115云端媒体整理】执行失败：{item.get('source_name')}，原因：{error}")
        self._progress(completed=result.success + result.failed + result.skipped, success=result.success, failed=result.failed)

    def _execute_group(self, p115: P115Ops,
                       items: List[Dict[str, Any]],
                       run_id: str,
                       history: List[Dict[str, Any]],
                       run_history: List[Dict[str, Any]],
                       result: ExecuteResult,
                       success_items: List[Dict[str, Any]]) -> None:
        """处理一个 batch（来自同 group，长度 ≤ batch_size）。
        一次 ensure_dir + 一次 list_entries 冲突检查 + batch_rename + batch_move；
        任一阶段抛错时退回逐条 fallback，单条粒度的成功/失败仍写入 history。
        """
        # 准入：校验关键 ID，并确认源文件仍处于 dry-run 时的位置和状态。
        accepted: List[tuple] = []  # (source_id, item)
        source_cache: Dict[str, Dict[str, Any]] = {}
        for item in items:
            source_id = item.get("source_cid") if item.get("source_is_dir") else item.get("source_fid")
            if not source_id:
                self._record_outcome(item, "failed", "源文件ID为空",
                                     run_id, history, run_history, result, success_items)
                continue
            if not item.get("target_parent_cid"):
                self._record_outcome(item, "failed", "目标父目录CID为空",
                                     run_id, history, run_history, result, success_items)
                continue
            parent_cid = str(item.get("source_parent_cid") or "")
            if not parent_cid:
                self._record_outcome(item, "failed", "源父目录CID为空",
                                     run_id, history, run_history, result, success_items)
                continue
            if parent_cid not in source_cache:
                try:
                    source_cache[parent_cid] = self._entries_by_id(p115, parent_cid)
                except Exception as err:
                    source_cache[parent_cid] = {"__error__": err}
            parent_entries = source_cache[parent_cid]
            if "__error__" in parent_entries:
                self._record_outcome(item, "failed", f"执行前校验源目录失败：{parent_entries['__error__']}",
                                     run_id, history, run_history, result, success_items)
                continue
            source_entry = parent_entries.get(str(source_id))
            if source_entry is None:
                self._record_outcome(item, "failed", "源文件已移动或不存在，请重新dry-run",
                                     run_id, history, run_history, result, success_items)
                continue
            source_validation = source_entry_matches_plan(
                item,
                current_name=p115.entry_name(source_entry),
                current_size=p115.entry_size(source_entry),
            )
            if not source_validation.valid:
                self._record_outcome(item, "failed", source_validation.message,
                                     run_id, history, run_history, result, success_items)
                continue
            accepted.append((source_id, item))
        if not accepted:
            return

        first_item = accepted[0][1]

        # ensure_dir：同 group 共享同一目标分类目录 + 季目录，只 ensure 一次
        try:
            final_parent = p115.ensure_dir(first_item["target_parent_cid"],
                                            first_item.get("target_dir_name"))
            if first_item.get("target_season_dir_name"):
                final_parent = p115.ensure_dir(final_parent,
                                                first_item["target_season_dir_name"])
        except Exception as err:
            for _, item in accepted:
                self._record_outcome(item, "failed", f"创建目标目录失败：{err}",
                                     run_id, history, run_history, result, success_items)
            return

        # 一次性 list_entries 目标目录，构造同名文件集合做冲突检测；失败则全组退回逐条
        try:
            existing_entries = p115.list_entries(final_parent)
        except P115UnavailableError as err:
            logger.warning(
                f"【115云端媒体整理】list_entries({final_parent}) 失败，本组退回逐条 fallback：{err}"
            )
            for _, item in accepted:
                self._execute_single_item_fallback(p115, item, run_id,
                                                    history, run_history, result, success_items)
            return
        existing_file_names = {p115.entry_name(e) for e in existing_entries if not p115.is_folder(e)}

        # 决定每个 item 的最终 target_name；冲突按 conflict_strategy 处理
        to_process: List[tuple] = []  # (source_id, item, final_target_name)
        for source_id, item in accepted:
            target_name = item.get("target_name") or item.get("source_name")
            if not item.get("source_is_dir") and target_name in existing_file_names:
                if self._conflict_strategy == "skip":
                    self._record_outcome(item, "skipped", f"目标已存在：{target_name}",
                                         run_id, history, run_history, result, success_items)
                    continue
                if self._conflict_strategy == "rename_with_suffix":
                    target_name = self._next_available_in_set(target_name, existing_file_names)
                    existing_file_names.add(target_name)  # 同组内后续 item 不再撞这个新名字
            to_process.append((source_id, item, target_name))
        if not to_process:
            return

        # 阶段 1：batch_rename（只针对需要改名的 item，按 BATCH_RENAME_MAX 切片）
        renames = {sid: name for sid, item, name in to_process
                   if name != item.get("source_name")}
        rename_failed_sids = set()
        already_moved_sids = set()
        if renames:
            completed_rename_sids = set()
            try:
                for chunk in self._chunks_dict(renames, BATCH_RENAME_MAX):
                    logger.info(f"【115云端媒体整理】batch_rename({len(chunk)})")
                    p115.batch_rename(chunk)
                    completed_rename_sids.update(chunk)
            except P115UnavailableError as err:
                logger.warning(f"【115云端媒体整理】batch_rename 结果不确定，核对状态后逐条恢复：{err}")
                item_by_sid = {sid: item for sid, item, _ in to_process}
                for fid, name in renames.items():
                    if fid in completed_rename_sids:
                        continue
                    item = item_by_sid[fid]
                    state = self._locate_item_state(p115, item, final_parent, name)
                    if state == "target":
                        already_moved_sids.add(fid)
                        continue
                    if state == "renamed":
                        continue
                    if state != "source":
                        rename_failed_sids.add(fid)
                        self._record_outcome(item, "failed", "rename 后无法确认源文件状态",
                                             run_id, history, run_history, result, success_items)
                        continue
                    try:
                        p115.rename(fid, name)
                    except Exception as single_err:
                        rename_failed_sids.add(fid)
                        self._record_outcome(item, "failed", f"rename 失败：{single_err}",
                                             run_id, history, run_history, result, success_items)

        # 阶段 2：batch_move（剔除 rename 失败和已确认移动成功的项目）
        for sid, item, name in to_process:
            if sid in already_moved_sids:
                item["target_name"] = name
                item["target_parent_cid"] = final_parent
                self._record_outcome(item, "executed", "",
                                     run_id, history, run_history, result, success_items)
        movable = [(sid, item, name) for sid, item, name in to_process
                   if sid not in rename_failed_sids and sid not in already_moved_sids]
        if not movable:
            return
        fids = [sid for sid, _, _ in movable]
        try:
            logger.info(f"【115云端媒体整理】batch_move({len(fids)} -> {final_parent})")
            p115.batch_move(fids, final_parent)
            for sid, item, name in movable:
                item["target_name"] = name
                item["target_parent_cid"] = final_parent
                self._record_outcome(item, "executed", "",
                                     run_id, history, run_history, result, success_items)
        except P115UnavailableError as err:
            logger.warning(f"【115云端媒体整理】batch_move 结果不确定，核对状态后逐条恢复：{err}")
            for sid, item, name in movable:
                state = self._locate_item_state(p115, item, final_parent, name)
                if state == "target":
                    item["target_name"] = name
                    item["target_parent_cid"] = final_parent
                    self._record_outcome(item, "executed", "",
                                         run_id, history, run_history, result, success_items)
                    continue
                if state not in {"source", "renamed"}:
                    self._record_outcome(item, "failed", "move 后无法确认源文件状态",
                                         run_id, history, run_history, result, success_items)
                    continue
                try:
                    p115.move(sid, final_parent)
                    item["target_name"] = name
                    item["target_parent_cid"] = final_parent
                    self._record_outcome(item, "executed", "",
                                         run_id, history, run_history, result, success_items)
                except Exception as single_err:
                    self._record_outcome(item, "failed", f"move 失败：{single_err}",
                                         run_id, history, run_history, result, success_items)

    @staticmethod
    def _entries_by_id(p115: P115Ops, parent_cid: str) -> Dict[str, Any]:
        entries = {}
        for entry in p115.list_entries(parent_cid):
            entry_id = p115.entry_cid(entry) if p115.is_folder(entry) else p115.entry_fid(entry)
            if entry_id:
                entries[str(entry_id)] = entry
        return entries

    @staticmethod
    def _locate_item_state(
        p115: P115Ops,
        item: Dict[str, Any],
        target_parent: str,
        target_name: str,
    ) -> str:
        """在副作用响应不确定时核对真实状态，避免盲目重复 rename/move。"""
        source_id = str(item.get("source_cid") if item.get("source_is_dir") else item.get("source_fid") or "")
        if not source_id:
            return "missing"
        try:
            target_entry = p115.find_entry_by_id(target_parent, source_id)
            if target_entry is not None and p115.entry_name(target_entry) == target_name:
                return "target"
        except Exception:
            pass
        source_parent = str(item.get("source_parent_cid") or "")
        try:
            source_entry = p115.find_entry_by_id(source_parent, source_id)
        except Exception:
            return "unknown"
        if source_entry is None:
            return "missing"
        return "renamed" if p115.entry_name(source_entry) == target_name else "source"

    def _execute_single_item_fallback(self, p115: P115Ops,
                                       item: Dict[str, Any],
                                       run_id: str,
                                       history: List[Dict[str, Any]],
                                       run_history: List[Dict[str, Any]],
                                       result: ExecuteResult,
                                       success_items: List[Dict[str, Any]]) -> None:
        """单条 fallback：当 ensure_dir / list_entries 失败、batch 路径不可用时用旧 execute_move。"""
        try:
            outcome = p115.execute_move(item, conflict_strategy=self._conflict_strategy)
            if outcome.get("success"):
                item["target_name"] = outcome.get("target_name") or item.get("target_name")
                item["target_parent_cid"] = outcome.get("target_parent_cid") or item.get("target_parent_cid")
                self._record_outcome(item, "executed", "",
                                     run_id, history, run_history, result, success_items)
            elif outcome.get("skipped"):
                self._record_outcome(item, "skipped", outcome.get("message") or "",
                                     run_id, history, run_history, result, success_items)
            else:
                self._record_outcome(item, "failed", outcome.get("message") or "",
                                     run_id, history, run_history, result, success_items)
        except Exception as err:
            self._record_outcome(item, "failed", str(err),
                                 run_id, history, run_history, result, success_items)

    @staticmethod
    def _chunks_dict(d: Dict[str, str], size: int):
        items = list(d.items())
        for i in range(0, len(items), size):
            yield dict(items[i:i + size])

    @staticmethod
    def _next_available_in_set(name: str, existing: set) -> str:
        """在已知集合 existing 中找 'name (N).ext' 形式的下一个不冲突候选名。"""
        path = Path(name)
        stem = path.stem if path.suffix else name
        suffix = path.suffix
        counter = 1
        while True:
            candidate = f"{stem} ({counter}){suffix}"
            if candidate not in existing:
                return candidate
            counter += 1

    def _cleanup_sources(
        self,
        p115: P115Ops,
        success_items: List[Dict[str, Any]],
    ) -> Dict[str, List[str]]:
        """只清理本轮成功移动所涉及的来源根，避免触碰无关来源目录。

        字幕不随视频整理：只剩字幕的来源目录会连同字幕一起删除；仍需保留的目录里，
        只删除本轮已整理视频的同名字幕（如「视频名.chs.srt」），其他文件不动。
        返回 {"dirs": 已删除目录 CID, "subtitles": 已删除字幕文件名}。
        """
        result: Dict[str, List[str]] = {"dirs": [], "subtitles": []}
        source_roots = {
            str(item.get("source_root_cid"))
            for item in success_items
            if item.get("source_root_cid")
        }
        stems: Dict[str, List[str]] = {}
        for item in success_items:
            if not item.get("source_is_dir") and item.get("source_parent_cid") and item.get("source_name"):
                stems.setdefault(str(item["source_parent_cid"]), []).append(PurePosixPath(item["source_name"]).stem)
        logger.info(f"【115云端媒体整理】开始清理来源目录：来源根 {len(source_roots)} 个")
        plans: List[Dict[str, Any]] = []
        for source_cid in source_roots:
            if self._task.cancel.is_set():
                return result
            plans.append(p115.plan_source_cleanup(
                source_cid,
                max(0, self._max_depth) + 2,
                removable_extensions=SUBTITLE_EXTENSIONS,
                sidecar_stems=stems,
            ))
        batch_size = max(1, self._batch_size)
        for plan in plans:
            # 先删除保留目录中的同名字幕，再自底向上删除空目录（只剩字幕的目录连同字幕一起删除）
            names = {f["fid"]: f["name"] for f in plan["files"]}
            for kind, ids in (("字幕", list(names)), ("空目录", plan["dirs"])):
                for offset in range(0, len(ids), batch_size):
                    if self._task.cancel.is_set():
                        return result
                    for entry_id in self._delete_entries(p115, ids[offset:offset + batch_size], kind):
                        if kind == "字幕":
                            result["subtitles"].append(names[entry_id])
                        else:
                            result["dirs"].append(entry_id)
                            result["subtitles"].extend(plan["dir_files"].get(entry_id, []))
        logger.info(
            f"【115云端媒体整理】来源目录清理完成：空目录 {len(result['dirs'])} 个，字幕 {len(result['subtitles'])} 个"
        )
        return result

    @staticmethod
    def _delete_entries(p115: P115Ops, ids: List[str], label: str) -> List[str]:
        """批量删除；失败时逐条重试。返回已删除的 ID。"""
        if not ids:
            return []
        try:
            p115.batch_delete(ids)
            logger.info(f"【115云端媒体整理】批量删除{label} {len(ids)} 个")
            return list(ids)
        except Exception as err:
            logger.warning(f"【115云端媒体整理】批量删除{label}失败，回退逐条：{err}")
        deleted = []
        for entry_id in ids:
            try:
                p115.delete(entry_id)
                deleted.append(entry_id)
                logger.info(f"【115云端媒体整理】已删除{label}：{entry_id}")
            except Exception as single_err:
                logger.warning(f"【115云端媒体整理】删除{label}失败 {entry_id}: {single_err}")
        return deleted

    def _exclude_list(self) -> List[str]:
        return [item.strip() for item in self._exclude_keywords.split(",") if item.strip()]

    def _p115_ops(self) -> P115Ops:
        # 单例复用：让 P115Ops 内部的限速 / cookie 健康 30s 缓存跨调用真正生效。
        # 配置变更走 init_plugin → 那里会把 _ops_instance 清空，下次调用自然重建。
        if self._ops_instance is None:
            self._ops_instance = P115Ops(
                cookie_path=self._cookie_path if self._cookie_mode == "file" else "",
                cookie_text=self._cookie_text if self._cookie_mode == "text" else "",
                min_interval=self._min_request_interval_ms / 1000.0,
                max_retries=self._max_retries,
                retry_base=self._retry_base_seconds,
                jitter_ratio=self._jitter_ratio,
                list_page_size=self._list_page_size,
            )
        return self._ops_instance

    def _refresh_plex_after_success(self, success_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not success_items:
            logger.info("【115云端媒体整理】无成功整理项目，跳过Plex刷新")
            return []
        if not self._refresh_plex_after_execute:
            logger.info("【115云端媒体整理】整理后刷新Plex未启用，跳过刷新")
            return []

        roots_by_type: Dict[str, str] = {}
        for source in self._source_mapping_list():
            roots_by_type.setdefault(source["media_type"], source["target_root_path"])
        folders = refresh_folders(success_items, roots_by_type)
        if not folders:
            logger.info("【115云端媒体整理】未生成Plex刷新目录，跳过刷新")
            return []

        services = self._plex_service_infos()
        if not services:
            # 未配置或未连接 Plex 不计入目录失败数，避免未使用 Plex 的用户每次通知都出现失败提示。
            return [{"success": False, "status": "unavailable", "message": "未找到可用的Plex媒体服务器，未刷新"}]

        mappings, errors = parse_path_mappings(self._plex_path_mappings)
        for error in errors:
            logger.warning(f"【115云端媒体整理】{error}，该行已忽略")
        logger.info(f"【115云端媒体整理】开始刷新Plex：服务器 {len(services)} 个，目录 {len(folders)} 个")
        results = []
        for service_name, service_info in services.items():
            results.extend(self._refresh_plex_server(service_name, service_info.instance, folders, mappings))
        return results

    def _refresh_plex_server(self, service_name: str, instance: Any,
                             folders: List[Dict[str, str]], mappings: List[Any]) -> List[Dict[str, Any]]:
        """只对匹配到的 Plex 媒体库提交局部扫描。

        不调用宿主 refresh_library_by_items：它在任一路径匹配失败时会刷新全部媒体库。
        """
        get_plex = getattr(instance, "get_plex", None)
        plex = get_plex() if callable(get_plex) else None
        if plex is None:
            logger.warning(f"【115云端媒体整理】Plex刷新失败：{service_name} 无法获取Plex连接")
            return [{"success": False, "status": "failed", "server": service_name, "message": "无法获取Plex连接，未刷新"}]
        try:
            libraries = load_plex_libraries(plex)
        except Exception as err:
            logger.warning(f"【115云端媒体整理】读取Plex媒体库失败：{service_name}，原因：{err}")
            return [{"success": False, "status": "failed", "server": service_name, "message": f"读取Plex媒体库失败：{err}"}]

        results = []
        for folder in folders:
            row = {
                "server": service_name,
                "media_type": folder["media_type"],
                "category": folder["category"],
                "source_path": folder["path"],
            }
            targets, method = resolve_refresh_targets(folder["path"], mappings, libraries)
            if not targets:
                results.append({
                    **row,
                    "success": False,
                    "status": "unmatched",
                    "library": "",
                    "target_path": "",
                    "message": "未匹配到Plex媒体库，已跳过（不会刷新全部媒体库）；可在高级设置填写Plex路径映射",
                })
                logger.warning(f"【115云端媒体整理】Plex未匹配到媒体库，跳过刷新：{service_name}，{folder['path']}")
                continue
            for library, plex_path in targets:
                try:
                    plex.query(refresh_endpoint(library.key, plex_path))
                except Exception as err:
                    results.append({
                        **row,
                        "success": False,
                        "status": "failed",
                        "library": library.title,
                        "target_path": plex_path,
                        "message": f"刷新失败：{err}",
                    })
                    logger.warning(f"【115云端媒体整理】Plex刷新异常：{service_name} / {library.title} - {plex_path}，原因：{err}")
                    continue
                results.append({
                    **row,
                    "success": True,
                    "status": "refreshed",
                    "library": library.title,
                    "target_path": plex_path,
                    "message": f"已提交刷新（{method}）",
                })
                logger.info(f"【115云端媒体整理】Plex刷新已提交：{service_name} / {library.title} - {plex_path}")
        return results

    def _plex_service_infos(self) -> Dict[str, Any]:
        try:
            services = MediaServerHelper().get_services(type_filter="plex", name_filters=self._plex_mediaservers or None)
            if not services:
                logger.warning("【115云端媒体整理】未找到Plex媒体服务器，请检查MoviePilot媒体服务器配置")
                return {}
            active_services = {}
            for service_name, service_info in services.items():
                if service_info.instance.is_inactive():
                    logger.warning(f"【115云端媒体整理】Plex媒体服务器未连接：{service_name}")
                    continue
                active_services[service_name] = service_info
            if not active_services:
                logger.warning("【115云端媒体整理】没有已连接的Plex媒体服务器")
            return active_services
        except Exception as err:
            logger.warning(f"【115云端媒体整理】获取Plex媒体服务器失败：{err}")
            return {}

    def _update_attention(self, plan: List[Dict[str, Any]], complete_scan: bool) -> List[Dict[str, Any]]:
        """维护「需处理」列表：跳过、失败或保留待确认的文件，直到后续扫描不再报告问题。"""
        rows = attention_items(plan, self.get_data("attention") or [], complete_scan=complete_scan)
        rows = stamp_first_seen(rows, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.save_data("attention", rows)
        return rows

    def _notify_run(self, result: Dict[str, Any], success_items: List[Dict[str, Any]],
                    attention: List[Dict[str, Any]], plex_text: str = ""):
        """执行结果通知：有入库时用「整理入库」类型并附片名和海报，否则需人工处理时用「手动处理」类型。"""
        message = organize_message(result, success_items, attention, plex_text)
        if result.get("success"):
            mtype = MessageType.Organize
        elif result.get("failed") or result.get("held") or attention:
            mtype = MessageType.Manual
        else:
            mtype = MessageType.Plugin
        if self._notify:
            self.post_message(mtype=mtype, title=message["title"], text=message["text"],
                              image=message["image"] or None)

    def _notify_text(self, title: str, text: str, mtype=None):
        if self._notify:
            self.post_message(mtype=mtype or MessageType.Plugin, title=title, text=text)

    def _append_run_summary(
        self,
        run_id: str,
        started_at: datetime,
        result: Dict[str, Any],
        run_history: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        runs = self.get_data("runs") or []
        media_counts = self._count_by(run_history, "media_type")
        category_counts = self._count_by(run_history, "target_category")
        sample_items = [{
            "source_name": item.get("source_name"),
            "target_name": item.get("target_name"),
            "target_category": item.get("target_category"),
            "status": item.get("status"),
            "error": item.get("error"),
        } for item in run_history[:10]]
        runs.append({
            "run_id": run_id,
            "time": started_at.strftime("%Y-%m-%d %H:%M:%S"),
            "finished_at": result.get("finished_at"),
            "duration_seconds": result.get("duration_seconds"),
            "cancelled": result.get("cancelled", False),
            "source": result.get("trigger_source") or "manual",
            "plan_id": result.get("plan_id"),
            "total": result.get("total", 0),
            "success": result.get("success", 0),
            "failed": result.get("failed", 0),
            "skipped": result.get("skipped", 0),
            "held": result.get("held", 0),
            "plex_refresh_count": summarize_refresh(result.get("plex_refresh"))["refreshed"],
            "cleaned_empty_dirs": len(result.get("cleaned_empty_dirs") or []),
            "deleted_subtitles": len(result.get("deleted_subtitles") or []),
            "media_counts": media_counts,
            "category_counts": category_counts,
            "sample_items": sample_items,
        })
        return runs[-max(1, self._run_limit):]

    @staticmethod
    def _history_record(item: Dict[str, Any], status: str, error: str, run_id: str = "") -> Dict[str, Any]:
        return {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "run_id": run_id,
            "item_id": item.get("item_id"),
            "source_fid": item.get("source_fid"),
            "source_cid": item.get("source_cid"),
            "media_type": item.get("media_type"),
            "source_name": item.get("source_name"),
            "target_category": item.get("target_category"),
            "target_name": item.get("target_name"),
            "target_path": item.get("target_path"),
            "status": status,
            "error": error,
        }

    def _default_config(self) -> Dict[str, Any]:
        return {
            "enabled": False,
            "notify": True,
            "onlyonce": False,
            "cron": "",
            "dry_run": True,
            "delete_empty_source_dirs": True,
            "refresh_plex_after_execute": True,
            "allow_external_execute": False,
            "auto_execute_policy": "confident",
            "plex_mediaservers": [],
            "plex_path_mappings": "",
            "max_depth": 5,
            "max_items_per_run": 200,
            "min_file_size_mb": 100,
            "batch_size": 30,
            "sleep_between_batches": 1.0,
            "conflict_strategy": "skip",
            "unrecognized_action": "skip",
            "cookie_path": "/config/115-cookies.txt",
            "cookie_text": "",
            "source_mappings": "[]",
            "cookie_mode": "file",
            "exclude_keywords": "sample,trailer,花絮,预告",
            "category_mapping": json.dumps(DEFAULT_CATEGORY_MAPPING, ensure_ascii=False, indent=2),
            "target_cids": json.dumps(DEFAULT_TARGET_CIDS, ensure_ascii=False, indent=2),
            "min_request_interval_ms": ANTI_BLOCK_DEFAULTS["min_request_interval_ms"],
            "max_retries": ANTI_BLOCK_DEFAULTS["max_retries"],
            "retry_base_seconds": ANTI_BLOCK_DEFAULTS["retry_base_seconds"],
            "jitter_ratio": ANTI_BLOCK_DEFAULTS["jitter_ratio"],
            "list_page_size": ANTI_BLOCK_DEFAULTS["list_page_size"],
            "history_limit": 1000,
            "run_limit": 100,
            "history_page": 1,
            "history_page_size": 50,
            "plan_ttl_hours": 24,
            "run_page": 1,
            "run_page_size": 10,
        }

    @staticmethod
    def _safe_bool(value: Any, default: bool = False) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "y", "on", "执行", "是"}
        return default

    @staticmethod
    def _safe_int(value: Any, default: int) -> int:
        try:
            return int(value)
        except Exception:
            return default

    @classmethod
    def _clamp_int(cls, value: Any, default: int, minimum: int, maximum: int) -> int:
        return max(minimum, min(maximum, cls._safe_int(value, default)))

    @classmethod
    def _paginate(cls, items: List[Any], page: int, page_size: int) -> Tuple[List[Any], Dict[str, int]]:
        total = len(items)
        page_size = cls._clamp_int(page_size, 50, 1, 500)
        total_pages = max(1, (total + page_size - 1) // page_size)
        page = max(1, min(cls._safe_int(page, 1), total_pages))
        start_index = (page - 1) * page_size
        end_index = min(total, start_index + page_size)
        return items[start_index:end_index], {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "start": start_index + 1 if total else 0,
            "end": end_index,
        }

    @staticmethod
    def _safe_float(value: Any, default: float) -> float:
        try:
            return float(value)
        except Exception:
            return default

    def _jitter_sleep(self, base: float) -> float:
        """对固定 sleep 值施加 ±jitter_ratio 的随机抖动，避免可识别的节奏。"""
        base = max(0.0, float(base or 0.0))
        if base <= 0:
            return 0.0
        ratio = max(0.0, min(1.0, float(self._jitter_ratio or 0.0)))
        if ratio <= 0:
            return base
        return base * random.uniform(1.0 - ratio, 1.0 + ratio)

    @staticmethod
    def _count_by(items: List[Dict[str, Any]], key: str) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for item in items:
            value = str(item.get(key) or "")
            counts[value] = counts.get(value, 0) + 1
        return counts
