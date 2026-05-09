from __future__ import annotations

import re
import uuid
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List

from .category_mapper import CategoryMapper
from .models import MediaItem, OrganizePlan


class Planner:
    def __init__(self, category_mapper: CategoryMapper, target_cids: Dict[str, Dict[str, str]]):
        self.category_mapper = category_mapper
        self.target_cids = target_cids

    def build_plans(
        self,
        media_type: str,
        items: Iterable[MediaItem],
        profile: str,
        config_snapshot: Dict[str, Any],
        history: List[Dict[str, Any]],
        unrecognized_action: str = "skip",
        source_root_cid: str = "",
        target_category_paths: Dict[str, str] = None,
    ) -> List[Dict[str, Any]]:
        plan_id = uuid.uuid4().hex
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        plans: List[Dict[str, Any]] = []
        history_keys = self._history_keys(history)
        target_category_paths = target_category_paths or {}

        for item in items:
            item_key = self._item_key(item)
            if item_key in history_keys:
                continue
            warnings: List[str] = []
            mediainfo, meta = self._recognize(media_type, item.path_hint, warnings)
            if not mediainfo and unrecognized_action == "skip":
                continue

            title = self._first_attr(mediainfo, ("title", "name", "original_title")) or PurePosixPath(item.name).stem
            year = self._first_attr(mediainfo, ("year", "release_year")) or self._extract_year(item.path_hint)
            tmdbid = self._first_attr(mediainfo, ("tmdb_id", "tmdbid"))
            season = self._first_int(meta, ("begin_season", "season")) or self._first_int(mediainfo, ("season",))
            episode = self._first_int(meta, ("begin_episode", "episode")) or self._first_int(mediainfo, ("episode",))
            mp_category, target_category, category_warning = self.category_mapper.resolve(media_type, mediainfo, self.target_cids)
            if category_warning:
                warnings.extend(category_warning.split("；"))

            target_parent = self.target_cids.get(media_type, {}).get(target_category, "")
            target_category_path = target_category_paths.get(target_category, "")
            confidence = "normal" if mediainfo else "unrecognized"
            action = "move"
            status = "planned"
            if not mediainfo:
                unrecognized_cid = self.target_cids.get("unrecognized")
                if unrecognized_action == "move_to_unrecognized" and unrecognized_cid:
                    action = "move"
                    target_category = "未识别"
                    target_parent = unrecognized_cid
                    target_category_path = target_category_paths.get("未识别", "")
                    warnings.append("未识别项目将移动到未识别目录")
                else:
                    action = "skip"
                    if unrecognized_action == "move_to_unrecognized":
                        warnings.append("未配置未识别目录CID，已跳过")
                status = "skipped" if action == "skip" else "planned"

            target_dir_name = self._media_dir_name(title, year)
            if media_type == "movie":
                target_season_dir_name = None
                target_name = self._movie_name(title, year, item.ext, item.name)
            else:
                target_season_dir_name = f"Season {season or 1:02d}"
                target_name = self._tv_name(title, year, season, episode, item.ext, item.name, warnings)

            target_path = str(PurePosixPath(target_category) / target_dir_name / (target_season_dir_name or "") / target_name)
            target_path = target_path.replace("//", "/")
            source_path = item.path_hint
            plans.append(OrganizePlan(
                plan_id=plan_id,
                item_id=item_key,
                created_at=created_at,
                media_type=media_type,
                profile=profile,
                config_snapshot=config_snapshot,
                source_name=item.name,
                source_ext=item.ext,
                source_fid=item.fid,
                source_cid=item.cid,
                source_parent_cid=item.parent_cid,
                source_root_cid=source_root_cid,
                source_is_dir=item.is_dir,
                source_path=source_path,
                target_category_path=target_category_path,
                path_hint=item.path_hint,
                title=title,
                year=str(year) if year else None,
                tmdbid=str(tmdbid) if tmdbid else None,
                season=season,
                episode=episode,
                moviepilot_category=mp_category,
                target_category=target_category,
                target_parent_cid=target_parent,
                target_dir_name=target_dir_name,
                target_dir_cid=None,
                target_season_dir_name=target_season_dir_name,
                target_season_dir_cid=None,
                target_name=target_name,
                target_path=target_path,
                action=action,
                status=status,
                error=None,
                recognition_source="MoviePilot" if mediainfo else "none",
                confidence=confidence,
                warnings=warnings,
            ).to_dict())
        return plans

    def _recognize(self, media_type: str, path_hint: str, warnings: List[str]):
        try:
            from app.chain.media import MediaChain
            from app.core.metainfo import MetaInfoPath
            from app.schemas.types import MediaType

            meta = MetaInfoPath(Path(path_hint))
            meta.type = MediaType.MOVIE if media_type == "movie" else MediaType.TV
            chain = MediaChain()
            if hasattr(chain, "recognize_media"):
                return chain.recognize_media(meta=meta), meta
            return chain.recognize_by_meta(meta), meta
        except Exception as err:
            warnings.append(f"识别失败：{err}")
            return None, None

    @staticmethod
    def _history_keys(history: List[Dict[str, Any]]) -> set:
        return {str(item.get("item_id") or "") for item in history if item.get("status") == "executed"}

    @staticmethod
    def _item_key(item: MediaItem) -> str:
        if item.is_dir:
            return f"dir:{item.cid}:{item.name}"
        return f"file:{item.fid}:{item.size}:{item.name}"

    @staticmethod
    def _first_attr(obj: Any, names: Iterable[str]) -> Any:
        if not obj:
            return None
        for name in names:
            value = getattr(obj, name, None)
            if value:
                return value
        return None

    @staticmethod
    def _first_int(obj: Any, names: Iterable[str]) -> int:
        value = Planner._first_attr(obj, names)
        try:
            return int(value or 0)
        except Exception:
            return 0

    @staticmethod
    def _extract_year(text: str) -> str:
        match = re.search(r"(?:19|20)\d{2}", text or "")
        return match.group(0) if match else ""

    @staticmethod
    def _media_dir_name(title: str, year: Any) -> str:
        return f"{title} ({year})" if year else title

    @staticmethod
    def _movie_name(title: str, year: Any, ext: str, source_name: str) -> str:
        suffix = ext or PurePosixPath(source_name).suffix
        return f"{title} ({year}){suffix}" if year else f"{title}{suffix}"

    @staticmethod
    def _tv_name(title: str, year: Any, season: int, episode: int, ext: str, source_name: str, warnings: List[str]) -> str:
        suffix = ext or PurePosixPath(source_name).suffix
        if season and episode:
            year_part = f" ({year})" if year else ""
            return f"{title}{year_part} - S{season:02d}E{episode:02d}{suffix}"
        warnings.append("未识别到明确季集，保留源文件名")
        return source_name
