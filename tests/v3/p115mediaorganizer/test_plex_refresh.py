"""Targeted Plex refresh: only touched title folders are scanned, never every library."""

from __future__ import annotations

import time
import unittest
import xml.etree.ElementTree as ElementTree
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.parse import parse_qs, urlsplit

from .test_workflow import configuration, ns, plan, plex_refresh, plugin

SECTIONS_XML = """<MediaContainer>
  <Directory key="1" type="movie" title="电影">
    <Location id="11" path="/CloudNAS/115/媒体库/Movie" />
  </Directory>
  <Directory key="2" type="show" title="剧集">
    <Location id="21" path="/CloudNAS/115/媒体库/TV" />
  </Directory>
  <Directory key="3" type="movie" title="本地电影">
    <Location id="31" path="/volume1/Movies" />
  </Directory>
</MediaContainer>"""


class FakePlex:
    """Records every request; any full-library refresh endpoint fails the test."""

    def __init__(self, sections_xml: str = SECTIONS_XML, fail_refresh: bool = False):
        self.sections_xml = sections_xml
        self.fail_refresh = fail_refresh
        self.queries: list[str] = []

    def query(self, key):
        self.queries.append(key)
        if key == "/library/sections":
            return ElementTree.fromstring(self.sections_xml)
        if "/library/sections/all/refresh" in key or key.endswith("/refresh"):
            raise AssertionError(f"full library refresh requested: {key}")
        if self.fail_refresh:
            raise RuntimeError("Plex timeout")
        return None

    @property
    def refreshes(self) -> list[tuple[str, str]]:
        """[(section key, scanned path)] for every partial refresh request."""
        result = []
        for key in self.queries:
            parsed = urlsplit(key)
            if parsed.path.endswith("/refresh"):
                section = parsed.path.split("/")[3]
                result.append((section, parse_qs(parsed.query)["path"][0]))
        return result


class FakeInstance:
    """Plex wrapper as exposed by MoviePilot; its own refresh methods must never be used."""

    def __init__(self, plex):
        self._plex = plex
        self.refresh_library_by_items = Mock(side_effect=AssertionError("host fallback refreshes all libraries"))
        self.refresh_root_library = Mock(side_effect=AssertionError("full library refresh"))

    def get_plex(self):
        return self._plex

    @staticmethod
    def is_inactive():
        return False


def executed(category="外语电影", folder="Dune (2021)", media_type="movie", root="/媒体库/Movie", **extra):
    return {
        "media_type": media_type,
        "target_category": category,
        "target_root_path": root,
        "target_dir_name": folder,
        "target_path": f"{root}/{category}/{folder}/file.mkv",
        **extra,
    }


def libraries(xml=SECTIONS_XML):
    return plex_refresh.load_plex_libraries(FakePlex(xml))


class PathResolutionTest(unittest.TestCase):
    def test_auto_detects_mount_prefix_from_library_location(self):
        targets, method = plex_refresh.resolve_refresh_targets("/媒体库/Movie/外语电影/Dune (2021)", [], libraries())
        self.assertEqual(method, "自动匹配")
        self.assertEqual([(lib.key, path) for lib, path in targets], [("1", "/CloudNAS/115/媒体库/Movie/外语电影/Dune (2021)")])

    def test_explicit_mapping_wins_and_longest_prefix_is_used(self):
        mappings, errors = plex_refresh.parse_path_mappings(
            "/媒体库 => /mnt/wrong\n/媒体库/Movie => /volume1/Movies\n"
        )
        self.assertEqual(errors, [])
        targets, method = plex_refresh.resolve_refresh_targets("/媒体库/Movie/外语电影/Dune (2021)", mappings, libraries())
        self.assertEqual(method, "路径映射")
        self.assertEqual([(lib.key, path) for lib, path in targets], [("3", "/volume1/Movies/外语电影/Dune (2021)")])

    def test_unmatched_folder_returns_nothing_instead_of_whole_server(self):
        targets, method = plex_refresh.resolve_refresh_targets("/其他目录/电影/Dune (2021)", [], libraries())
        self.assertEqual((targets, method), ([], ""))

    def test_similar_prefix_is_not_treated_as_same_folder(self):
        xml = '<MediaContainer><Directory key="9" title="x"><Location path="/mnt/媒体库/Movie2" /></Directory></MediaContainer>'
        targets, _ = plex_refresh.resolve_refresh_targets("/媒体库/Movie/外语电影/Dune", [], libraries(xml))
        self.assertEqual(targets, [])

    def test_more_specific_overlap_beats_single_common_folder_name(self):
        xml = """<MediaContainer>
          <Directory key="1" title="other"><Location path="/data/Movie" /></Directory>
          <Directory key="2" title="real"><Location path="/mnt/115/媒体库/Movie" /></Directory>
        </MediaContainer>"""
        targets, _ = plex_refresh.resolve_refresh_targets("/媒体库/Movie/外语电影/Dune", [], libraries(xml))
        self.assertEqual([(lib.key, path) for lib, path in targets], [("2", "/mnt/115/媒体库/Movie/外语电影/Dune")])

    def test_windows_plex_paths_are_matched_and_joined_with_backslashes(self):
        xml = r'<MediaContainer><Directory key="5" title="w"><Location path="D:\115\媒体库\Movie" /></Directory></MediaContainer>'
        targets, _ = plex_refresh.resolve_refresh_targets("/媒体库/Movie/外语电影/Dune", [], libraries(xml))
        self.assertEqual([path for _, path in targets], [r"D:\115\媒体库\Movie\外语电影\Dune"])
        mappings, errors = plex_refresh.parse_path_mappings(r"/媒体库 => D:\115\媒体库")
        self.assertEqual(errors, [])
        targets, _ = plex_refresh.resolve_refresh_targets("/媒体库/Movie/外语电影/Dune", mappings, libraries(xml))
        self.assertEqual([path for _, path in targets], [r"D:\115\媒体库\Movie\外语电影\Dune"])
        # Typed with forward slashes and different case: the path sent to Plex still uses Plex's own prefix.
        mappings, _ = plex_refresh.parse_path_mappings("/媒体库 => d:/115/媒体库")
        targets, _ = plex_refresh.resolve_refresh_targets("/媒体库/Movie/外语电影/Dune", mappings, libraries(xml))
        self.assertEqual([path for _, path in targets], [r"D:\115\媒体库\Movie\外语电影\Dune"])

    def test_invalid_mapping_lines_are_reported_by_configuration_check(self):
        for text in ("/媒体库 /CloudNAS", "媒体库 => /CloudNAS", "/媒体库 => CloudNAS", "/a/../b => /c"):
            result = configuration.check_configuration({"source_mappings": [], "plex_path_mappings": text})
            self.assertTrue(any("Plex 路径映射第 1 行" in e for e in result.errors), text)
        result = configuration.check_configuration({"plex_path_mappings": "\n/媒体库 => /CloudNAS/115/媒体库\n"})
        self.assertFalse(any("Plex" in e for e in result.errors))

    def test_folders_are_deduplicated_per_title_and_skip_cid_only_targets(self):
        folders = plex_refresh.refresh_folders([
            executed(),
            executed(),  # second file of the same movie
            executed(category="国产剧", folder="繁花 (2023)", media_type="tv", root="/媒体库/TV"),
            executed(category="未识别", folder="x", target_path="115://cid/9/x/x.mkv"),
            executed(media_type="music"),
        ])
        self.assertEqual(
            [f["path"] for f in folders],
            ["/媒体库/Movie/外语电影/Dune (2021)", "/媒体库/TV/国产剧/繁花 (2023)"],
        )

    def test_old_plan_without_root_falls_back_to_configured_root(self):
        item = executed()
        item.pop("target_root_path")
        folders = plex_refresh.refresh_folders([item], {"movie": "/媒体库/Movie"})
        self.assertEqual(folders[0]["path"], "/媒体库/Movie/外语电影/Dune (2021)")

    def test_refresh_endpoint_matches_plexapi_section_update(self):
        self.assertEqual(
            plex_refresh.refresh_endpoint("1", "/CloudNAS/115/媒体库/Movie/外语电影/Dune (2021)"),
            "/library/sections/1/refresh?path=%2FCloudNAS%2F115%2F%E5%AA%92%E4%BD%93%E5%BA%93%2FMovie%2F"
            "%E5%A4%96%E8%AF%AD%E7%94%B5%E5%BD%B1%2FDune+%282021%29",
        )


class PluginRefreshTest(unittest.TestCase):
    def setUp(self):
        self.p = plugin()
        self.plex = FakePlex()
        self.instance = FakeInstance(self.plex)
        self.p._plex_service_infos = Mock(return_value={"Plex": SimpleNamespace(instance=self.instance)})

    def test_only_touched_title_folders_are_refreshed(self):
        rows = self.p._refresh_plex_after_success([
            executed(),
            executed(),
            executed(category="国产剧", folder="繁花 (2023)", media_type="tv", root="/媒体库/TV"),
        ])
        self.assertEqual(self.plex.refreshes, [
            ("1", "/CloudNAS/115/媒体库/Movie/外语电影/Dune (2021)"),
            ("2", "/CloudNAS/115/媒体库/TV/国产剧/繁花 (2023)"),
        ])
        self.assertEqual([r["status"] for r in rows], ["refreshed", "refreshed"])
        self.assertEqual(rows[0]["library"], "电影")
        self.instance.refresh_library_by_items.assert_not_called()
        self.instance.refresh_root_library.assert_not_called()

    def test_unmatched_folder_is_skipped_and_reported_without_any_refresh(self):
        rows = self.p._refresh_plex_after_success([executed(root="/别处/Movie")])
        self.assertEqual(self.plex.refreshes, [])
        self.assertEqual(rows[0]["status"], "unmatched")
        self.assertIn("不会刷新全部媒体库", rows[0]["message"])
        self.assertEqual(plex_refresh.summarize_refresh(rows), {"refreshed": 0, "unmatched": 1, "failed": 0})

    def test_configured_mapping_is_used(self):
        self.p._plex_path_mappings = "/别处 => /volume1"
        self.p._refresh_plex_after_success([executed(root="/别处/Movies")])
        self.assertEqual(self.plex.refreshes, [("3", "/volume1/Movies/外语电影/Dune (2021)")])

    def test_refresh_error_is_reported_per_folder_without_fallback(self):
        self.plex.fail_refresh = True
        rows = self.p._refresh_plex_after_success([executed()])
        self.assertEqual(rows[0]["status"], "failed")
        self.assertIn("Plex timeout", rows[0]["message"])
        self.instance.refresh_root_library.assert_not_called()

    def test_unavailable_plex_client_does_not_refresh(self):
        self.instance._plex = None
        rows = self.p._refresh_plex_after_success([executed()])
        self.assertEqual(rows[0]["status"], "failed")
        self.instance.refresh_root_library.assert_not_called()

    def test_disabled_refresh_does_not_contact_plex(self):
        self.p._refresh_plex_after_execute = False
        self.assertEqual(self.p._refresh_plex_after_success([executed()]), [])
        self.p._plex_service_infos.assert_not_called()

    def test_missing_plex_server_does_not_add_failure_noise_to_messages(self):
        # Refresh is enabled by default; users without Plex must not see a failure in every notification.
        self.p._plex_service_infos = Mock(return_value={})
        rows = self.p._refresh_plex_after_success([executed()])
        self.assertEqual(rows[0]["status"], "unavailable")
        summary = plex_refresh.summarize_refresh(rows)
        self.assertEqual(summary, {"refreshed": 0, "unmatched": 0, "failed": 0})
        self.assertEqual(plex_refresh.describe_refresh_summary(summary), "")

    def test_nothing_to_refresh_does_not_contact_plex(self):
        rows = self.p._refresh_plex_after_success([executed(target_path="115://cid/9/x/x.mkv")])
        self.assertEqual(rows, [])
        self.p._plex_service_infos.assert_not_called()

    def test_execution_result_and_run_summary_count_only_refreshed_folders(self):
        p = self.p
        items = plan(p, 2)
        for item in items:
            item.update(
                media_type="movie",
                target_root_path="/媒体库/Movie",
                target_category="外语电影",
                target_dir_name="Dune (2021)",
            )
        items.append({
            **items[0],
            "item_id": "file-x",
            "target_root_path": "/别处/Movie",
            "target_path": "/别处/Movie/外语电影/Dune (2021)/x.mkv",
        })
        p.save_data("last_plan", items)
        p._p115_ops = Mock(return_value=SimpleNamespace(available=True))
        p._sleep_between_batches = 0

        def group(_ops, chunk, runid, history, run_history, result, success):
            for item in chunk:
                p._record_outcome(item, "executed", "", runid, history, run_history, result, success)

        p._execute_group = group
        p._cleanup_sources = Mock(return_value={"dirs": [], "subtitles": []})
        response = p._execute_last_plan(allow_dry_run=True, reviewed=True)
        self.assertEqual(response.data["plex_refresh_summary"], {"refreshed": 1, "unmatched": 1, "failed": 0})
        self.assertIn("Plex：已刷新 1 个目录，1 个未匹配到媒体库（未刷新）", response.message)
        self.assertEqual(p.get_data("runs")[-1]["plex_refresh_count"], 1)
        self.assertEqual(
            p.workflow_status_api().data["last_result"]["plex_refresh_summary"]["unmatched"], 1
        )
        self.assertEqual(self.plex.refreshes, [("1", "/CloudNAS/115/媒体库/Movie/外语电影/Dune (2021)")])

    def test_saved_mapping_round_trips_through_init(self):
        config = {**self.p.config, "plex_path_mappings": "/媒体库 => /CloudNAS/115/媒体库"}
        self.p._stop_service = Mock()
        self.p.init_plugin(config)
        self.assertEqual(self.p._plex_path_mappings, "/媒体库 => /CloudNAS/115/媒体库")
        self.assertIn("plex_path_mappings", self.p._default_config())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
