import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app import schemas
from app.core.config import settings
from app.log import logger
from app.plugins import _PluginBase
from app.schemas.types import NotificationType

from .category_mapper import DEFAULT_CATEGORY_MAPPING, CategoryMapper
from .models import ExecuteResult
from .p115_ops import P115Ops, P115UnavailableError
from .planner import Planner


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


class P115MediaOrganizer(_PluginBase):
    plugin_name = "115云端媒体整理"
    plugin_desc = "将115最近接收中的媒体云端整理到媒体库。"
    plugin_icon = "clouddisk.png"
    plugin_version = "0.2.0"
    plugin_author = "Zongfei"
    author_url = "https://github.com/Zongfei"
    plugin_config_prefix = "p115mediaorganizer_"
    plugin_order = 50
    auth_level = 2

    _enabled = False
    _notify = True
    _onlyonce = False
    _cron = ""
    _dry_run = True
    _delete_empty_source_dirs = True
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
    _source_mappings = json.dumps(DEFAULT_SOURCE_MAPPINGS, ensure_ascii=False, indent=2)
    _category_mapping = json.dumps(DEFAULT_CATEGORY_MAPPING, ensure_ascii=False, indent=2)
    _target_cids = json.dumps(DEFAULT_TARGET_CIDS, ensure_ascii=False, indent=2)
    _history_limit = 1000
    _scheduler = None

    def init_plugin(self, config: dict = None):
        self.stop_service()
        config = config or {}
        self._enabled = bool(config.get("enabled", False))
        self._notify = bool(config.get("notify", True))
        self._onlyonce = bool(config.get("onlyonce", False))
        self._cron = str(config.get("cron") or "").strip()
        self._dry_run = bool(config.get("dry_run", True))
        self._delete_empty_source_dirs = bool(config.get("delete_empty_source_dirs", True))
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
        self._source_mappings = config.get("source_mappings") or self._source_mappings
        self._category_mapping = config.get("category_mapping") or self._category_mapping
        self._target_cids = config.get("target_cids") or self._target_cids
        self._history_limit = self._safe_int(config.get("history_limit"), 1000)
        logger.info(
            f"【115云端媒体整理】插件初始化：enabled={self._enabled}，dry_run={self._dry_run}，"
            f"onlyonce={self._onlyonce}，cron={self._cron or '未设置'}，来源映射={len(self._source_mapping_list())} 个"
        )

        if self._onlyonce:
            logger.info("【115云端媒体整理】已安排立即运行任务，约 3 秒后触发")
            self._scheduler = BackgroundScheduler(timezone=settings.TZ)
            self._scheduler.add_job(
                func=self.auto_run,
                trigger="date",
                run_date=datetime.now(tz=pytz.timezone(settings.TZ)) + timedelta(seconds=3),
                name="115云端媒体整理立即运行",
            )
            self._scheduler.start()
            self._onlyonce = False
            config["onlyonce"] = False
            self.update_config(config=config)

    def get_state(self) -> bool:
        return bool(self._enabled)

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        return []

    def get_api(self) -> List[Dict[str, Any]]:
        return [
            {"path": "/dry_run_movie", "endpoint": self.dry_run_movie, "methods": ["POST"], "auth": "bear", "summary": "生成电影整理计划"},
            {"path": "/dry_run_tv", "endpoint": self.dry_run_tv, "methods": ["POST"], "auth": "bear", "summary": "生成电视剧整理计划"},
            {"path": "/dry_run_all", "endpoint": self.dry_run_all, "methods": ["POST"], "auth": "bear", "summary": "生成全部整理计划"},
            {"path": "/execute_last_plan", "endpoint": self.execute_last_plan, "methods": ["POST"], "auth": "bear", "summary": "执行最近一次整理计划"},
            {"path": "/history", "endpoint": self.history, "methods": ["GET"], "auth": "bear", "summary": "查询整理历史"},
            {"path": "/clear_history", "endpoint": self.clear_history, "methods": ["POST"], "auth": "bear", "summary": "清空整理历史"},
            {"path": "/resolve_path", "endpoint": self.resolve_path_api, "methods": ["POST"], "auth": "bear", "summary": "解析115路径"},
            {"path": "/list_dir", "endpoint": self.list_dir_api, "methods": ["POST"], "auth": "bear", "summary": "列出115目录"},
        ]

    def get_service(self) -> List[Dict[str, Any]]:
        if not self.get_state() or not self._cron:
            return []
        return [{
            "id": f"{self.__class__.__name__}.AutoRun",
            "name": "115云端媒体整理",
            "trigger": CronTrigger.from_crontab(self._cron),
            "func": self.auto_run,
            "kwargs": {},
        }]

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        return [{
            "component": "VForm",
            "content": [
                self._form_hint("基础设置"),
                self._row([
                    self._col(self._switch("enabled", "启用插件"), 3),
                    self._col(self._switch("notify", "发送通知"), 3),
                    self._col(self._switch("onlyonce", "立即运行一次"), 3),
                    self._col(self._switch("dry_run", "仅生成计划"), 3),
                ]),
                self._row([
                    self._col(self._text("cron", "CRON表达式"), 12),
                ]),
                self._form_hint("执行策略"),
                self._row([
                    self._col(self._switch("delete_empty_source_dirs", "删除空源目录"), 4),
                    self._col(self._select("conflict_strategy", "重名策略", [{"title": "跳过", "value": "skip"}, {"title": "自动后缀", "value": "rename_with_suffix"}]), 4),
                    self._col(self._select("unrecognized_action", "未识别处理", [{"title": "跳过", "value": "skip"}, {"title": "移动到未识别", "value": "move_to_unrecognized"}]), 4),
                ]),
                self._row([
                    self._col(self._text("max_depth", "最大扫描深度"), 4),
                    self._col(self._text("max_items_per_run", "单次最多处理"), 4),
                    self._col(self._text("min_file_size_mb", "最小文件大小MB"), 4),
                ]),
                self._row([
                    self._col(self._text("batch_size", "批大小"), 4),
                    self._col(self._text("sleep_between_batches", "批间隔秒"), 4),
                    self._col(self._text("history_limit", "历史保留条数"), 4),
                ]),
                self._form_hint("115 连接"),
                self._row([
                    self._col(self._text("cookie_path", "115 Cookie文件路径"), 12),
                ]),
                self._row([
                    self._col(self._textarea("cookie_text", "115 Cookie文本（文件不可用时兜底）", rows=3), 12),
                ]),
                self._form_hint("目录配置：填写115路径即可；target_root_path 下的分类目录需与 MoviePilot 分类一致"),
                self._row([self._col(self._textarea("source_mappings", "来源与目标路径映射JSON", rows=8), 12)]),
                self._row([self._col(self._textarea("target_cids", "目标CID JSON（高级覆盖；路径模式通常保持默认）", rows=8), 12)]),
                self._form_hint("高级选项"),
                self._row([self._col(self._textarea("exclude_keywords", "排除关键词，逗号分隔", rows=2), 12)]),
                self._row([self._col(self._textarea("category_mapping", "分类别名映射JSON（可选）", rows=5), 12)]),
            ],
        }], self._default_config()

    def get_page(self) -> List[dict]:
        last_plan = self.get_data("last_plan") or []
        last_result = self.get_data("last_result") or {}
        history = self.get_data("history") or []
        p115 = self._p115_ops()
        status = "p115client可用" if p115.available else p115.import_error or "p115client不可用"
        plan_summary = self._count_by(last_plan, "status")
        plan_rows = [[
            item.get("media_type"),
            item.get("source_name"),
            item.get("target_category"),
            item.get("target_path"),
            item.get("status"),
            "；".join(item.get("warnings") or []),
        ] for item in last_plan[:50]]
        mapping_rows = [[
            item.get("name"),
            item.get("media_type"),
            item.get("source_path"),
            item.get("target_root_path"),
        ] for item in self._source_mapping_list()]
        error_rows = [[item.get("source"), item.get("error")] for item in (last_result.get("errors") or [])[:20]]
        history_rows = [[
            item.get("time"),
            item.get("source_name"),
            item.get("target_category"),
            item.get("target_name"),
            item.get("status"),
            item.get("error"),
        ] for item in list(reversed(history))[:50]]
        cleaned_dirs = last_result.get("cleaned_empty_dirs") or []
        return [{
            "component": "VContainer",
            "content": [
                {"component": "VAlert", "props": {"type": "info", "variant": "tonal", "text": f"{status}；dry_run：{self._dry_run}"}},
                self._section("来源映射", self._table(["名称", "类型", "来源路径", "目标根路径"], mapping_rows)),
                {"component": "VAlert", "props": {"type": "success", "variant": "tonal", "text": f"最近计划 {len(last_plan)} 条：planned {plan_summary.get('planned', 0)}，executed {plan_summary.get('executed', 0)}，failed {plan_summary.get('failed', 0)}，skipped {plan_summary.get('skipped', 0)}；展示前 {min(50, len(last_plan))} 条"}},
                self._section("最近计划", self._table(["类型", "源文件", "目标分类", "目标路径", "状态", "警告"], plan_rows)),
                {"component": "VAlert", "props": {"type": "warning" if last_result.get("failed", 0) else "success", "variant": "tonal", "text": f"最近执行：总计 {last_result.get('total', 0)}，成功 {last_result.get('success', 0)}，失败 {last_result.get('failed', 0)}，跳过 {last_result.get('skipped', 0)}，清理空目录 {len(cleaned_dirs)}；历史 {len(history)} 条"}},
                self._section("失败项", self._table(["源文件", "错误"], error_rows)) if error_rows else {"component": "div"},
                self._section("最近历史", self._table(["时间", "源文件", "目标分类", "目标名称", "状态", "错误"], history_rows)),
            ],
        }]

    def stop_service(self):
        try:
            if self._scheduler:
                self._scheduler.remove_all_jobs()
                if self._scheduler.running:
                    self._scheduler.shutdown()
                self._scheduler = None
        except Exception as err:
            logger.warning(f"停止115云端媒体整理服务失败：{err}")

    def dry_run_movie(self):
        return self._dry_run_for("movie")

    def dry_run_tv(self):
        return self._dry_run_for("tv")

    def dry_run_all(self):
        sources = self._source_mapping_list()
        logger.info(f"【115云端媒体整理】开始 dry-run：来源 {len(sources)} 个")
        plan = []
        for source in sources:
            response = self._dry_run_source(source, save=False)
            if not response.success:
                return response
            plan.extend(response.data or [])
        self.save_data("last_plan", plan)
        logger.info(f"【115云端媒体整理】dry-run 完成：计划 {len(plan)} 条")
        return schemas.Response(success=True, message=f"已生成整理计划：{len(plan)} 条", data=plan)

    def execute_last_plan(self):
        guard = self._execute_guard()
        if guard:
            return guard
        plan = self.get_data("last_plan") or []
        logger.info(f"【115云端媒体整理】开始执行 last_plan：计划 {len(plan)} 条")
        result = ExecuteResult(plan_id=plan[0].get("plan_id") if plan else "", total=len(plan))
        p115 = self._p115_ops()
        history = self.get_data("history") or []
        for item in plan:
            if item.get("action") == "skip" or item.get("status") == "skipped":
                result.skipped += 1
                continue
            try:
                outcome = p115.execute_move(item, conflict_strategy=self._conflict_strategy)
                if outcome.get("success"):
                    result.success += 1
                    logger.info(f"【115云端媒体整理】执行成功：{item.get('source_name')} -> {item.get('target_path')}")
                    item["status"] = "executed"
                    history.append(self._history_record(item, "executed", ""))
                elif outcome.get("skipped"):
                    result.skipped += 1
                    logger.info(f"【115云端媒体整理】执行跳过：{item.get('source_name')}，原因：{outcome.get('message')}")
                    item["status"] = "skipped"
                    item["error"] = outcome.get("message")
                else:
                    result.failed += 1
                    logger.info(f"【115云端媒体整理】执行失败：{item.get('source_name')}，原因：{outcome.get('message')}")
                    item["status"] = "failed"
                    item["error"] = outcome.get("message")
                    result.errors.append({"source": item.get("source_name"), "error": item.get("error")})
            except Exception as err:
                result.failed += 1
                logger.info(f"【115云端媒体整理】执行异常：{item.get('source_name')}，原因：{err}")
                item["status"] = "failed"
                item["error"] = str(err)
                result.errors.append({"source": item.get("source_name"), "error": str(err)})
            time.sleep(max(0.0, self._sleep_between_batches))
        cleaned_dirs = []
        if self._delete_empty_source_dirs:
            cleaned_dirs = self._cleanup_empty_source_dirs(p115)
            result_dict = result.to_dict()
            result_dict["cleaned_empty_dirs"] = cleaned_dirs
        else:
            result_dict = result.to_dict()
        history = history[-max(1, self._history_limit):]
        self.save_data("history", history)
        self.save_data("last_plan", plan)
        self.save_data("last_result", result_dict)
        logger.info(
            f"【115云端媒体整理】执行完成：总计 {result.total}，成功 {result.success}，"
            f"失败 {result.failed}，跳过 {result.skipped}，清理空目录 {len(cleaned_dirs)}"
        )
        self._notify_summary("执行完成", result_dict)
        return schemas.Response(success=result.failed == 0, message=f"执行完成：成功 {result.success}，失败 {result.failed}，跳过 {result.skipped}，清理空目录 {len(cleaned_dirs)}", data=result_dict)

    def history(self):
        return schemas.Response(success=True, data=self.get_data("history") or [])

    def clear_history(self):
        self.save_data("history", [])
        return schemas.Response(success=True, message="历史已清空")

    def resolve_path_api(self, data: dict = None):
        path = str((data or {}).get("path") or "").strip()
        if not path:
            return schemas.Response(success=False, message="path不能为空")
        p115 = self._p115_ops()
        if not p115.available:
            return schemas.Response(success=False, message=p115.import_error or "p115client不可用")
        try:
            return schemas.Response(success=True, data={"path": path, "cid": p115.resolve_path(path)})
        except Exception as err:
            return schemas.Response(success=False, message=str(err))

    def list_dir_api(self, data: dict = None):
        path = str((data or {}).get("path") or "").strip()
        cid = str((data or {}).get("cid") or "").strip()
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

    def auto_run(self):
        logger.info(f"【115云端媒体整理】自动运行开始：dry_run={self._dry_run}")
        response = self.dry_run_all()
        if not response.success:
            logger.info(f"【115云端媒体整理】自动运行失败：{response.message}")
            self._notify_text("115云端媒体整理", response.message)
            return
        if not self._dry_run:
            self.execute_last_plan()
        else:
            logger.info(f"【115云端媒体整理】自动运行 dry-run 完成：计划 {len(response.data or [])} 条")
            self._notify_text("115云端媒体整理", f"dry-run完成，计划 {len(response.data or [])} 条")

    def _dry_run_for(self, media_type: str, save: bool = True):
        logger.info(f"【115云端媒体整理】开始 {media_type} dry-run")
        plan = []
        for source in self._source_mapping_list():
            if source.get("media_type") != media_type:
                continue
            response = self._dry_run_source(source, save=False)
            if not response.success:
                return response
            plan.extend(response.data or [])
        if save:
            self.save_data("last_plan", plan)
        logger.info(f"【115云端媒体整理】{media_type} dry-run 完成：计划 {len(plan)} 条")
        return schemas.Response(success=True, message=f"已生成{media_type}整理计划：{len(plan)} 条", data=plan)

    def _dry_run_source(self, source: Dict[str, Any], save: bool = True):
        try:
            p115 = self._p115_ops()
            if not p115.available:
                logger.info(f"【115云端媒体整理】p115client不可用：{p115.import_error}")
                return schemas.Response(success=False, message=p115.import_error or "p115client不可用")
            media_type = str(source.get("media_type") or "").lower()
            source_cid = str(source.get("source_cid") or "")
            source_path = str(source.get("source_path") or source_cid)
            logger.info(f"【115云端媒体整理】开始扫描来源：类型={media_type}，路径={source_path}")
            if not source_cid and source_path:
                source_cid = p115.resolve_path(source_path)
                source = dict(source, source_cid=source_cid)
                logger.info(f"【115云端媒体整理】来源路径解析成功：{source_path} -> {source_cid}")
            target_cids = self._current_target_cids(p115=p115)
            if media_type not in ("movie", "tv") or not source_cid:
                return schemas.Response(success=False, message=f"来源映射无效：{source}")
            items = p115.walk_media_items(
                source_cid=source_cid,
                source_path=source_path,
                max_depth=max(0, self._max_depth),
                min_file_size=max(0, self._min_file_size_mb) * 1024 * 1024,
                exclude_keywords=self._exclude_list(),
                max_items=max(0, self._max_items_per_run),
            )
            logger.info(f"【115云端媒体整理】来源扫描完成：{source_path}，候选视频 {len(items)} 个")
            mapper = CategoryMapper(self._category_mapping_dict())
            planner = Planner(mapper, target_cids)
            plan = planner.build_plans(
                media_type,
                items,
                self._config_snapshot(),
                self.get_data("history") or [],
                self._unrecognized_action,
                source_root_cid=source_cid,
            )
            if save:
                self.save_data("last_plan", plan)
            logger.info(f"【115云端媒体整理】来源计划生成完成：{source_path}，计划 {len(plan)} 条")
            return schemas.Response(success=True, message=f"已生成{media_type}整理计划：{len(plan)} 条", data=plan)
        except Exception as err:
            logger.exception(f"生成115整理计划失败：{err}")
            return schemas.Response(success=False, message=str(err))

    def _execute_guard(self):
        if self._dry_run:
            return schemas.Response(success=False, message="当前仍为dry_run=true，禁止执行移动")
        plan = self.get_data("last_plan") or []
        if not plan:
            return schemas.Response(success=False, message="没有可执行的last_plan")
        snapshot = self._config_snapshot()
        for item in plan:
            if item.get("config_snapshot") != snapshot:
                return schemas.Response(success=False, message="last_plan配置快照与当前配置不一致，请重新dry-run")
        p115 = self._p115_ops()
        if not p115.available:
            return schemas.Response(success=False, message=p115.import_error or "p115client不可用")
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

    def _current_target_cids(self, p115: P115Ops = None) -> Dict[str, Dict[str, str]]:
        target_cids = self._target_cids_dict()
        resolved = {
            "movie": dict(target_cids.get("movie", {})),
            "tv": dict(target_cids.get("tv", {})),
            "unrecognized": target_cids.get("unrecognized", ""),
        }
        self._resolve_target_paths(resolved, p115=p115)
        return resolved


    def _category_mapping_dict(self) -> Dict[str, Dict[str, str]]:
        try:
            data = json.loads(self._category_mapping or "{}")
            return data if isinstance(data, dict) else DEFAULT_CATEGORY_MAPPING
        except Exception:
            return DEFAULT_CATEGORY_MAPPING

    def _target_cids_dict(self) -> Dict[str, Any]:
        try:
            data = json.loads(self._target_cids or "{}")
            if not isinstance(data, dict):
                return DEFAULT_TARGET_CIDS
            return data if ("movie" in data or "tv" in data) else DEFAULT_TARGET_CIDS
        except Exception:
            return DEFAULT_TARGET_CIDS

    def _source_mapping_list(self) -> List[Dict[str, str]]:
        try:
            data = json.loads(self._source_mappings or "[]")
            mappings = data if isinstance(data, list) else []
        except Exception:
            mappings = []
        if not mappings:
            mappings = DEFAULT_SOURCE_MAPPINGS
        normalized = []
        for item in mappings:
            if not isinstance(item, dict):
                continue
            media_type = str(item.get("media_type") or "").lower()
            source_path = str(item.get("source_path") or "").strip()
            target_root_path = str(item.get("target_root_path") or "").strip()
            if media_type not in ("movie", "tv") or not source_path or not target_root_path:
                continue
            normalized.append({
                "name": str(item.get("name") or source_path),
                "media_type": media_type,
                "source_path": source_path,
                "target_root_path": target_root_path,
            })
        return normalized

    def _resolve_target_paths(self, target_cids: Dict[str, Any], p115: P115Ops = None):
        for source in self._source_mapping_list():
            media_type = source.get("media_type")
            target_root_path = source.get("target_root_path")
            if media_type not in ("movie", "tv") or not target_root_path:
                continue
            if p115 is None:
                p115 = self._p115_ops()
            if not p115.available:
                return
            for category in list(target_cids.get(media_type, {}).keys()):
                if target_cids[media_type].get(category):
                    continue
                try:
                    target_cids[media_type][category] = p115.resolve_path(f"{target_root_path.rstrip('/')}/{category}")
                except Exception:
                    pass

    def _cleanup_empty_source_dirs(self, p115: P115Ops) -> List[str]:
        cleaned = []
        source_roots = set()
        for source in self._source_mapping_list():
            source_cid = source.get("source_cid")
            source_path = source.get("source_path")
            if not source_cid and source_path:
                try:
                    source_cid = p115.resolve_path(source_path)
                except Exception as err:
                    logger.warning(f"解析115来源路径失败 {source_path}: {err}")
                    continue
            if source_cid:
                source_roots.add(source_cid)
        logger.info(f"【115云端媒体整理】开始清理空来源目录：来源根 {len(source_roots)} 个")
        for source_cid in source_roots:
            for empty_cid in p115.list_empty_dirs_bottom_up(source_cid, max(0, self._max_depth) + 2):
                try:
                    p115.delete(empty_cid)
                    cleaned.append(empty_cid)
                    logger.info(f"【115云端媒体整理】已删除空来源目录：{empty_cid}")
                except Exception as err:
                    logger.warning(f"删除115空源目录失败 {empty_cid}: {err}")
        logger.info(f"【115云端媒体整理】空来源目录清理完成：{len(cleaned)} 个")
        return cleaned

    def _exclude_list(self) -> List[str]:
        return [item.strip() for item in self._exclude_keywords.split(",") if item.strip()]

    def _p115_ops(self) -> P115Ops:
        return P115Ops(cookie_path=self._cookie_path, cookie_text=self._cookie_text)

    def _notify_summary(self, title: str, result: Dict[str, Any]):
        text = f"计划 {result.get('total', 0)} 条，成功 {result.get('success', 0)}，失败 {result.get('failed', 0)}，跳过 {result.get('skipped', 0)}"
        errors = result.get("errors") or []
        if errors:
            text += "\n" + "\n".join([f"{item.get('source')}: {item.get('error')}" for item in errors[:5]])
        self._notify_text(title, text)

    def _notify_text(self, title: str, text: str):
        if self._notify:
            self.post_message(mtype=NotificationType.Plugin, title=title, text=text)

    @staticmethod
    def _history_record(item: Dict[str, Any], status: str, error: str) -> Dict[str, Any]:
        return {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "item_id": item.get("item_id"),
            "source_fid": item.get("source_fid"),
            "source_cid": item.get("source_cid"),
            "source_name": item.get("source_name"),
            "target_category": item.get("target_category"),
            "target_name": item.get("target_name"),
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
            "max_depth": 5,
            "max_items_per_run": 200,
            "min_file_size_mb": 100,
            "batch_size": 30,
            "sleep_between_batches": 1.0,
            "conflict_strategy": "skip",
            "unrecognized_action": "skip",
            "cookie_path": "/config/115-cookies.txt",
            "cookie_text": "",
            "source_mappings": json.dumps(DEFAULT_SOURCE_MAPPINGS, ensure_ascii=False, indent=2),
            "exclude_keywords": "sample,trailer,花絮,预告",
            "category_mapping": json.dumps(DEFAULT_CATEGORY_MAPPING, ensure_ascii=False, indent=2),
            "target_cids": json.dumps(DEFAULT_TARGET_CIDS, ensure_ascii=False, indent=2),
            "history_limit": 1000,
        }

    @staticmethod
    def _safe_int(value: Any, default: int) -> int:
        try:
            return int(value)
        except Exception:
            return default

    @staticmethod
    def _safe_float(value: Any, default: float) -> float:
        try:
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _switch(model: str, label: str) -> Dict[str, Any]:
        return {"component": "VSwitch", "props": {"model": model, "label": label}}

    @staticmethod
    def _text(model: str, label: str) -> Dict[str, Any]:
        return {"component": "VTextField", "props": {"model": model, "label": label}}

    @staticmethod
    def _select(model: str, label: str, items: List[Dict[str, str]]) -> Dict[str, Any]:
        return {"component": "VSelect", "props": {"model": model, "label": label, "items": items}}

    @staticmethod
    def _textarea(model: str, label: str, rows: int = 4) -> Dict[str, Any]:
        return {"component": "VTextarea", "props": {"model": model, "label": label, "rows": rows}}

    @staticmethod
    def _col(component: Dict[str, Any], md: int = 12) -> Dict[str, Any]:
        return {"component": "VCol", "props": {"cols": 12, "md": md}, "content": [component]}

    @staticmethod
    def _row(cols: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {"component": "VRow", "content": cols}

    @staticmethod
    def _form_hint(text: str) -> Dict[str, Any]:
        return {
            "component": "VAlert",
            "props": {"type": "info", "variant": "tonal", "density": "compact", "class": "mb-2", "text": text},
        }

    @staticmethod
    def _count_by(items: List[Dict[str, Any]], key: str) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for item in items:
            value = str(item.get(key) or "")
            counts[value] = counts.get(value, 0) + 1
        return counts

    @staticmethod
    def _section(title: str, content: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "component": "VCard",
            "props": {"variant": "tonal", "class": "mb-3"},
            "content": [
                {"component": "VCardTitle", "text": title},
                {"component": "VCardText", "content": [content]},
            ],
        }

    @staticmethod
    def _table(headers: List[str], rows: List[List[Any]]) -> Dict[str, Any]:
        if not rows:
            return {"component": "VAlert", "props": {"type": "info", "variant": "tonal", "text": "暂无数据"}}
        return {
            "component": "VTable",
            "props": {"density": "compact"},
            "content": [
                {"component": "thead", "content": [{"component": "tr", "content": [{"component": "th", "text": header} for header in headers]}]},
                {"component": "tbody", "content": P115MediaOrganizer._table_rows(rows)},
            ],
        }

    @staticmethod
    def _table_rows(rows: List[List[str]]) -> List[Dict[str, Any]]:
        content = []
        for row in rows:
            content.append({"component": "tr", "content": [{"component": "td", "text": str(cell or "")} for cell in row]})
        return content
