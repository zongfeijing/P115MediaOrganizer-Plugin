from __future__ import annotations

import time
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any, Dict, Iterable, List, Optional

from .models import MediaItem


VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi", ".ts", ".m2ts", ".rmvb", ".flv", ".mov", ".wmv", ".webm"}
SKIP_DIR_NAMES = {"@Recycle", "#recycle", "@eaDir", "动画电影", "外语电影", "华语电影", "未分类", "综艺", "日韩剧", "欧美剧", "国产剧"}


class P115UnavailableError(RuntimeError):
    pass


class P115Ops:
    def __init__(self, cookie_path: str = "", cookie_text: str = ""):
        self.cookie_path = cookie_path
        self.cookie_text = cookie_text
        self.client = None
        self.backend = ""
        self.import_error = ""
        self._mkdir_cache: Dict[str, str] = {}
        self._mp_item_cache: Dict[str, Any] = {}
        self._init_client()

    @property
    def available(self) -> bool:
        return self.client is not None and not self.import_error

    def _init_client(self):
        mp_error = self._init_moviepilot_client()
        if self.client:
            return
        cookie_error = self._init_cookie_client()
        if self.client:
            return
        errors = [error for error in (mp_error, cookie_error) if error]
        self.import_error = "；".join(errors) or "MoviePilot 115未登录，且p115client Cookie不可用"

    def _init_moviepilot_client(self) -> str:
        try:
            from app.modules.filemanager.storages.u115 import U115Pan

            storage = U115Pan()
            if not storage.check():
                return "MoviePilot 115未登录或登录凭证不可用"
            self.client = storage
            self.backend = "moviepilot"
            return ""
        except Exception as err:
            return f"MoviePilot 115初始化失败：{err}"

    def _init_cookie_client(self) -> str:
        try:
            from p115client import P115Client
        except Exception as err:
            return f"p115client导入失败：{err}"

        try:
            if self.cookie_text:
                self.client = P115Client(self.cookie_text)
                self.backend = "p115client"
                return ""
            cookie_file = Path(self.cookie_path)
            if not self.cookie_path or not cookie_file.exists():
                return f"115 Cookie文件不存在：{self.cookie_path}"
            self.client = P115Client(cookie_file)
            self.backend = "p115client"
            return ""
        except TypeError:
            try:
                self.client = P115Client(cookies=Path(self.cookie_path))
                self.backend = "p115client"
                return ""
            except Exception as err:
                return f"p115client初始化失败：{err}"
        except Exception as err:
            return f"p115client初始化失败：{err}"

    def resolve_path(self, path: str) -> str:
        client = self.require_client()
        if self.backend == "moviepilot":
            item = client.get_item(Path(path))
            if not item or getattr(item, "type", "") != "dir":
                raise P115UnavailableError(f"路径不存在或不是目录：{path}")
            self._moviepilot_remember(item)
            return str(item.fileid)

        method = getattr(client, "fs_dir_getid", None)
        if not method:
            raise P115UnavailableError("当前p115client未找到可用的路径解析API")
        result = method(path)
        self._raise_if_failed(result)
        cid = result.get("id") if isinstance(result, dict) else None
        if not cid:
            raise P115UnavailableError(f"路径不存在或不是目录：{path}")
        return str(cid)

    def require_client(self):
        if not self.available:
            raise P115UnavailableError(self.import_error or "115连接不可用")
        return self.client

    def list_entries(self, cid: str) -> List[Any]:
        client = self.require_client()
        if self.backend == "moviepilot":
            return self._moviepilot_list_entries(cid)
        for method_name in ("fs_files", "fs_list", "list", "listdir", "iterdir"):
            method = getattr(client, method_name, None)
            if not method:
                continue
            try:
                result = method(cid)
            except TypeError:
                try:
                    result = method(cid=cid)
                except TypeError:
                    result = method(pid=cid)
            return self._extract_entries(result)
        raise P115UnavailableError("当前p115client未找到可用的目录列表API")

    def walk_media_items(
        self,
        source_cid: str,
        source_path: str,
        max_depth: int,
        move_whole_dirs: bool,
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
            for entry in self.list_entries(cid):
                name = self.entry_name(entry)
                if not name:
                    continue
                is_dir = self.is_folder(entry)
                path_hint = str(PurePosixPath(current_path) / name)
                if is_dir:
                    if name in SKIP_DIR_NAMES:
                        continue
                    if move_whole_dirs:
                        items.append(self._to_media_item(entry, cid, path_hint))
                    else:
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
        if self.backend == "moviepilot":
            parent_path = self._moviepilot_path(parent_cid)
            folder = client.get_folder(parent_path / name)
            if folder:
                self._moviepilot_remember(folder)
                cid = str(folder.fileid)
                self._mkdir_cache[key] = cid
                return cid
            raise P115UnavailableError(f"创建目录失败：{parent_path / name}")
        for method_name in ("fs_mkdir", "mkdir", "makedirs"):
            method = getattr(client, method_name, None)
            if not method:
                continue
            try:
                result = method(name, pid=parent_cid)
            except TypeError:
                try:
                    result = method({"pid": parent_cid, "name": name})
                except TypeError:
                    result = method(parent_id=parent_cid, name=name)
            self._raise_if_failed(result)
            cid = self._extract_created_cid(result) or self.entry_cid(self.find_child(parent_cid, name, folder=True))
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
            entries = self.list_entries(cid)
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
        if self.backend == "moviepilot":
            item = self._moviepilot_entry(fid_or_cid)
            if not item:
                raise P115UnavailableError(f"删除失败，找不到项目：{fid_or_cid}")
            return client.delete(item)
        for method_name in ("fs_delete", "delete", "remove"):
            method = getattr(client, method_name, None)
            if not method:
                continue
            try:
                result = method([fid_or_cid])
            except TypeError:
                result = method(fid_or_cid)
            self._raise_if_failed(result)
            return result
        raise P115UnavailableError("当前p115client未找到可用的删除API")

    def rename(self, fid: str, name: str):
        client = self.require_client()
        if self.backend == "moviepilot":
            item = self._moviepilot_entry(fid)
            if not item:
                raise P115UnavailableError(f"重命名失败，找不到项目：{fid}")
            if not client.rename(item, name):
                raise P115UnavailableError(f"重命名失败：{item.name} -> {name}")
            item.name = name
            item.path = (Path(item.path).parent / name).as_posix() + ("/" if getattr(item, "type", "") == "dir" else "")
            self._moviepilot_remember(item)
            return True
        for method_name in ("fs_rename", "rename"):
            method = getattr(client, method_name, None)
            if not method:
                continue
            try:
                result = method((fid, name))
            except Exception:
                try:
                    result = method({"fid": fid, "file_name": name})
                except TypeError:
                    result = method(file_id=fid, name=name)
            self._raise_if_failed(result)
            return result
        raise P115UnavailableError("当前p115client未找到可用的重命名API")

    def move(self, fid: str, target_cid: str):
        client = self.require_client()
        if self.backend == "moviepilot":
            item = self._moviepilot_entry(fid)
            target_path = self._moviepilot_path(target_cid)
            if not item:
                raise P115UnavailableError(f"移动失败，找不到项目：{fid}")
            if not client.move(item, target_path, item.name):
                raise P115UnavailableError(f"移动失败：{item.name} -> {target_path}")
            item.path = (target_path / item.name).as_posix() + ("/" if getattr(item, "type", "") == "dir" else "")
            self._moviepilot_remember(item)
            return True
        for method_name in ("fs_move", "move"):
            method = getattr(client, method_name, None)
            if not method:
                continue
            try:
                result = method([fid], pid=target_cid)
            except Exception:
                try:
                    result = method(fid, pid=target_cid)
                except TypeError:
                    result = method(file_id=fid, parent_id=target_cid)
            self._raise_if_failed(result)
            return result
        raise P115UnavailableError("当前p115client未找到可用的移动API")

    def execute_move(self, plan: Dict[str, Any], conflict_strategy: str = "skip") -> Dict[str, Any]:
        if self.backend == "moviepilot":
            return self._moviepilot_execute_move(plan, conflict_strategy)

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

        if target_name != plan.get("source_name"):
            self.rename(source_id, target_name)
            time.sleep(0.1)
        self.move(source_id, final_parent)
        return {"success": True, "message": "完成", "target_name": target_name, "target_parent_cid": final_parent}


    def _moviepilot_execute_move(self, plan: Dict[str, Any], conflict_strategy: str = "skip") -> Dict[str, Any]:
        source_path = plan.get("source_path") or plan.get("path_hint")
        source_item = self.client.get_item(Path(source_path)) if source_path else None
        if not source_item:
            return {"success": False, "message": f"源文件不存在：{source_path}"}
        self._moviepilot_remember(source_item)

        target_category_path = plan.get("target_category_path")
        if not target_category_path:
            target_parent = plan.get("target_parent_cid")
            target_category_path = self._moviepilot_path(target_parent).as_posix() if target_parent else ""
        if not target_category_path:
            return {"success": False, "message": "目标分类路径为空"}

        target_dir = self.client.get_folder(Path(target_category_path) / str(plan.get("target_dir_name") or ""))
        if not target_dir:
            return {"success": False, "message": f"目标目录创建失败：{target_category_path}"}
        if plan.get("target_season_dir_name"):
            target_dir = self.client.get_folder(Path(target_dir.path) / str(plan.get("target_season_dir_name")))
            if not target_dir:
                return {"success": False, "message": f"季目录创建失败：{plan.get('target_season_dir_name')}"}

        target_name = plan.get("target_name") or plan.get("source_name")
        if not plan.get("source_is_dir"):
            conflict = self.client.get_item(Path(target_dir.path) / target_name)
            if conflict and conflict_strategy == "skip":
                return {"success": False, "skipped": True, "message": f"目标已存在：{target_name}"}
            if conflict and conflict_strategy == "rename_with_suffix":
                target_name = self._moviepilot_next_available_name(Path(target_dir.path), target_name, False)

        if not self.client.move(source_item, Path(target_dir.path), target_name):
            return {"success": False, "message": f"移动失败：{source_item.name} -> {Path(target_dir.path) / target_name}"}
        return {"success": True, "message": "完成", "target_name": target_name, "target_parent_cid": str(target_dir.fileid)}

    def _moviepilot_next_available_name(self, parent_path: Path, name: str, folder: bool) -> str:
        path = PurePosixPath(name)
        stem = path.stem if path.suffix else name
        suffix = path.suffix
        for index in range(1, 1000):
            candidate = f"{stem} ({index}){suffix}"
            item = self.client.get_item(parent_path / candidate)
            if not item or ((getattr(item, "type", "") == "dir") != folder):
                return candidate
        raise P115UnavailableError(f"无法生成不冲突名称：{name}")

    def _next_available_name(self, parent_cid: str, name: str, folder: bool) -> str:
        path = PurePosixPath(name)
        stem = path.stem if path.suffix else name
        suffix = path.suffix
        for index in range(1, 1000):
            candidate = f"{stem} ({index}){suffix}"
            if not self.find_child(parent_cid, candidate, folder=folder):
                return candidate
        raise P115UnavailableError(f"无法生成不冲突名称：{name}")


    def _moviepilot_list_entries(self, cid: str) -> List[Any]:
        from app.schemas import FileItem
        fileitem = FileItem(storage="u115", fileid=str(cid), path=self._moviepilot_path(cid).as_posix(), type="dir")
        entries = self.client.list(fileitem)
        return [self._moviepilot_to_entry(entry, cid) for entry in entries]

    def _moviepilot_to_entry(self, item: Any, parent_cid: str) -> Dict[str, Any]:
        self._moviepilot_remember(item)
        return {
            "name": getattr(item, "name", ""),
            "fid": str(getattr(item, "fileid", "") or ""),
            "cid": str(getattr(item, "fileid", "") or ""),
            "parent_cid": str(parent_cid or ""),
            "path": str(getattr(item, "path", "") or ""),
            "is_dir": getattr(item, "type", "") == "dir",
            "size": int(getattr(item, "size", 0) or 0),
            "_fileitem": item,
        }

    def _moviepilot_entry(self, fileid: str) -> Optional[Any]:
        item = self._moviepilot_item_by_id(fileid)
        if item:
            return item
        parent_cid = self._moviepilot_parent_cid(fileid)
        for entry in self.list_entries(parent_cid):
            if self.entry_cid(entry) == str(fileid) or self.entry_fid(entry) == str(fileid):
                return entry.get("_fileitem") if isinstance(entry, dict) else entry
        return None

    def _moviepilot_path(self, cid: str) -> Path:
        if not cid or str(cid) == "0":
            return Path("/")
        item = self._moviepilot_item_by_id(cid)
        if not item:
            raise P115UnavailableError(f"找不到115目录：{cid}")
        return Path(item.path)

    def _moviepilot_parent_cid(self, fileid: str) -> str:
        item = self._moviepilot_item_by_id(fileid)
        parent = getattr(item, "parent_fileid", "") if item else ""
        if parent:
            return str(parent)
        path = Path(getattr(item, "path", "/") or "/") if item else Path("/")
        parent_item = self.client.get_item(path.parent) if path.parent.as_posix() != path.as_posix() else None
        return str(getattr(parent_item, "fileid", "0") or "0")

    def _moviepilot_item_by_id(self, fileid: str) -> Optional[Any]:
        return self._mp_item_cache.get(str(fileid))

    def _moviepilot_remember(self, item: Any):
        fileid = str(getattr(item, "fileid", "") or "")
        if fileid:
            self._mp_item_cache[fileid] = item

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
            for key in ("cid", "file_id", "fid", "id", "file_id"):
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
            raise P115UnavailableError(message)

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
