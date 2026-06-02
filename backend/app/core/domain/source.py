"""Source monitoring domain models."""
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, field_validator


class DriveSourceConfig(BaseModel):
    """Configuration for a monitored Google Drive folder."""

    folder_id: str
    folder_name: str
    polling_interval_minutes: int = 15

    @field_validator("polling_interval_minutes")
    @classmethod
    def _validate_polling_interval(cls, v: int) -> int:
        if v < 5 or v > 1440:
            msg = "polling_interval_minutes must be between 5 and 1440"
            raise ValueError(msg)
        return v


class GmailSourceConfig(BaseModel):
    """Configuration for monitored Gmail labels."""

    label_ids: list[str]
    label_names: list[str]
    polling_interval_minutes: int = 10

    @field_validator("polling_interval_minutes")
    @classmethod
    def _validate_polling_interval(cls, v: int) -> int:
        if v < 5 or v > 1440:
            msg = "polling_interval_minutes must be between 5 and 1440"
            raise ValueError(msg)
        return v


class CalendarSourceConfig(BaseModel):
    """Configuration for a monitored Google Calendar."""

    calendar_id: str
    calendar_name: str
    lookahead_days: int = 30

    @field_validator("lookahead_days")
    @classmethod
    def _validate_lookahead_days(cls, v: int) -> int:
        if v < 7 or v > 90:
            msg = "lookahead_days must be between 7 and 90"
            raise ValueError(msg)
        return v


class SourceConfig(BaseModel):
    """A user-configured monitored source (Drive folder, Gmail label, or Calendar)."""

    id: UUID
    user_id: UUID
    source_type: Literal["drive", "gmail", "calendar"]
    config: DriveSourceConfig | GmailSourceConfig | CalendarSourceConfig
    status: Literal["active", "error", "paused"] = "active"
    last_sync_at: datetime | None = None
    last_sync_count: int = 0


class FileChange(BaseModel):
    """A single file change detected during a polling cycle."""

    file_id: str
    filename: str
    mime_type: str
    modified_at: datetime


class ChangeSet(BaseModel):
    """Result of a polling cycle: new files and an updated sync token."""

    new_files: list[FileChange]
    new_sync_token: str | None = None
