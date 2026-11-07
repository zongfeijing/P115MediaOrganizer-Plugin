"""Conservative auto-execution, the follow-up list, and the organize notification."""

from __future__ import annotations

import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from .test_workflow import execution_module, plugin, reporting


def item(i, **extra):
    base = {
        "plan_id": "shared",
        "item_id": f"file:{i}",
        "status": "planned",
        "action": "move",
        "media_type": "movie",
        "source_name": f"Movie.{i}.2026.mkv",
        "source_fid": f"fid{i}",
        "path_hint": f"/最近接收/Movie/Movie.{i}.2026.mkv",
        "title": f"影片{i}",
        "year": "2026",
        "target_root_path": "/MeidiaLib/Movie",
        "target_category": "华语电影",
        "target_dir_name": f"影片{i} (2026)",
        "target_path": f"/MeidiaLib/Movie/华语电影/影片{i} (2026)/影片{i} (2026).mkv",
        "confidence": "normal",
        "media_source": "themoviedb",
        "media_id": str(1000 + i),
        "warnings": [],
        "created_at_epoch": time.time(),
    }
    base.update(extra)
    return base


class HoldPolicyTest(unittest.TestCase):
    hold = staticmethod(execution_module.auto_execute_hold_reason)

    def test_clear_recognition_is_executed(self):
        self.assertEqual(self.hold(item(1)), "")

    def test_unrecognized_missing_identity_or_warnings_are_held(self):
        self.assertEqual(self.hold(item(1, confidence="unrecognized", target_category="华语电影")), "未明确识别媒体")
        self.assertEqual(self.hold(item(1, media_id="")), "未明确识别媒体")
        self.assertIn("MoviePilot分类为空", self.hold(item(1, warnings=["MoviePilot分类为空"])))

    def test_tv_without_episode_is_held(self):
        self.assertEqual(self.hold(item(1, media_type="tv", episode=0)), "未识别到明确集数")
        self.assertEqual(self.hold(item(1, media_type="tv", season=1, episode=3)), "")

    def test_naming_template_fallback_does_not_block(self):
        self.assertEqual(self.hold(item(1, warnings=["MoviePilot命名模板渲染失败，使用内置命名：x"])), "")

    def test_explicit_move_to_unrecognized_is_not_held(self):
        self.assertEqual(self.hold(item(1, confidence="unrecognized", target_category="未识别", media_id="")), "")


class AutoExecutionTest(unittest.TestCase):
    def setUp(self):
        self.p = plugin()
        self.p._sleep_between_batches = 0
        self.p._p115_ops = Mock(return_value=SimpleNamespace(available=True))
        self.p._cleanup_sources = Mock(return_value={"dirs": [], "subtitles": []})
        self.p._refresh_plex_after_success = Mock(return_value=[])
        self.executed = []

        def group(_ops, chunk, runid, history, run_history, result, success):
            for row in chunk:
                self.executed.append(row["item_id"])
                self.p._record_outcome(row, "executed", "", runid, history, run_history, result, success)

        self.p._execute_group = group
        snapshot = self.p._config_snapshot()
        rows = [item(1), item(2, warnings=["MoviePilot分类为空"]), item(3, media_type="tv", episode=0)]
        for row in rows:
            row["config_snapshot"] = snapshot
        self.p.save_data("last_plan", rows)

    def test_automatic_run_holds_unclear_files_and_lists_them(self):
        response = self.p._execute_last_plan(trigger_source="auto", allow_dry_run=True)
        self.assertEqual(self.executed, ["file:1"])
        self.assertEqual(response.data["held"], 2)
        self.assertIn("2 个识别不明确", response.message)
        plan = self.p.get_data("last_plan")
        self.assertEqual([r["status"] for r in plan], ["executed", "planned", "planned"])
        attention = self.p.get_data("attention")
        self.assertEqual(sorted(r["key"] for r in attention), ["file:2", "file:3"])
        self.assertTrue(all(r["status"] == "held" for r in attention))
        self.assertEqual(self.p.workflow_status_api().data["attention"]["count"], 2)
        self.assertEqual(self.p.get_data("runs")[-1]["held"], 2)

    def test_reviewed_run_executes_everything_and_clears_held_entries(self):
        self.p._execute_last_plan(trigger_source="auto", allow_dry_run=True)
        self.executed.clear()
        self.p._execute_last_plan(trigger_source="manual_confirmed", allow_dry_run=True, reviewed=True)
        self.assertEqual(self.executed, ["file:2", "file:3"])
        self.assertEqual(self.p.get_data("attention"), [])
        self.assertNotIn("held_reason", self.p.get_data("last_plan")[1])

    def test_policy_all_keeps_previous_behaviour(self):
        self.p._auto_execute_policy = "all"
        response = self.p._execute_last_plan(trigger_source="auto", allow_dry_run=True)
        self.assertEqual(self.executed, ["file:1", "file:2", "file:3"])
        self.assertEqual(response.data["held"], 0)

    def test_policy_config_falls_back_to_confident(self):
        self.p._stop_service = Mock()
        self.p.init_plugin({**self.p.config, "auto_execute_policy": "weird"})
        self.assertEqual(self.p._auto_execute_policy, "confident")
        self.assertEqual(self.p._default_config()["auto_execute_policy"], "confident")

    def test_notification_uses_organize_type_with_titles_and_poster(self):
        rows = self.p.get_data("last_plan")
        rows[0]["image"] = "https://image.tmdb.org/t/p/w500/a.jpg"
        self.p.save_data("last_plan", rows)
        self.p._execute_last_plan(trigger_source="auto", allow_dry_run=True)
        kwargs = self.p.post_message.call_args.kwargs
        self.assertEqual(kwargs["mtype"], "整理入库")
        self.assertEqual(kwargs["title"], "115 整理入库：影片1 (2026)")
        self.assertIn("影片1 (2026) → 华语电影", kwargs["text"])
        self.assertIn("保留待确认 2", kwargs["text"])
        self.assertIn("需处理 2 个", kwargs["text"])
        self.assertEqual(kwargs["image"], "https://image.tmdb.org/t/p/w500/a.jpg")

    def test_notification_without_success_but_problems_is_manual_type(self):
        self.p._auto_execute_policy = "confident"
        rows = self.p.get_data("last_plan")
        rows[0]["warnings"] = ["MoviePilot分类为空"]
        self.p.save_data("last_plan", rows)
        self.p._execute_last_plan(trigger_source="auto", allow_dry_run=True)
        kwargs = self.p.post_message.call_args.kwargs
        self.assertEqual(kwargs["mtype"], "手动处理")
        self.assertEqual(kwargs["title"], "115 整理完成：没有新入库")
        self.assertIsNone(kwargs["image"])

    def test_notification_respects_notify_switch(self):
        self.p._notify = False
        self.p._execute_last_plan(trigger_source="auto", allow_dry_run=True)
        self.p.post_message.assert_not_called()

    def test_scheduled_run_returns_a_response_and_finishes_the_task(self):
        # Regression: auto_run used to return None, so _run_exclusive raised on response.success
        # after the work was done and the scheduled task was reported as failed.
        plan = self.p.get_data("last_plan")
        self.p._generate_plan = Mock(return_value=SimpleNamespace(success=True, message="ok", data=plan))
        self.p._dry_run = False
        response = self.p.auto_run()
        self.assertTrue(response.success)
        self.assertEqual(self.p._task.snapshot()["status"], "completed")
        self.assertEqual(self.executed, ["file:1"])
        self.p._dry_run = True
        self.assertTrue(self.p.auto_run().success)
        self.assertEqual(self.p.post_message.call_args.kwargs["title"], "115 整理预览已生成")
        self.p._generate_plan = Mock(return_value=SimpleNamespace(success=False, message="连接失败", data=None))
        self.assertFalse(self.p.auto_run().success)
        self.assertEqual(self.p._task.snapshot()["status"], "failed")

    def test_attention_records_are_listable_and_free_of_internal_ids(self):
        self.p._execute_last_plan(trigger_source="auto", allow_dry_run=True)
        rows = self.p.records_api(kind="attention").data["items"]
        self.assertEqual(len(rows), 2)
        self.assertTrue(all("key" not in r for r in rows))
        self.assertTrue(all(r["reason"].startswith("已保留待确认") for r in rows))
        self.assertEqual({r["status"] for r in rows}, {"held"})


class AttentionListTest(unittest.TestCase):
    def test_skip_at_execution_survives_later_previews_until_resolved(self):
        skipped = item(1, status="skipped", error="目标已存在：影片1 (2026).mkv")
        rows = reporting.attention_items([skipped])
        self.assertEqual([r["reason"] for r in rows], ["目标已存在：影片1 (2026).mkv"])
        # Next preview sees the same file as plannable: the problem is not known to be fixed.
        rows = reporting.attention_items([item(1)], rows)
        self.assertEqual(len(rows), 1)
        # Organized later: drop it.
        self.assertEqual(reporting.attention_items([item(1, status="executed")], rows), [])

    def test_files_gone_after_full_scan_are_dropped_but_kept_after_partial_scan(self):
        rows = reporting.attention_items([item(1, status="failed", error="移动失败")])
        self.assertEqual(len(reporting.attention_items([], rows, complete_scan=False)), 1)
        self.assertEqual(reporting.attention_items([], rows, complete_scan=True), [])

    def test_already_organized_skips_are_not_listed(self):
        routine = item(1, status="skipped", action="skip", warnings=["此前已成功整理，跳过重复处理"])
        self.assertEqual(reporting.attention_items([routine]), [])

    def test_unrecognized_and_new_reasons_replace_old_ones_and_keep_first_seen(self):
        rows = reporting.stamp_first_seen(
            reporting.attention_items([item(1, status="skipped", action="skip", warnings=["未识别到媒体"])]),
            "2026-11-01 10:00:00",
        )
        rows = reporting.attention_items([item(1, status="failed", error="源文件已移动")], rows)
        self.assertEqual(rows[0]["reason"], "源文件已移动")
        self.assertEqual(rows[0]["first_seen"], "2026-11-01 10:00:00")


class MessageFormatTest(unittest.TestCase):
    def test_episodes_are_grouped_into_ranges_per_show(self):
        eps = [item(i, media_type="tv", title="藏锋", season=1, episode=i, target_category="国产剧") for i in (1, 2, 3, 5, 7, 8)]
        msg = reporting.organize_message({"success": 6, "failed": 0, "skipped": 0}, eps, [])
        self.assertEqual(msg["title"], "115 整理入库：藏锋 (2026)")
        self.assertIn("藏锋 (2026) S01E01-E03、E05、E07-E08 → 国产剧", msg["text"])

    def test_many_titles_are_summarized(self):
        movies = [item(i) for i in range(12)]
        msg = reporting.organize_message({"success": 12, "failed": 0, "skipped": 0}, movies, [])
        self.assertEqual(msg["title"], "115 整理入库：影片0 (2026) 等 12 部")
        self.assertIn("另有 4 部", msg["text"])

    def test_failures_subtitles_and_plex_are_reported(self):
        result = {"success": 1, "failed": 1, "skipped": 0, "errors": [{"source": "x.mkv", "error": "超时"}],
                  "deleted_subtitles": ["a.srt", "b.ass"]}
        msg = reporting.organize_message(result, [item(1)], [], "Plex：已刷新 1 个目录")
        self.assertIn("失败：x.mkv：超时", msg["text"])
        self.assertIn("已删除来源字幕 2 个", msg["text"])
        self.assertTrue(msg["text"].endswith("Plex：已刷新 1 个目录"))

    def test_stopped_run_title(self):
        msg = reporting.organize_message({"success": 2, "cancelled": True}, [item(1)], [])
        self.assertEqual(msg["title"], "115 整理已停止：完成 2 个文件")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()


class NewAttentionNoticeTest(unittest.TestCase):
    """Runs that organize nothing notify only about files that newly need attention."""

    def setUp(self):
        self.p = plugin()
        self.p._dry_run = False
        self.p._execute_last_plan = Mock()
        snapshot = self.p._config_snapshot()
        self.unclear = item(9, status="skipped", action="skip", confidence="unrecognized",
                            warnings=["未识别到媒体，保留源文件"], config_snapshot=snapshot)

    def scan(self, rows):
        def fake_generate(media_type=None, save=True):
            self.p.save_data("last_plan", rows)
            self.p._update_attention(rows, complete_scan=True)
            return SimpleNamespace(success=True, message="ok", data=rows)
        self.p._generate_plan = fake_generate

    def test_new_problem_is_notified_once_then_stays_quiet(self):
        self.scan([self.unclear])
        self.p.auto_run()
        self.p._execute_last_plan.assert_not_called()  # nothing executable: no empty execution
        first = self.p.post_message.call_args.kwargs
        self.assertEqual(first["mtype"], "手动处理")
        self.assertEqual(first["title"], "115 整理：1 个文件需处理")
        self.assertIn("Movie.9.2026.mkv：未识别到媒体，保留源文件", first["text"])
        self.p.post_message.reset_mock()
        self.p.auto_run()
        self.p.post_message.assert_not_called()

    def test_trigger_without_execution_reports_new_problems(self):
        self.scan([self.unclear])
        self.p._allow_external_execute = True
        response = self.p._trigger_api({"source": "openclaw", "execute": True})
        self.assertIn("无可执行计划", response.message)
        self.p._execute_last_plan.assert_not_called()
        self.assertEqual(self.p.post_message.call_args.kwargs["title"], "115 整理：1 个文件需处理")
