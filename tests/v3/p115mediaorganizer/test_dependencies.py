"""Real p115client contract tests with fake cookies and all network access blocked."""
from __future__ import annotations

import os
import tempfile
import unittest
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from unittest.mock import Mock, patch

from .test_plugin import p115_ops_module


def dependencies_installed() -> bool:
    try:
        version("p115client")
        version("python-concurrenttools")
    except PackageNotFoundError:
        return False
    return True


@unittest.skipUnless(
    dependencies_installed() or os.environ.get("P115_REQUIRE_DEPENDENCY_TESTS") == "1",
    "Install the pinned V3 dependencies to run real client contract tests",
)
class P115DependencyContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Missing packages fail (rather than skip) when CI requires these tests.
        if version("p115client") != "0.0.9.7.2":
            raise AssertionError("Expected p115client==0.0.9.7.2")
        if version("python-concurrenttools") != "0.1.9":
            raise AssertionError("Expected python-concurrenttools==0.1.9")
        from concurrenttools import async_conmap, thread_conmap
        from p115client import P115Client

        cls.client_class = P115Client
        if not callable(thread_conmap) or not callable(async_conmap):
            raise AssertionError("Missing concurrenttools 0.1.9 APIs")

    def setUp(self):
        for target in (
            "socket.socket.connect",
            "socket.socket.connect_ex",
            "socket.create_connection",
            "socket.getaddrinfo",
        ):
            patcher = patch(target, side_effect=AssertionError("Network is disabled in dependency tests"))
            patcher.start()
            self.addCleanup(patcher.stop)
        self.ops = p115_ops_module.P115Ops(
            cookie_text="UID=123; CID=test; SEID=test",
            min_interval=0,
            max_retries=0,
        )
        self.assertTrue(self.ops.available, self.ops.import_error)
        self.request = Mock(return_value={"state": True})
        self.ops.client.request = self.request

    def test_cookie_text_and_cookie_file_construct_without_login(self):
        self.assertIsInstance(self.ops.client, self.client_class)
        self.assertFalse(hasattr(self.ops.client, "check_for_relogin"))
        with tempfile.TemporaryDirectory() as directory:
            cookie_path = Path(directory) / "cookies.txt"
            cookie_path.write_text("UID=123; CID=test; SEID=test")
            with patch.object(self.client_class, "login", side_effect=AssertionError("No interactive login")):
                ops = p115_ops_module.P115Ops(cookie_path=str(cookie_path))
                self.assertTrue(ops.available, ops.import_error)

    def test_missing_cookie_does_not_start_login(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(self.client_class, "login", side_effect=AssertionError("No interactive login")):
                ops = p115_ops_module.P115Ops(cookie_path=str(Path(directory) / "missing.txt"))
                self.assertFalse(ops.available)
                self.assertIn("Cookie文件不存在", ops.import_error)

    def test_path_resolution_and_paginated_listing_payloads(self):
        self.request.return_value = {"state": True, "id": "42"}
        self.assertEqual(self.ops.resolve_path("/in"), "42")
        self.request.assert_called_once_with(
            url="https://webapi.115.com/files/getid", params={"path": "/in"}, async_=False,
        )
        self.request.reset_mock()
        self.ops.list_page_size = 2
        entries = [{"fid": "1", "n": "a.mkv"}, {"fid": "2", "n": "b.mkv"}]
        self.request.side_effect = [{"state": True, "data": entries}, {"state": True, "data": []}]
        self.assertEqual(self.ops.list_entries("42"), entries)
        self.assertEqual(self.request.call_count, 2)
        payloads = [call.kwargs["params"] for call in self.request.call_args_list]
        self.assertEqual([p["offset"] for p in payloads], [0, 2])
        self.assertTrue(all(p["cid"] == "42" and p["limit"] == 2 for p in payloads))

    def test_single_and_batch_rename_payloads(self):
        self.ops.rename("1", "a.mkv")
        self.request.assert_called_once_with(
            url="https://webapi.115.com/files/batch_rename", method="POST",
            data={"files_new_name[1]": "a.mkv"}, async_=False,
        )
        self.request.reset_mock()
        self.ops.batch_rename({"1": "a.mkv", "2": "b.mkv"})
        self.request.assert_called_once_with(
            url="https://webapi.115.com/files/batch_rename", method="POST",
            data={"files_new_name[1]": "a.mkv", "files_new_name[2]": "b.mkv"}, async_=False,
        )

    def test_single_and_batch_move_payloads(self):
        self.ops.move("1", "42")
        self.request.assert_called_once_with(
            url="https://webapi.115.com/files/move", method="POST",
            data={"fid[0]": "1", "pid": "42"}, async_=False,
        )
        self.request.reset_mock()
        self.ops.batch_move(["1", "2"], "42")
        self.request.assert_called_once_with(
            url="https://webapi.115.com/files/move", method="POST",
            data={"fid[0]": "1", "fid[1]": "2", "pid": "42"}, async_=False,
        )

    def test_mkdir_and_delete_payloads(self):
        # ensure_dir first checks whether the child already exists.
        self.request.side_effect = [
            {"state": True, "data": []},
            {"state": True, "cid": "42"},
        ]
        self.assertEqual(self.ops.ensure_dir("10", "Movies"), "42")
        self.assertEqual(self.request.call_count, 2)
        self.request.assert_called_with(
            url="https://webapi.115.com/files/add", method="POST",
            data={"cname": "Movies", "pid": "10"}, async_=False,
        )
        self.request.side_effect = None
        self.request.return_value = {"state": True}
        self.request.reset_mock()
        self.ops.delete("1")
        self.request.assert_called_once_with(
            url="https://webapi.115.com/rb/delete", method="POST", data={"fid[0]": "1"}, async_=False,
        )
        self.request.reset_mock()
        self.ops.batch_delete(["1", "2"])
        self.request.assert_called_once_with(
            url="https://webapi.115.com/rb/delete", method="POST",
            data={"fid[0]": "1", "fid[1]": "2"}, async_=False,
        )

    def test_health_check_uses_index_info_and_reports_expired_cookie(self):
        self.assertTrue(self.ops.health_check(force=True)["ok"])
        self.request.assert_called_once_with(
            url="https://webapi.115.com/files/index_info", params={"count_space_nums": 0}, async_=False,
        )
        self.request.reset_mock()
        self.request.return_value = {"state": False, "errno": 99, "message": "登录超时"}
        health = self.ops.health_check(force=True)
        self.assertFalse(health["ok"])
        self.assertIn("Cookie 失效", health["message"])
        self.request.assert_called_once()

    def test_side_effect_api_failure_is_not_retried(self):
        self.ops.max_retries = 3
        self.request.return_value = {"state": False, "errno": 990003, "message": "请稍后"}
        with self.assertRaises(p115_ops_module.P115UnavailableError):
            self.ops.batch_move(["1", "2"], "42")
        self.request.assert_called_once()


if __name__ == "__main__":
    unittest.main()
