from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class TriggerRequest(BaseModel):
    source: str = Field(default="external", max_length=64)
    execute: bool | None = None
    force_execute: bool = False

    @field_validator("source", mode="before")
    @classmethod
    def normalize_source(cls, value) -> str:
        return " ".join(str(value or "external").split())[:64] or "external"


class ResolvePathRequest(BaseModel):
    path: str = Field(min_length=1, max_length=1024)


class ListDirectoryRequest(BaseModel):
    path: str = Field(default="", max_length=1024)
    cid: str = Field(default="", max_length=64)
