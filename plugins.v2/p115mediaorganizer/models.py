from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MediaItem:
    fid: Optional[str]
    cid: Optional[str]
    name: str
    ext: Optional[str]
    size: int
    is_dir: bool
    parent_cid: str
    path_hint: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OrganizePlan:
    plan_id: str
    item_id: str
    created_at: str
    media_type: str
    config_snapshot: Dict[str, Any]
    source_name: str
    source_ext: Optional[str]
    source_fid: Optional[str]
    source_cid: Optional[str]
    source_parent_cid: str
    source_root_cid: str
    source_is_dir: bool
    path_hint: str
    title: str
    year: Optional[str]
    tmdbid: Optional[str]
    season: Optional[int]
    episode: Optional[int]
    moviepilot_category: str
    target_category: str
    target_parent_cid: str
    target_dir_name: str
    target_dir_cid: Optional[str]
    target_season_dir_name: Optional[str]
    target_season_dir_cid: Optional[str]
    target_name: str
    target_path: str
    action: str
    status: str
    error: Optional[str]
    recognition_source: str
    confidence: str
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExecuteResult:
    plan_id: str
    total: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
