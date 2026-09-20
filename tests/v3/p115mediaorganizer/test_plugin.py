from __future__ import annotations

import ast
import importlib.util
import json
import sys
import types
import unittest
from enum import Enum
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[3]
PLUGIN_DIR = ROOT / "plugins.v3" / "p115mediaorganizer"
PACKAGE_NAME = "p115mediaorganizer_v3_test"


def load_module(name: str):
    package = sys.modules.get(PACKAGE_NAME)
    if package is None:
        package = types.ModuleType(PACKAGE_NAME)
        package.__path__ = [str(PLUGIN_DIR)]
        sys.modules[PACKAGE_NAME] = package
    qualified = f"{PACKAGE_NAME}.{name}"
    spec = importlib.util.spec_from_file_location(qualified, PLUGIN_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[qualified] = module
    assert spec.loader
    spec.loader.exec_module(module)
    return module


models = load_module("models")
category_mapper = load_module("category_mapper")
planner_module = load_module("planner")
execution_module = load_module("execution")

_app_module = sys.modules.setdefault("app", types.ModuleType("app"))
_app_module.__path__ = getattr(_app_module, "__path__", [])
_sdk_module = sys.modules.setdefault("app.sdk", types.ModuleType("app.sdk"))
_sdk_module.__path__ = getattr(_sdk_module, "__path__", [])
_logging_module = types.ModuleType("app.sdk.logging")
_logging_module.logger = SimpleNamespace(
    info=lambda *_args, **_kwargs: None,
    warning=lambda *_args, **_kwargs: None,
    error=lambda *_args, **_kwargs: None,
)
sys.modules.setdefault("app.sdk.logging", _logging_module)
p115_ops_module = load_module("p115_ops")


class MediaSource(Enum):
    TMDB = "tmdb"


class V3ContractTest(unittest.TestCase):
    def test_indexes_select_dedicated_v3_implementation(self):
        v2 = json.loads((ROOT / "package.v2.json").read_text())
        v3 = json.loads((ROOT / "package.v3.json").read_text())
        self.assertIs(v2["P115MediaOrganizer"]["v3"], False)
        self.assertEqual(v3["P115MediaOrganizer"]["version"], "1.2.0")
        self.assertEqual(v3["P115MediaOrganizer"]["system_version"], ">=3.0.0")

    def test_v3_code_does_not_import_legacy_or_internal_host_paths(self):
        forbidden = (
            "app.core",
            "app.helper",
            "app.utils",
            "app.application",
            "app.domain",
            "app.foundation",
            "app.adapters",
            "app.runtime",
        )
        violations = []
        for path in PLUGIN_DIR.glob("*.py"):
            tree = ast.parse(path.read_text(), filename=str(path))
            for node in ast.walk(tree):
                module = None
                if isinstance(node, ast.ImportFrom):
                    module = node.module
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith(forbidden):
                            violations.append(f"{path.name}:{node.lineno}:{alias.name}")
                if module and module.startswith(forbidden):
                    violations.append(f"{path.name}:{node.lineno}:{module}")
        self.assertEqual(violations, [])

    def test_terminal_plan_items_are_not_executed_again(self):
        plan = [
            {"status": "executed", "action": "move"},
            {"status": "skipped", "action": "skip"},
            {"status": "failed", "action": "move"},
            {"status": "planned", "action": "move"},
        ]
        executable = execution_module.executable_plan_items(plan)
        self.assertEqual(executable, plan[2:])

    def test_expired_plan_is_rejected(self):
        snapshot = {"source_mappings": []}
        plan = [{
            "plan_id": "plan-1",
            "status": "planned",
            "action": "move",
            "config_snapshot": snapshot,
            "created_at_epoch": 100.0,
        }]
        result = execution_module.validate_plan(
            plan,
            config_snapshot=snapshot,
            ttl_hours=1,
            now_epoch=3701.0,
        )
        self.assertFalse(result.valid)
        self.assertIn("超过1小时", result.message)

    def test_changed_source_file_is_rejected(self):
        item = {"source_name": "old.mkv", "source_size": 100, "source_is_dir": False}
        renamed = execution_module.source_entry_matches_plan(
            item, current_name="new.mkv", current_size=100
        )
        resized = execution_module.source_entry_matches_plan(
            item, current_name="old.mkv", current_size=101
        )
        self.assertFalse(renamed.valid)
        self.assertFalse(resized.valid)

    def test_target_categories_are_resolved_per_source_root(self):
        target_cids = {"movie": {"外语电影": ""}, "tv": {}, "unrecognized": ""}
        first, _ = execution_module.resolve_target_cids_for_source(
            target_cids,
            {"media_type": "movie", "target_root_path": "/库A"},
            lambda path: f"cid:{path}",
        )
        second, _ = execution_module.resolve_target_cids_for_source(
            target_cids,
            {"media_type": "movie", "target_root_path": "/库B"},
            lambda path: f"cid:{path}",
        )
        self.assertEqual(first["movie"]["外语电影"], "cid:/库A/外语电影")
        self.assertEqual(second["movie"]["外语电影"], "cid:/库B/外语电影")

    def test_streaming_scan_stops_before_loading_later_pages(self):
        calls = []

        class Client:
            @staticmethod
            def fs_files(payload):
                calls.append(payload["offset"])
                start = payload["offset"]
                return {"data": [
                    {"fid": str(start + 1), "n": f"movie-{start + 1}.mkv", "s": 1024},
                    {"fid": str(start + 2), "n": f"movie-{start + 2}.mkv", "s": 1024},
                ]}

        ops = object.__new__(p115_ops_module.P115Ops)
        ops.client = Client()
        ops.import_error = ""
        ops.list_page_size = 2
        ops._last_call_ts = 0.0
        ops.min_interval = 0.0
        ops.jitter_ratio = 0.0
        ops.max_retries = 0
        ops.retry_base = 0.1
        ops._cookie_alive = None
        items = ops.walk_media_items("0", "/in", 1, max_items=1)
        self.assertEqual(len(items), 1)
        self.assertEqual(calls, [0])

    def test_target_must_not_be_inside_source_tree(self):
        self.assertTrue(execution_module.source_contains_target("/incoming", "/incoming/library"))
        self.assertTrue(execution_module.source_contains_target("/incoming", "/incoming"))
        self.assertFalse(execution_module.source_contains_target("/incoming", "/library"))
        self.assertFalse(execution_module.source_contains_target("/incoming/a", "/incoming/ab"))

    def test_category_prefers_v3_library_category(self):
        mapper = category_mapper.CategoryMapper()
        media = SimpleNamespace(library_category="欧美剧", category="旧分类")
        source, target, warning = mapper.resolve(
            "tv", media, {"tv": {"欧美剧": "123"}}
        )
        self.assertEqual((source, target, warning), ("欧美剧", "欧美剧", ""))

    def test_category_fallback_uses_v3_classification_service(self):
        app_module = types.ModuleType("app")
        app_module.__path__ = []
        sdk_module = types.ModuleType("app.sdk")
        sdk_module.__path__ = []
        classification_module = types.ModuleType("app.sdk.classification")
        classification_module.classify_media = lambda media: SimpleNamespace(
            library_category="国产剧"
        )
        old_modules = {
            name: sys.modules.get(name)
            for name in ("app", "app.sdk", "app.sdk.classification")
        }
        sys.modules.update({
            "app": app_module,
            "app.sdk": sdk_module,
            "app.sdk.classification": classification_module,
        })
        try:
            mapper = category_mapper.CategoryMapper()
            media = SimpleNamespace(library_category="", category="")
            source, target, warning = mapper.resolve(
                "tv", media, {"tv": {"国产剧": "target-cid"}}
            )
            self.assertEqual((source, target, warning), ("国产剧", "国产剧", ""))
        finally:
            for name, previous in old_modules.items():
                if previous is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = previous

    def test_media_identity_is_normalized_as_a_pair(self):
        app_module = types.ModuleType("app")
        app_module.__path__ = []
        sdk_module = types.ModuleType("app.sdk")
        sdk_module.__path__ = []
        media_module = types.ModuleType("app.sdk.media")
        media_module.resolve_media_identity = lambda media: (media.media_source, media.media_id)
        old_modules = {name: sys.modules.get(name) for name in ("app", "app.sdk", "app.sdk.media")}
        sys.modules.update({"app": app_module, "app.sdk": sdk_module, "app.sdk.media": media_module})
        try:
            media = SimpleNamespace(media_source=MediaSource.TMDB, media_id=12345)
            self.assertEqual(
                planner_module.Planner._media_identity(media),
                ("tmdb", "12345"),
            )
        finally:
            for name, previous in old_modules.items():
                if previous is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = previous

    def test_custom_v3_category_uses_dynamic_target_resolver(self):
        calls = []
        planner = planner_module.Planner(
            category_mapper=category_mapper.CategoryMapper(),
            target_cids={"movie": {}, "tv": {}},
            target_resolver=lambda media_type, category: calls.append((media_type, category)) or "cid-doc",
        )
        media = SimpleNamespace(
            title="Documentary",
            year=2026,
            media_source=MediaSource.TMDB,
            media_id="88",
            library_category="纪录片",
            category="纪录片",
        )
        meta = SimpleNamespace(begin_season=None, begin_episode=None)
        planner._recognize = lambda *_args, **_kwargs: (media, meta)
        planner._media_identity = lambda _media: ("tmdb", "88")
        planner._moviepilot_rename_path = lambda *_args, **_kwargs: "Documentary (2026)/Documentary.mkv"
        item = models.MediaItem("f1", None, "Documentary.mkv", ".mkv", 100, False, "p1", "/in/Documentary.mkv")
        plans = planner.build_plans("movie", [item], {}, [])
        self.assertEqual(calls, [("movie", "纪录片")])
        self.assertEqual(plans[0]["target_parent_cid"], "cid-doc")
        self.assertEqual(plans[0]["status"], "planned")

    def test_plan_persists_v3_media_identity(self):
        planner = planner_module.Planner(
            category_mapper=category_mapper.CategoryMapper(),
            target_cids={"movie": {"外语电影": "target-cid"}},
        )
        media = SimpleNamespace(
            title="Example",
            year=2026,
            media_source=MediaSource.TMDB,
            media_id="12345",
            library_category="外语电影",
            category="外语电影",
        )
        meta = SimpleNamespace(begin_season=None, begin_episode=None)
        planner._recognize = lambda *_args, **_kwargs: (media, meta)
        planner._moviepilot_rename_path = lambda *_args, **_kwargs: "Example (2026)/Example (2026).mkv"
        item = models.MediaItem(
            fid="fid-1",
            cid=None,
            name="Example.2026.mkv",
            ext=".mkv",
            size=1024,
            is_dir=False,
            parent_cid="source-cid",
            path_hint="/待整理/Example.2026.mkv",
        )
        old_resolver = planner_module.Planner._media_identity
        planner_module.Planner._media_identity = staticmethod(lambda _media: ("tmdb", "12345"))
        try:
            plans = planner.build_plans("movie", [item], {}, [])
        finally:
            planner_module.Planner._media_identity = old_resolver
        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0]["media_source"], "tmdb")
        self.assertEqual(plans[0]["media_id"], "12345")
        self.assertNotIn("tmdbid", plans[0])


if __name__ == "__main__":
    unittest.main()
