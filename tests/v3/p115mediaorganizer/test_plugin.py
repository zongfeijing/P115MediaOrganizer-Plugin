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


class MediaSource(Enum):
    TMDB = "tmdb"


class V3ContractTest(unittest.TestCase):
    def test_indexes_select_dedicated_v3_implementation(self):
        v2 = json.loads((ROOT / "package.v2.json").read_text())
        v3 = json.loads((ROOT / "package.v3.json").read_text())
        self.assertIs(v2["P115MediaOrganizer"]["v3"], False)
        self.assertEqual(v3["P115MediaOrganizer"]["version"], "1.0.0")
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
