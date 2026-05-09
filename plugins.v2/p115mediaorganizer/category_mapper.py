from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


DEFAULT_CATEGORY_MAPPING = {
    "movie": {
        "动画电影": "动画电影",
        "华语电影": "华语电影",
        "外语电影": "外语电影",
    },
    "tv": {
        "国漫": "国产剧",
        "日番": "日韩剧",
        "纪录片": "未分类",
        "儿童": "未分类",
        "综艺": "综艺",
        "国产剧": "国产剧",
        "欧美剧": "欧美剧",
        "日韩剧": "日韩剧",
        "未分类": "未分类",
    },
}

MOVIE_FALLBACK_CATEGORY = "外语电影"
TV_FALLBACK_CATEGORY = "未分类"


class CategoryMapper:
    def __init__(self, mapping: Optional[Dict[str, Dict[str, str]]] = None):
        self.mapping = mapping or DEFAULT_CATEGORY_MAPPING

    def resolve(
        self,
        media_type: str,
        mediainfo: Any,
        target_cids: Dict[str, Dict[str, str]],
    ) -> Tuple[str, str, str]:
        warnings = []
        source_category = self._get_category(media_type, mediainfo, warnings)
        fallback = MOVIE_FALLBACK_CATEGORY if media_type == "movie" else TV_FALLBACK_CATEGORY
        mapped_category = self.mapping.get(media_type, {}).get(source_category or "")

        if not source_category:
            warnings.append("MoviePilot分类为空")
        if source_category and not mapped_category:
            warnings.append(f"分类未映射：{source_category}")
        target_category = mapped_category or fallback

        if target_category not in target_cids.get(media_type, {}):
            warnings.append(f"目标分类CID不存在：{target_category}")
            target_category = fallback

        if target_category not in target_cids.get(media_type, {}):
            warnings.append(f"兜底分类CID不存在：{target_category}")

        return source_category or "", target_category, "；".join(warnings)

    def _get_category(self, media_type: str, mediainfo: Any, warnings: list) -> str:
        if not mediainfo:
            warnings.append("未识别到媒体信息")
            return ""

        category = str(getattr(mediainfo, "category", "") or "").strip()
        if category:
            return category

        tmdb_info = getattr(mediainfo, "tmdb_info", None)
        if not tmdb_info:
            warnings.append("tmdb_info为空")
            return ""

        try:
            try:
                from app.modules.themoviedb.category import CategoryHelper
            except Exception:
                from app.modules.themoviedb import CategoryHelper

            helper = CategoryHelper()
            if media_type == "movie" and hasattr(helper, "get_movie_category"):
                return str(helper.get_movie_category(tmdb_info) or "").strip()
            if media_type == "tv" and hasattr(helper, "get_tv_category"):
                return str(helper.get_tv_category(tmdb_info) or "").strip()
        except Exception as err:
            warnings.append(f"分类兜底失败：{err}")
        return ""
