"""Source cleanup deletes leftover subtitles but never other files or the source root."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from .test_workflow import p115_ops_module, plugin


class FakeTree(p115_ops_module.P115Ops):
    """In-memory 115 tree: {cid: [entries]}; records every delete call."""

    def __init__(self, tree, fail_batch=False):
        self.tree = tree
        self.fail_batch = fail_batch
        self.batches = []
        self.singles = []

    def list_entries(self, cid):
        return [dict(entry) for entry in self.tree.get(str(cid), [])]

    def batch_delete(self, fids):
        if self.fail_batch:
            raise RuntimeError("batch failed")
        self.batches.append(list(fids))
        return {"state": True}

    def delete(self, fid):
        self.singles.append(fid)
        return {"state": True}

    @property
    def deleted(self):
        return [fid for batch in self.batches for fid in batch] + self.singles


def video(fid, name, size=2_000_000_000):
    return {"fid": fid, "n": name, "s": size, "is_dir": False}


def subtitle(fid, name):
    return {"fid": fid, "n": name, "s": 40_000, "is_dir": False}


def folder(cid, name):
    return {"cid": cid, "n": name, "is_dir": True}


# /最近接收/Movie (root 10)
#   Dune.2021.2160p.mkv            <- organized this run (gone after move); sidecars sit in the root
#   Dune.2021.2160p.chs.srt        sidecar of the organized video  -> delete
#   Other.2020.chs.srt             unrelated subtitle in the root  -> keep
#   notes.txt                      other file in the root          -> keep
#   Show.S01 (11)/                 only subtitles left             -> delete folder (with subtitles)
#     Show.S01E01.ass, Show.S01E02.srt
#   Extras (12)/                   has a non-subtitle file         -> keep folder and files
#     Show.S01E01.srt, poster.jpg
#   Nested (13)/ -> Season 1 (14)/ only subtitles; Nested itself only has that child -> delete both
TREE = {
    "10": [
        subtitle("f1", "Dune.2021.2160p.chs.srt"),
        subtitle("f2", "Other.2020.chs.srt"),
        video("f3", "notes.txt", 100),
        folder("11", "Show.S01"),
        folder("12", "Extras"),
        folder("13", "Nested"),
    ],
    "11": [subtitle("f4", "Show.S01E01.ass"), subtitle("f5", "Show.S01E02.srt")],
    "12": [subtitle("f6", "Show.S01E01.srt"), video("f7", "poster.jpg", 300_000)],
    "13": [folder("14", "Season 1")],
    "14": [subtitle("f8", "Show.S01E03.SRT")],
}

ORGANIZED = [
    {"source_root_cid": "10", "source_parent_cid": "10", "source_name": "Dune.2021.2160p.mkv", "source_is_dir": False},
    {"source_root_cid": "10", "source_parent_cid": "11", "source_name": "Show.S01E01.mkv", "source_is_dir": False},
    {"source_root_cid": "10", "source_parent_cid": "12", "source_name": "Show.S01E01.mkv", "source_is_dir": False},
]


class CleanupPlanTest(unittest.TestCase):
    def plan(self, tree=TREE, items=ORGANIZED):
        ops = FakeTree(tree)
        stems = {}
        for item in items:
            stems.setdefault(item["source_parent_cid"], []).append(item["source_name"].rsplit(".", 1)[0])
        return ops.plan_source_cleanup(
            "10", 7, removable_extensions=p115_ops_module.SUBTITLE_EXTENSIONS, sidecar_stems=stems
        )

    def test_subtitle_only_folders_are_removed_bottom_up(self):
        plan = self.plan()
        self.assertEqual(plan["dirs"], ["11", "14", "13"])
        self.assertEqual(plan["dir_files"]["11"], ["Show.S01E01.ass", "Show.S01E02.srt"])
        self.assertEqual(plan["dir_files"]["14"], ["Show.S01E03.SRT"])

    def test_only_sidecars_of_organized_videos_are_deleted_in_kept_folders(self):
        plan = self.plan()
        # Root keeps Other.2020.chs.srt and notes.txt; Extras keeps poster.jpg but drops the sidecar.
        self.assertEqual(sorted(f["name"] for f in plan["files"]), ["Dune.2021.2160p.chs.srt", "Show.S01E01.srt"])
        self.assertNotIn("12", plan["dirs"])
        self.assertNotIn("10", plan["dirs"])

    def test_subtitles_of_another_video_still_in_the_folder_are_kept(self):
        tree = {"10": [
            subtitle("f1", "Dune.2021.2160p.REPACK.srt"),
            subtitle("f2", "Dune.2021.2160p.chs.srt"),
            video("f3", "Dune.2021.2160p.REPACK.mkv"),  # skipped this run, still in the source
        ]}
        plan = self.plan(tree, ORGANIZED[:1])
        self.assertEqual([f["name"] for f in plan["files"]], ["Dune.2021.2160p.chs.srt"])

    def test_sidecar_match_needs_the_dot_after_the_stem(self):
        tree = {"10": [subtitle("f1", "Dune.2021.2160pX.srt"), subtitle("f2", "dune.2021.2160p.ENG.SRT")]}
        plan = self.plan(tree, ORGANIZED[:1])
        self.assertEqual([f["name"] for f in plan["files"]], ["dune.2021.2160p.ENG.SRT"])

    def test_without_subtitle_extensions_behaves_like_empty_dir_cleanup(self):
        ops = FakeTree({"10": [folder("11", "a"), folder("12", "b")], "11": [], "12": [subtitle("s", "x.srt")]})
        self.assertEqual(ops.plan_source_cleanup("10", 7)["dirs"], ["11"])

    def test_depth_limit_keeps_deep_folders(self):
        plan = FakeTree(TREE).plan_source_cleanup("10", 1, removable_extensions=p115_ops_module.SUBTITLE_EXTENSIONS)
        self.assertNotIn("14", plan["dirs"])
        self.assertNotIn("13", plan["dirs"])


class PluginCleanupTest(unittest.TestCase):
    def setUp(self):
        self.p = plugin()
        self.p._task = SimpleNamespace(cancel=SimpleNamespace(is_set=lambda: False))

    def test_deletes_sidecars_then_folders_and_reports_names(self):
        ops = FakeTree(TREE)
        result = self.p._cleanup_sources(ops, ORGANIZED)
        self.assertEqual(sorted(ops.batches[0]), ["f1", "f6"])  # sidecars first
        self.assertEqual(ops.batches[1], ["11", "14", "13"])  # then folders, children first
        self.assertNotIn("f2", ops.deleted)
        self.assertNotIn("f3", ops.deleted)
        self.assertNotIn("f7", ops.deleted)
        self.assertNotIn("10", ops.deleted)
        self.assertEqual(result["dirs"], ["11", "14", "13"])
        self.assertEqual(
            sorted(result["subtitles"]),
            sorted(["Dune.2021.2160p.chs.srt", "Show.S01E01.srt", "Show.S01E01.ass", "Show.S01E02.srt", "Show.S01E03.SRT"]),
        )

    def test_batch_failure_falls_back_to_single_deletes(self):
        ops = FakeTree(TREE, fail_batch=True)
        result = self.p._cleanup_sources(ops, ORGANIZED)
        self.assertEqual(sorted(ops.singles[:2]), ["f1", "f6"])
        self.assertEqual(ops.singles[2:], ["11", "14", "13"])
        self.assertEqual(len(result["subtitles"]), 5)

    def test_untouched_source_roots_are_not_scanned(self):
        ops = FakeTree(TREE)
        ops.plan_source_cleanup = Mock(return_value={"dirs": [], "files": [], "dir_files": {}})
        self.p._cleanup_sources(ops, [])
        ops.plan_source_cleanup.assert_not_called()


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
