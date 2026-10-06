"""Small thread-safe task state; scheduling is owned by MoviePilot."""

from __future__ import annotations

import threading
import time
from uuid import uuid4


class TaskCancelled(RuntimeError):
    pass


class TaskState:
    def __init__(self):
        self.lock = threading.RLock()
        self.cancel = threading.Event()
        self._state = {"status": "idle", "message": "尚未运行任务"}

    def reserve(self, kind: str) -> dict:
        with self.lock:
            if self._state["status"] in ("queued", "running", "stopping"):
                raise ValueError("已有任务正在运行，请等待完成或先停止")
            self.cancel.clear()
            self._state = {
                "id": uuid4().hex,
                "kind": kind,
                "status": "queued",
                "phase": "queued",
                "message": "任务已排队",
                "started_at": time.time(),
                "updated_at": time.time(),
                "completed": 0,
                "total": 0,
                "success": 0,
                "failed": 0,
            }
            return self.snapshot()

    def snapshot(self) -> dict:
        with self.lock:
            return dict(self._state)

    def update(self, **changes):
        with self.lock:
            self._state.update(changes, updated_at=time.time())

    def request_stop(self):
        with self.lock:
            if self._state["status"] not in ("queued", "running", "stopping"):
                return False
            self.cancel.set()
            self.update(
                status="stopping",
                message="正在停止：会完成当前批次，不会中断已开始的移动操作",
            )
            return True

    def checkpoint(self):
        if self.cancel.is_set():
            message = (
                "扫描已停止，未生成新计划；请重新生成预览"
                if self.snapshot().get("kind")
                in ("scan", "dry_run_all", "dry_run_movie", "dry_run_tv")
                else "任务已停止，已完成项目保留；未执行项目需重新确认后执行"
            )
            raise TaskCancelled(message)
