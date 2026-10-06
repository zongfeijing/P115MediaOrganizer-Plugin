from __future__ import annotations

import ast
import json
import sys
import threading
import time
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from .test_plugin import (
    PLUGIN_DIR,
    category_mapper,
    execution_module,
    load_module,
    models,
    planner_module,
    p115_ops_module,
)

configuration = load_module("configuration")
task_state = load_module("task_state")


class Response:
    def __init__(self, success=True, message="", data=None):
        self.success, self.message, self.data = success, message, data


class HttpError(Exception):
    def __init__(self, status, detail):
        self.status_code, self.detail = status, detail


# Execute the production class/mixin with narrow host stubs. No MoviePilot process or database is imported.
ns = {
    "schemas": SimpleNamespace(Response=Response),
    "Request": object,
    "HTTPException": HttpError,
    "check_configuration": configuration.check_configuration,
    "connection_mode": configuration.connection_mode,
    "executable_plan_items": execution_module.executable_plan_items,
    "validate_plan": execution_module.validate_plan,
    "TaskCancelled": task_state.TaskCancelled,
}
usability_tree = ast.parse((PLUGIN_DIR / "usability.py").read_text())
usability_tree.body = [
    n
    for n in usability_tree.body
    if not isinstance(n, ast.ImportFrom)
    or (n.module in ("__future__", "collections", "importlib.metadata"))
]
exec(compile(usability_tree, "usability.py", "exec"), ns)


class Base:
    def __init__(self):
        self.data, self.config = {}, {}

    def get_data(self, key):
        return self.data.get(key)

    def save_data(self, key, value):
        self.data[key] = value

    def get_config(self):
        return self.config

    def update_config(self, config):
        self.config = config


class Cron:
    @staticmethod
    def from_crontab(value):
        if len(value.split()) != 5:
            raise ValueError("invalid cron")
        return value


ns.update(
    _PluginBase=Base,
    TaskState=task_state.TaskState,
    P115Ops=p115_ops_module.P115Ops,
    P115UnavailableError=p115_ops_module.P115UnavailableError,
    DEFAULT_CATEGORY_MAPPING=category_mapper.DEFAULT_CATEGORY_MAPPING,
    CategoryMapper=category_mapper.CategoryMapper,
    Planner=planner_module.Planner,
    ExecuteResult=models.ExecuteResult,
    ANTI_BLOCK_DEFAULTS=p115_ops_module.ANTI_BLOCK_DEFAULTS,
    BATCH_RENAME_MAX=p115_ops_module.BATCH_RENAME_MAX,
    CronTrigger=Cron,
    source_contains_target=execution_module.source_contains_target,
    source_entry_matches_plan=execution_module.source_entry_matches_plan,
    resolve_target_cids_for_source=execution_module.resolve_target_cids_for_source,
    compute_batch_group_key=planner_module.compute_batch_group_key,
    parse_json=configuration.parse_json,
    logger=SimpleNamespace(info=Mock(), warning=Mock(), error=Mock()),
)
main_tree = ast.parse((PLUGIN_DIR / "__init__.py").read_text())
main_tree.body = [
    n
    for n in main_tree.body
    if not isinstance(n, ast.ImportFrom)
    or n.module in ("datetime", "pathlib", "html", "typing", "uuid")
]
exec(compile(main_tree, "__init__.py", "exec"), ns)
Plugin = ns["P115MediaOrganizer"]
SOURCES = [
    {
        "name": "Movies",
        "media_type": "movie",
        "source_path": "/incoming/movie",
        "target_root_path": "/library/movie",
    },
    {
        "name": "TV",
        "media_type": "tv",
        "source_path": "/incoming/tv",
        "target_root_path": "/library/tv",
    },
]


def plugin():
    p = Plugin()
    p.config = {
        **p._default_config(),
        "source_mappings": json.dumps(SOURCES),
        "cookie_mode": "text",
        "cookie_text": "fake",
    }
    p._effective_config = p.config
    p._source_mappings = p.config["source_mappings"]
    p._cookie_mode = "text"
    p._cookie_text = "fake"
    p._notify_summary = Mock()
    return p


def plan(p, count=2):
    return [
        {
            "plan_id": "shared",
            "item_id": f"file-{i}",
            "status": "planned",
            "action": "move",
            "source_name": f"a-{i}.mkv",
            "target_root_path": "/library/movie",
            "target_category": "华语电影",
            "target_path": f"/library/movie/a-{i}.mkv",
            "created_at_epoch": time.time(),
            "config_snapshot": p._config_snapshot(),
        }
        for i in range(count)
    ]


class ConfigurationTest(unittest.TestCase):
    def test_invalid_empty_and_incomplete_never_use_sample_paths(self):
        for value in (
            "[{invalid}]",
            "[]",
            json.dumps([{"media_type": "movie", "source_path": "/in"}]),
        ):
            p = plugin()
            p._source_mappings = value
            p._effective_config["source_mappings"] = value
            self.assertFalse(p.validate_config_api().success)
            self.assertEqual(p._source_mapping_list(), [])

    def test_cross_source_target_is_rejected(self):
        rows = [dict(r) for r in SOURCES]
        rows[1]["target_root_path"] = "/incoming/movie/TV"
        result = configuration.check_configuration({"source_mappings": rows})
        self.assertFalse(result.valid)
        self.assertTrue(any("任何来源" in e for e in result.errors))

    def test_root_traversal_duplicates_and_invalid_nested_json_rejected(self):
        for path in ("/", "relative", "/a/../b"):
            rows = [{**SOURCES[0], "source_path": path}]
            self.assertFalse(
                configuration.check_configuration({"source_mappings": rows}).valid
            )
        self.assertFalse(
            configuration.check_configuration(
                {"source_mappings": [SOURCES[0], SOURCES[0]]}
            ).valid
        )
        self.assertFalse(
            configuration.check_configuration(
                {"source_mappings": SOURCES, "target_cids": "bad"}
            ).valid
        )
        self.assertFalse(
            configuration.check_configuration(
                {"source_mappings": SOURCES, "category_mapping": {"movie": []}}
            ).valid
        )

    def test_legacy_text_first_and_explicit_file_choice(self):
        self.assertEqual(
            configuration.connection_mode({"cookie_text": "legacy"}), "text"
        )
        self.assertEqual(
            configuration.connection_mode(
                {"cookie_text": "legacy", "cookie_mode": "file"}
            ),
            "file",
        )
        p = plugin()
        p._cookie_mode = "file"
        p._cookie_path = "/config/cookies"
        factory = Mock()
        with patch.dict(ns, {"P115Ops": factory}):
            p._p115_ops()
        self.assertEqual(factory.call_args.kwargs["cookie_text"], "")
        self.assertEqual(factory.call_args.kwargs["cookie_path"], "/config/cookies")


class PlanWorkflowTest(unittest.TestCase):
    def test_multi_source_plan_has_one_id_and_complete_path(self):
        media = SimpleNamespace(
            title="Example", year=2026, library_category="华语电影", category="华语电影"
        )
        p = plugin()
        p._p115_ops = Mock(return_value=SimpleNamespace(available=True))

        def scan(source, **kwargs):
            planner = planner_module.Planner(
                category_mapper.CategoryMapper(),
                {"movie": {"华语电影": "42"}, "tv": {"华语电影": "43"}},
            )
            planner._recognize = lambda *_: (
                media,
                SimpleNamespace(begin_season=1, begin_episode=1),
            )
            planner._media_identity = lambda _: ("tmdb", "88")
            planner._moviepilot_rename_path = lambda *_args, **_kwargs: (
                "Example (2026)/Example.mkv"
            )
            item = models.MediaItem(
                source["name"],
                None,
                "Example.mkv",
                ".mkv",
                1000,
                False,
                "10",
                source["source_path"] + "/Example.mkv",
            )
            return Response(
                data=planner.build_plans(
                    source["media_type"],
                    [item],
                    p._config_snapshot(),
                    [],
                    plan_id=p._scan_plan_id,
                    target_root_path=source["target_root_path"],
                )
            )

        p._dry_run_source = scan
        response = p.dry_run_all()
        self.assertTrue(response.success)
        self.assertEqual(len({r["plan_id"] for r in response.data}), 1)
        self.assertTrue(
            execution_module.validate_plan(
                response.data, p._config_snapshot(), 24
            ).valid
        )
        self.assertTrue(response.data[0]["target_path"].startswith("/library/movie/"))

    def test_failed_new_scan_invalidates_old_plan(self):
        p = plugin()
        p.save_data("last_plan", plan(p))
        p._dry_run_source = lambda *_args, **_kwargs: Response(
            success=False, message="bad path"
        )
        self.assertFalse(p.dry_run_all().success)
        self.assertEqual(p.get_data("last_plan"), [])
        self.assertFalse(p.get_data("scan_summary")["completed"])

    def test_unrecognized_and_history_duplicates_are_visible(self):
        planner = planner_module.Planner(
            category_mapper.CategoryMapper(), {"movie": {}, "tv": {}}
        )
        planner._recognize = lambda *_: (None, None)
        planner._media_identity = lambda _: (None, None)
        item = models.MediaItem(
            "f1", None, "unknown.mkv", ".mkv", 1000, False, "10", "/in/unknown.mkv"
        )
        for history in (
            [],
            [{"item_id": planner._item_key(item), "status": "executed"}],
        ):
            rows = planner.build_plans("movie", [item], {}, history)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["status"], "skipped")
            self.assertTrue(rows[0]["warnings"])
            self.assertEqual(execution_module.executable_plan_items(rows), [])

    def test_scan_reports_filter_reasons_and_stops_on_checkpoint(self):
        ops = object.__new__(p115_ops_module.P115Ops)
        entries = [
            {"fid": "1", "n": "notes.txt", "s": 2000},
            {"fid": "2", "n": "small.mkv", "s": 1},
            {"fid": "3", "n": "sample.mkv", "s": 2000},
            {"fid": "4", "n": "movie.mkv", "s": 2000},
        ]
        ops.iter_entries = lambda _cid: iter(entries)
        records = []
        rows = ops.walk_media_items(
            "0",
            "/in",
            2,
            min_file_size=100,
            exclude_keywords=["sample"],
            report=records.append,
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(
            {r["reason"] for r in records},
            {"非视频文件", "文件小于最小体积", "匹配排除关键词"},
        )
        task = task_state.TaskState()
        task.reserve("scan")
        task.request_stop()
        with self.assertRaises(task_state.TaskCancelled):
            ops.walk_media_items("0", "/in", 2, checkpoint=task.checkpoint)

    def test_stop_execution_preserves_finished_outcomes_and_remaining(self):
        p = plugin()
        p._batch_size = 1
        p.save_data("last_plan", plan(p, 3))
        p._p115_ops = Mock(return_value=SimpleNamespace(available=True))
        p._task.reserve("execute")
        p._task_owner_thread = threading.get_ident()

        def group(_ops, chunk, runid, history, run_history, result, success):
            p._record_outcome(
                chunk[0], "executed", "", runid, history, run_history, result, success
            )
            p._task.request_stop()

        p._execute_group = group
        p._cleanup_empty_source_dirs = Mock()
        p._refresh_plex_after_success = Mock()
        response = p._execute_last_plan(allow_dry_run=True)
        self.assertTrue(response.data["cancelled"])
        self.assertEqual(response.data["success"], 1)
        self.assertEqual(response.data["remaining"], 2)
        self.assertEqual(p.get_data("last_plan")[0]["status"], "executed")
        self.assertEqual(len(p.get_data("history")), 1)
        p._cleanup_empty_source_dirs.assert_not_called()
        p._refresh_plex_after_success.assert_not_called()


class ConfirmationTest(unittest.TestCase):
    def setUp(self):
        self.p = plugin()
        self.p.save_data("last_plan", plan(self.p))
        self.p._p115_ops = Mock(return_value=SimpleNamespace(available=True))
        self.p._require_admin_session = Mock()
        self.p._submit_task = Mock(return_value=Response(success=True))

    def test_manual_confirmation_is_one_use_and_does_not_change_scheduled_mode(self):
        receipt = self.p.prepare_execute_api(None)
        self.assertTrue(receipt.success)
        self.assertEqual(receipt.data["count"], 2)
        self.assertTrue(
            self.p.confirm_execute_api(None, {"token": receipt.data["token"]}).success
        )
        self.assertFalse(
            self.p.confirm_execute_api(None, {"token": receipt.data["token"]}).success
        )
        self.p._submit_task.assert_called_once_with("execute")
        self.assertTrue(self.p._dry_run)

    def test_plan_change_and_expiry_invalidate_confirmation(self):
        for mutate in ("plan", "expiry"):
            receipt = self.p.prepare_execute_api(None)
            if mutate == "plan":
                self.p.get_data("last_plan")[0]["target_path"] = "/changed"
            else:
                self.p._confirmation["expires_at"] = 0
            self.assertFalse(
                self.p.confirm_execute_api(
                    None, {"token": receipt.data["token"]}
                ).success
            )
        self.p._submit_task.assert_not_called()

    def test_busy_session_cannot_issue_confirmation(self):
        self.p._task.reserve("scan")
        self.assertFalse(self.p.prepare_execute_api(None).success)

    def test_api_key_is_not_manual_confirmation(self):
        security = types.ModuleType("app.sdk.security")
        security.decode_access_token = Mock(side_effect=ValueError("invalid token"))
        with patch.dict(sys.modules, {"app.sdk.security": security}):
            with self.assertRaises(HttpError):
                ns["UsabilityMixin"]._require_admin_session(
                    SimpleNamespace(headers={"Authorization": "Bearer invalid"})
                )
            with self.assertRaises(HttpError):
                ns["UsabilityMixin"]._require_admin_session(
                    SimpleNamespace(headers={"X-API-KEY": "key"})
                )

    def test_secret_fields_not_in_records_or_workflow(self):
        self.p.get_data("last_plan")[0]["cookie_text"] = "SHOULD_NOT_APPEAR"
        rows = self.p.records_api().data
        self.assertNotIn("SHOULD_NOT_APPEAR", json.dumps(rows))
        state = self.p.workflow_status_api().data
        self.assertNotIn("cookie_text", json.dumps(state))

    def test_filters_and_pagination_work_on_all_records(self):
        self.p.save_data(
            "history",
            [
                {
                    "source_name": f"a{i}",
                    "status": "failed" if i % 2 else "executed",
                    "run_id": "batch",
                }
                for i in range(65)
            ],
        )
        rows = self.p.records_api(
            page=2,
            page_size=20,
            kind="history",
            status="failed",
            query="a",
            run_id="batch",
        ).data
        self.assertEqual(rows["pagination"]["total"], 32)
        self.assertEqual(len(rows["items"]), 12)

    def test_task_duplicate_does_not_overwrite_active_state(self):
        state = self.p._task.reserve("scan")
        response = ns["UsabilityMixin"]._submit_task(self.p, "scan")
        self.assertFalse(response.success)
        with self.assertRaises(ValueError):
            self.p._task.reserve("check")
        self.assertEqual(self.p._task.snapshot()["id"], state["id"])


class HealthAndSchedulingTest(unittest.TestCase):
    def test_network_failure_is_not_a_cookie_expiry(self):
        ops = p115_ops_module.P115Ops(cookie_text="fake")
        ops.client = SimpleNamespace(
            fs_index_info=Mock(side_effect=TimeoutError("timeout"))
        )
        ops.import_error = ""
        ops.max_retries = 0
        ops.min_interval = 0
        with patch.object(p115_ops_module.time, "sleep"):
            health = ops.health_check(force=True)
        self.assertIsNone(health["ok"])
        self.assertEqual(health["kind"], "network")
        self.assertNotIn("更新 Cookie", health["message"])

    def test_queued_scan_runs_through_host_scheduler_without_thread_creation(self):
        p = plugin()
        scheduler = types.ModuleType("app.sdk.scheduler")
        jobs = []
        scheduler.add_plugin_once_job = lambda *args, **kwargs: (
            jobs.append(args[2]) or True
        )
        with patch.dict(sys.modules, {"app.sdk.scheduler": scheduler}):
            sdk = sys.modules["app.sdk"]
            with patch.object(sdk, "scheduler", scheduler, create=True):
                p._dry_run_source = lambda source, **kwargs: Response(data=[])
                response = p.start_task_api({"kind": "scan"})
                self.assertTrue(response.success)
                self.assertEqual(p._task.snapshot()["status"], "queued")
                self.assertFalse(p.start_task_api({"kind": "scan"}).success)
                jobs[0]()
        self.assertEqual(p._task.snapshot()["status"], "completed")
        self.assertIsNone(p._task_owner_thread)

    def test_queued_confirmation_rechecks_plan_before_any_mutation(self):
        p = plugin()
        p.save_data("last_plan", plan(p))
        p._task.reserve("execute")
        p._task.update(plan_digest=p._plan_digest(p.get_data("last_plan")))
        p.get_data("last_plan")[0]["target_path"] = "/changed"
        p._execute_last_plan = Mock()
        p._run_background_task()
        self.assertEqual(p._task.snapshot()["status"], "failed")
        p._execute_last_plan.assert_not_called()

    def test_invalid_numeric_config_or_json_fails_closed(self):
        p = plugin()
        p._effective_config["batch_size"] = 0
        p._dry_run_source = Mock()
        self.assertFalse(p.dry_run_all().success)
        p._dry_run_source.assert_not_called()
        p._effective_config["batch_size"] = 1
        p._source_mappings = "bad"
        p._effective_config["source_mappings"] = "bad"
        self.assertEqual(p._source_mapping_list(), [])

    def test_json_and_vue_render_do_not_check_network_during_page_load(self):
        p = plugin()
        health = Mock()
        p._ops_instance = SimpleNamespace(
            available=True, import_error="", health_check=health
        )
        page = p.get_page()
        self.assertTrue(page)
        health.assert_not_called()
        self.assertEqual(p.get_render_mode(), ("vue", "dist/assets"))


class AdditionalSafetyTest(unittest.TestCase):
    def test_expired_cookie_blocks_execution_but_network_unknown_does_not_fake_expiry(
        self,
    ):
        p = plugin()
        p.save_data("last_plan", plan(p))
        p._p115_ops = lambda: SimpleNamespace(available=True)
        p.save_data("connection_health", {"kind": "login", "ok": False})
        self.assertFalse(p._execute_guard(allow_dry_run=True).success)
        self.assertFalse(p.workflow_status_api().data["plan"]["valid"])
        p.save_data("connection_health", {"kind": "network", "ok": None})
        self.assertIsNone(p._execute_guard(allow_dry_run=True))

    def test_scan_cancel_invalidates_previous_plan_and_reports_incomplete_scan(self):
        p = plugin()
        p.save_data("last_plan", plan(p))

        def scan(*args, **kwargs):
            p._task.request_stop()
            p._checkpoint()

        p._dry_run_source = scan
        response = p.dry_run_all()
        self.assertFalse(response.success)
        self.assertEqual(p.get_data("last_plan"), [])
        self.assertFalse(p.get_data("scan_summary")["completed"])
        self.assertIn("重新生成", response.message)

    def test_record_pagination_hides_configuration_secrets_and_internal_ids(self):
        p = plugin()
        records = plan(p)
        records[0]["config_snapshot"]["cookie_text"] = "secret-cookie"
        records[0]["source_fid"] = "internal-file-id"
        p.save_data("last_plan", records)
        payload = json.dumps(p.records_api().data)
        self.assertNotIn("secret-cookie", payload)
        self.assertNotIn("internal-file-id", payload)

    def test_zero_scan_limit_remains_supported_for_existing_configurations(self):
        p = plugin()
        p._max_items_per_run = 0
        p._effective_config["max_items_per_run"] = 0
        p._dry_run_source = Mock(return_value=Response(data=[]))
        self.assertTrue(p.dry_run_all().success)
        self.assertEqual(p._dry_run_source.call_count, 2)
        self.assertFalse(p.get_data("scan_summary")["limit_reached"])
