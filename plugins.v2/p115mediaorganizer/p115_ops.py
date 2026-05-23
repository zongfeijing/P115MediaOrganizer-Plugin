from __future__ import annotations

import random
import re
import time
from datetime import datetime
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any, Callable, Dict, Iterable, List, Optional

from app.log import logger

from .models import MediaItem


VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi", ".ts", ".m2ts", ".rmvb", ".flv", ".mov", ".wmv", ".webm"}
SKIP_DIR_NAMES = {"@Recycle", "#recycle", "@eaDir", "动画电影", "外语电影", "华语电影", "未分类", "综艺", "日韩剧", "欧美剧", "国产剧"}

# 115 错误码分类（来源：p115client.check_response 的分支）
# 限频 / 临时性繁忙，应当退避后重试
RATE_LIMITED_ERRNOS = {590075, 990003, 990005, 990009, 990019,
                       40110000, 40140105, 40140116, 40140117}
# 登录态失效，不应重试，立即暴露给用户
LOGIN_REQUIRED_ERRNOS = {99, 990001, 40101004, 40101032}

# 抗封锁参数默认值的唯一来源：__init__.py 的类属性 / _default_config / P115Ops.__init__ 都从这里读
ANTI_BLOCK_DEFAULTS: Dict[str, Any] = {
    "min_request_interval_ms": 300,
    "max_retries": 3,
    "retry_base_seconds": 1.5,
    "jitter_ratio": 0.3,
    "list_page_size": 200,
}

# rename → move 之间的最小间隔，防止用户把 min_interval 设为 0 时 rename 还未在 115 服务端生效就触发 move
RENAME_MOVE_MIN_GAP = 0.05


class P115UnavailableError(RuntimeError):
    pass


class P115Ops:
    """115 客户端封装：内置限速、指数退避重试、cookie 健康检查、目录分页。"""

    def __init__(
        self,
        cookie_path: str = "",
        cookie_text: str = "",
        min_interval: float = ANTI_BLOCK_DEFAULTS["min_request_interval_ms"] / 1000.0,
        max_retries: int = ANTI_BLOCK_DEFAULTS["max_retries"],
        retry_base: float = ANTI_BLOCK_DEFAULTS["retry_base_seconds"],
        jitter_ratio: float = ANTI_BLOCK_DEFAULTS["jitter_ratio"],
        list_page_size: int = ANTI_BLOCK_DEFAULTS["list_page_size"],
    ):
        self.cookie_path = cookie_path
        self.cookie_text = cookie_text
        self.client = None
        self.import_error = ""
        self._mkdir_cache: Dict[str, str] = {}

        # 抗封锁参数
        self.min_interval = max(0.0, float(min_interval))
        self.max_retries = max(0, int(max_retries))
        self.retry_base = max(0.1, float(retry_base))
        self.jitter_ratio = max(0.0, min(1.0, float(jitter_ratio)))
        self.list_page_size = max(50, int(list_page_size))

        # 节流 / 健康检查状态
        self._last_call_ts = 0.0
        self._cookie_alive: Optional[bool] = None
        self._last_health_msg = ""
        self._last_health_at = 0.0

        self._init_client()

    @property
    def available(self) -> bool:
        return self.client is not None and not self.import_error

    @property
    def cookie_alive(self) -> Optional[bool]:
        return self._cookie_alive

    @property
    def last_health_message(self) -> str:
        return self._last_health_msg

    @property
    def last_health_at(self) -> float:
        return self._last_health_at

    # ---- 初始化 ----

    def _init_client(self):
        P115Client = self._load_p115_client()
        if not P115Client:
            return
        try:
            self.client = self._construct_client(P115Client)
        except Exception as err:
            self.import_error = f"p115client初始化失败：{err}"

    def _construct_client(self, P115Client):
        if self.cookie_text:
            return self._construct_with_relogin(P115Client, self.cookie_text)
        cookie_file = Path(self.cookie_path) if self.cookie_path else None
        if not cookie_file or not cookie_file.exists():
            self.import_error = f"115 Cookie文件不存在：{self.cookie_path}"
            return None
        return self._construct_with_relogin(P115Client, cookie_file)

    @staticmethod
    def _construct_with_relogin(P115Client, arg):
        # 优先启用 check_for_relogin，让 p115client 自身在 cookie 过期时尝试自动续命
        try:
            return P115Client(arg, check_for_relogin=True)
        except TypeError:
            pass
        try:
            return P115Client(arg)
        except TypeError:
            return P115Client(cookies=arg)

    def _load_p115_client(self):
        try:
            from p115client import P115Client
            return P115Client
        except ImportError as err:
            self.import_error = (
                f"p115client 未安装：{err}。请在 MoviePilot 容器内执行 "
                f"`pip install 'p115client>=0.0.8'`，或将其加入 requirements 后重启容器。"
            )
            return None
        except Exception as err:
            self.import_error = f"p115client导入失败：{err}"
            return None

    # ---- 限速 / 抖动 / 重试 ----

    def _throttle(self):
        """两次 API 调用之间至少 min_interval × (1 ± jitter)。"""
        now = time.monotonic()
        if self.min_interval > 0:
            elapsed = now - self._last_call_ts
            target = self._jitter(self.min_interval)
            if elapsed < target:
                time.sleep(target - elapsed)
        self._last_call_ts = time.monotonic()

    def _jitter(self, secs: float) -> float:
        if self.jitter_ratio <= 0:
            return secs
        return secs * random.uniform(1.0 - self.jitter_ratio, 1.0 + self.jitter_ratio)

    def _classify_error(self, exc: BaseException) -> str:
        """返回 'retry' / 'login' / 'fatal'。"""
        try:
            from p115client import P115LoginError, P115OperationalError  # type: ignore
            if isinstance(exc, P115LoginError):
                return "login"
            if isinstance(exc, P115OperationalError):
                return "retry"
        except Exception:
            pass
        text = str(exc)
        errno = self._extract_errno(text)
        if errno in LOGIN_REQUIRED_ERRNOS:
            return "login"
        if errno in RATE_LIMITED_ERRNOS:
            return "retry"
        lowered = text.lower()
        if any(k in lowered for k in ("rate limit", "too many", "frequent",
                                       "请求过于频繁", "请稍后", "ebusy")):
            return "retry"
        if any(k in lowered for k in ("cookie 失效", "cookie失效", "请重新登录",
                                       "登陆超时", "登录超时", "未登录")):
            return "login"
        return "fatal"

    @staticmethod
    def _extract_errno(text: str) -> int:
        # 优先信任 errno= / errno: 前缀（任意长度数字）
        match = re.search(r"errno[=:\s]+(\d+)", text, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except Exception:
                return 0
        # 兜底：只匹配 115 实际在用的 errno 形状，避免误吞 file_id 等大数字
        # - 40\d{6}（4010xxxx / 4011xxxx / 4014xxxx 系列）
        # - 5900\d{2}（590075 类）
        # - 99\d{4}（990001 ~ 999999）
        match = re.search(r"(?<!\d)(40\d{6}|5900\d{2}|99\d{4})(?!\d)", text)
        try:
            return int(match.group(1)) if match else 0
        except Exception:
            return 0

    def _call(self, label: str, fn: Callable, *args, retries: Optional[int] = None, **kwargs):
        """统一调度：限速 + 重试 + 状态跟踪。

        TypeError 直接透传（用于上层做签名兼容性探测），不计入重试。
        `retries` 显式传入时覆盖 `self.max_retries`；副作用 API（move/rename/delete/mkdir）
        应传 `retries=0` 避免"实际已成功但响应被解读为限频"导致的重复执行误报。
        """
        effective_retries = self.max_retries if retries is None else max(0, int(retries))
        last_exc: Optional[BaseException] = None
        for attempt in range(effective_retries + 1):
            self._throttle()
            try:
                result = fn(*args, **kwargs)
                self._raise_if_failed(result)
                self._cookie_alive = True
                return result
            except TypeError:
                # 签名不匹配，交给上层探测
                raise
            except Exception as exc:
                last_exc = exc
                kind = self._classify_error(exc)
                if kind == "login":
                    self._cookie_alive = False
                    self._last_health_msg = f"Cookie 失效：{exc}"
                    self._last_health_at = time.time()
                    raise P115UnavailableError(self._last_health_msg)
                if kind != "retry" or attempt >= effective_retries:
                    if isinstance(exc, P115UnavailableError):
                        raise
                    raise P115UnavailableError(str(exc))
                sleep_secs = self._jitter(self.retry_base * (2 ** attempt))
                logger.warning(
                    f"【115云端媒体整理】{label} 第 {attempt + 1} 次失败，"
                    f"{sleep_secs:.1f}s 后重试：{exc}"
                )
                time.sleep(sleep_secs)
        raise P115UnavailableError(str(last_exc) if last_exc else "未知错误")

    # ---- 健康检查 ----

    def health_check(self, force: bool = False) -> Dict[str, Any]:
        """轻量探针；30 秒内若有有效结果直接复用，避免页面刷新都打一次接口。"""
        if not self.available:
            return {
                "ok": False,
                "message": self.import_error or "p115client不可用",
                "checked_at": "",
            }
        now = time.time()
        if (not force
                and self._cookie_alive is not None
                and self._last_health_at > 0
                and now - self._last_health_at < 30):
            return self._health_payload()
        try:
            client = self.require_client()
            probe = getattr(client, "fs_space_info", None) or getattr(client, "fs_index_info", None)
            # 健康检查是"现在健不健康"语义，且经常在 UI 同步调用；只容忍一次瞬时抖动，
            # 不走默认 max_retries，避免按钮卡 ~10s 才返回
            if probe is not None:
                self._call("health_check", probe, retries=1)
            else:
                # 退化：列根目录首条，刚好走 _call 也能验证 cookie
                fs_files = getattr(client, "fs_files", None)
                if not fs_files:
                    raise P115UnavailableError("未找到健康检查所需的 API")
                try:
                    self._call("health_check.fs_files", fs_files,
                               {"cid": 0, "limit": 1, "offset": 0}, retries=1)
                except TypeError:
                    self._call("health_check.fs_files", fs_files, 0, retries=1)
            self._cookie_alive = True
            self._last_health_msg = "Cookie 正常"
        except P115UnavailableError as exc:
            kind = self._classify_error(exc)
            self._cookie_alive = False
            self._last_health_msg = (
                f"Cookie 失效：{exc}" if kind == "login" else f"健康检查失败：{exc}"
            )
        except Exception as exc:
            self._cookie_alive = False
            self._last_health_msg = f"健康检查失败：{exc}"
        self._last_health_at = time.time()
        return self._health_payload()

    def _health_payload(self) -> Dict[str, Any]:
        return {
            "ok": bool(self._cookie_alive),
            "message": self._last_health_msg or ("Cookie 正常" if self._cookie_alive else "Cookie 未检查"),
            "checked_at": (datetime.fromtimestamp(self._last_health_at).strftime("%Y-%m-%d %H:%M:%S")
                           if self._last_health_at else ""),
        }

    # ---- 基础 API ----

    def require_client(self):
        if not self.available:
            raise P115UnavailableError(self.import_error or "p115client不可用")
        return self.client

    def resolve_path(self, path: str) -> str:
        if path in ("", "/"):
            return "0"
        client = self.require_client()
        method = getattr(client, "fs_dir_getid", None)
        if not method:
            raise P115UnavailableError("当前p115client未找到可用的路径解析API")
        result = self._call(f"resolve_path({path})", method, path)
        cid = result.get("id") if isinstance(result, dict) else None
        if not cid:
            raise P115UnavailableError(f"路径不存在或不是目录：{path}")
        return str(cid)

    def list_entries(self, cid: str) -> List[Any]:
        """分页拉取目录内容并合并，避免单次响应过大或漏数据。"""
        client = self.require_client()
        method = None
        for method_name in ("fs_files", "fs_list", "list", "listdir", "iterdir"):
            method = getattr(client, method_name, None)
            if method:
                break
        if not method:
            raise P115UnavailableError("当前p115client未找到可用的目录列表API")

        all_entries: List[Any] = []
        offset = 0
        page_size = self.list_page_size
        used_dict_payload = True
        while True:
            try:
                if used_dict_payload:
                    payload = {"cid": cid, "limit": page_size, "offset": offset, "show_dir": 1}
                    result = self._call(
                        f"list_entries({cid}, offset={offset})", method, payload,
                    )
                else:
                    # 老版本不支持 dict payload，只能一次性拉取
                    result = self._call(f"list_entries({cid})", method, cid)
            except TypeError:
                if used_dict_payload:
                    used_dict_payload = False
                    continue
                # 再退一步：cid=cid 关键字
                try:
                    result = self._call(f"list_entries({cid})", method, cid=cid)
                except TypeError:
                    result = self._call(f"list_entries({cid})", method, pid=cid)
            page = self._extract_entries(result)
            if not page:
                break
            all_entries.extend(page)
            if not used_dict_payload:
                break
            if len(page) < page_size:
                break
            offset += len(page)
            if offset >= 50000:
                logger.warning(
                    f"【115云端媒体整理】list_entries 超过 50000 条，提前终止：cid={cid}"
                )
                break
        return all_entries

    def walk_media_items(
        self,
        source_cid: str,
        source_path: str,
        max_depth: int,
        min_file_size: int = 0,
        exclude_keywords: Optional[Iterable[str]] = None,
        max_items: int = 0,
    ) -> List[MediaItem]:
        items: List[MediaItem] = []
        excludes = [keyword.lower() for keyword in (exclude_keywords or []) if keyword]

        def walk(cid: str, current_path: str, depth: int):
            if max_items and len(items) >= max_items:
                return
            if depth > max_depth:
                return
            try:
                entries = self.list_entries(cid)
            except P115UnavailableError as err:
                logger.warning(
                    f"【115云端媒体整理】列出目录失败，跳过该子树：path={current_path}，原因：{err}"
                )
                return
            for entry in entries:
                name = self.entry_name(entry)
                if not name:
                    continue
                is_dir = self.is_folder(entry)
                path_hint = str(PurePosixPath(current_path) / name)
                if is_dir:
                    if name in SKIP_DIR_NAMES:
                        continue
                    walk(self.entry_cid(entry), path_hint, depth + 1)
                    continue

                ext = PurePosixPath(name).suffix.lower()
                if ext not in VIDEO_EXTENSIONS:
                    continue
                if self.entry_size(entry) < min_file_size:
                    continue
                if any(keyword in path_hint.lower() for keyword in excludes):
                    continue
                items.append(self._to_media_item(entry, cid, path_hint))
                if max_items and len(items) >= max_items:
                    return

        walk(source_cid, source_path, 0)
        return items

    def ensure_dir(self, parent_cid: str, name: str) -> str:
        key = f"{parent_cid}/{name}"
        if key in self._mkdir_cache:
            return self._mkdir_cache[key]
        existing = self.find_child(parent_cid, name, folder=True)
        if existing:
            cid = self.entry_cid(existing)
            self._mkdir_cache[key] = cid
            return cid
        client = self.require_client()
        for method_name in ("fs_mkdir", "mkdir", "makedirs"):
            method = getattr(client, method_name, None)
            if not method:
                continue
            result = self._invoke_with_signatures(
                f"mkdir({name})", method,
                (lambda: (name,), {"pid": parent_cid}),
                (lambda: ({"pid": parent_cid, "name": name},), {}),
                (lambda: (), {"parent_id": parent_cid, "name": name}),
                retries=0,
            )
            cid = self._extract_created_cid(result) or self.entry_cid(
                self.find_child(parent_cid, name, folder=True)
            )
            if cid:
                self._mkdir_cache[key] = cid
                return cid
        raise P115UnavailableError("当前p115client未找到可用的创建目录API")

    def find_child(self, parent_cid: str, name: str, folder: Optional[bool] = None) -> Optional[Any]:
        for entry in self.list_entries(parent_cid):
            if self.entry_name(entry) != name:
                continue
            if folder is None or self.is_folder(entry) == folder:
                return entry
        return None

    def list_empty_dirs_bottom_up(self, root_cid: str, max_depth: int) -> List[str]:
        empty_dirs: List[str] = []

        def walk(cid: str, depth: int) -> bool:
            if depth > max_depth:
                return False
            try:
                entries = self.list_entries(cid)
            except P115UnavailableError as err:
                logger.warning(
                    f"【115云端媒体整理】列出目录失败，无法判定是否为空：cid={cid}，原因：{err}"
                )
                return False
            has_file = False
            all_child_dirs_empty = True
            for entry in entries:
                if self.is_folder(entry):
                    child_empty = walk(self.entry_cid(entry), depth + 1)
                    all_child_dirs_empty = all_child_dirs_empty and child_empty
                else:
                    has_file = True
            is_empty = not has_file and all_child_dirs_empty
            if depth > 0 and is_empty:
                empty_dirs.append(cid)
            return is_empty

        walk(root_cid, 0)
        return empty_dirs

    def delete(self, fid_or_cid: str):
        client = self.require_client()
        for method_name in ("fs_delete", "delete", "remove"):
            method = getattr(client, method_name, None)
            if not method:
                continue
            return self._invoke_with_signatures(
                f"delete({fid_or_cid})", method,
                (lambda: ([fid_or_cid],), {}),
                (lambda: (fid_or_cid,), {}),
                retries=0,
            )
        raise P115UnavailableError("当前p115client未找到可用的删除API")

    def rename(self, fid: str, name: str):
        client = self.require_client()
        for method_name in ("fs_rename", "rename"):
            method = getattr(client, method_name, None)
            if not method:
                continue
            return self._invoke_with_signatures(
                f"rename({fid})", method,
                (lambda: ((fid, name),), {}),
                (lambda: ({"fid": fid, "file_name": name},), {}),
                (lambda: (), {"file_id": fid, "name": name}),
                retries=0,
            )
        raise P115UnavailableError("当前p115client未找到可用的重命名API")

    def move(self, fid: str, target_cid: str):
        client = self.require_client()
        for method_name in ("fs_move", "move"):
            method = getattr(client, method_name, None)
            if not method:
                continue
            return self._invoke_with_signatures(
                f"move({fid}->{target_cid})", method,
                (lambda: ([fid],), {"pid": target_cid}),
                (lambda: (fid,), {"pid": target_cid}),
                (lambda: (), {"file_id": fid, "parent_id": target_cid}),
                retries=0,
            )
        raise P115UnavailableError("当前p115client未找到可用的移动API")

    def _invoke_with_signatures(self, label: str, method: Callable, *variants,
                                 retries: Optional[int] = None):
        """依次尝试若干种签名，TypeError 不计入重试，进入下一种。"""
        last_type_err: Optional[TypeError] = None
        for args_fn, kwargs in variants:
            try:
                args = args_fn()
                return self._call(label, method, *args, retries=retries, **kwargs)
            except TypeError as err:
                last_type_err = err
                continue
        raise P115UnavailableError(
            f"{label} 所有签名均不兼容：{last_type_err}" if last_type_err else f"{label} 调用失败"
        )

    def execute_move(self, plan: Dict[str, Any], conflict_strategy: str = "skip") -> Dict[str, Any]:
        source_id = plan.get("source_cid") if plan.get("source_is_dir") else plan.get("source_fid")
        if not source_id:
            return {"success": False, "message": "源文件ID为空"}
        target_parent = plan.get("target_parent_cid")
        if not target_parent:
            return {"success": False, "message": "目标父目录CID为空"}

        final_parent = self.ensure_dir(target_parent, plan.get("target_dir_name"))
        if plan.get("target_season_dir_name"):
            final_parent = self.ensure_dir(final_parent, plan.get("target_season_dir_name"))

        target_name = plan.get("target_name") or plan.get("source_name")
        if not plan.get("source_is_dir"):
            conflict = self.find_child(final_parent, target_name, folder=False)
            if conflict and conflict_strategy == "skip":
                return {"success": False, "skipped": True, "message": f"目标已存在：{target_name}"}
            if conflict and conflict_strategy == "rename_with_suffix":
                target_name = self._next_available_name(final_parent, target_name, False)

        # rename → move 之间至少留 RENAME_MOVE_MIN_GAP，防止用户把 min_interval 调到 0 后
        # rename 还没在 115 服务端生效就触发 move 失败；正常 min_interval 已 >= 此值时 _throttle 就够了
        if target_name != plan.get("source_name"):
            self.rename(source_id, target_name)
            elapsed = time.monotonic() - self._last_call_ts
            if elapsed < RENAME_MOVE_MIN_GAP:
                time.sleep(RENAME_MOVE_MIN_GAP - elapsed)
        self.move(source_id, final_parent)
        return {"success": True, "message": "完成",
                "target_name": target_name, "target_parent_cid": final_parent}

    def _next_available_name(self, parent_cid: str, name: str, folder: bool) -> str:
        path = PurePosixPath(name)
        stem = path.stem if path.suffix else name
        suffix = path.suffix
        for index in range(1, 1000):
            candidate = f"{stem} ({index}){suffix}"
            if not self.find_child(parent_cid, candidate, folder=folder):
                return candidate
        raise P115UnavailableError(f"无法生成不冲突名称：{name}")

    def _to_media_item(self, entry: Any, parent_cid: str, path_hint: str) -> MediaItem:
        name = self.entry_name(entry)
        return MediaItem(
            fid=self.entry_fid(entry),
            cid=self.entry_cid(entry),
            name=name,
            ext=PurePosixPath(name).suffix.lower() or None,
            size=self.entry_size(entry),
            is_dir=self.is_folder(entry),
            parent_cid=parent_cid,
            path_hint=path_hint,
        )

    # ---- 静态工具 ----

    @staticmethod
    def _extract_entries(result: Any) -> List[Any]:
        if result is None:
            return []
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            for key in ("data", "list", "files", "items"):
                value = result.get(key)
                if isinstance(value, list):
                    return value
                if isinstance(value, dict):
                    for inner_key in ("list", "items"):
                        inner = value.get(inner_key)
                        if isinstance(inner, list):
                            return inner
        try:
            return list(result)
        except Exception:
            return []

    @staticmethod
    def _extract_created_cid(result: Any) -> str:
        if isinstance(result, dict):
            for key in ("cid", "file_id", "fid", "id"):
                if result.get(key):
                    return str(result.get(key))
            data = result.get("data")
            if isinstance(data, dict):
                return P115Ops._extract_created_cid(data)
        return ""

    @staticmethod
    def _raise_if_failed(result: Any):
        if not isinstance(result, dict):
            return
        state = result.get("state")
        errno = result.get("errno", result.get("errNo"))
        if state is False or (errno not in (None, "", 0, "0")):
            message = result.get("error") or result.get("message") or result.get("msg") or str(result)
            prefix = f"errno={errno} " if errno not in (None, "", 0, "0") else ""
            raise P115UnavailableError(f"{prefix}{message}")

    @staticmethod
    def _get(entry: Any, names: Iterable[str], default: Any = None) -> Any:
        for name in names:
            if isinstance(entry, dict) and name in entry:
                return entry.get(name)
            if hasattr(entry, name):
                return getattr(entry, name)
        return default

    def entry_name(self, entry: Any) -> str:
        return str(self._get(entry, ("name", "n", "file_name", "filename"), "") or "")

    def entry_fid(self, entry: Any) -> str:
        return str(self._get(entry, ("fid", "file_id", "id", "pickcode"), "") or "")

    def entry_cid(self, entry: Any) -> str:
        return str(self._get(entry, ("cid", "category_id", "id", "fid", "file_id"), "") or "")

    def entry_size(self, entry: Any) -> int:
        try:
            return int(self._get(entry, ("size", "s", "file_size"), 0) or 0)
        except Exception:
            return 0

    def is_folder(self, entry: Any) -> bool:
        value = self._get(entry, ("is_dir", "is_directory", "is_folder", "folder"), None)
        if value is not None:
            return bool(value)
        if self._get(entry, ("cid", "category_id"), None) and not self._get(entry, ("fid", "file_id", "pickcode"), None):
            return True
        return str(self._get(entry, ("type", "file_category"), "")).lower() in {"folder", "dir", "0"}
