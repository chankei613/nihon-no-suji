"""データ型と時刻ヘルパ。すべて日本時間(JST)で扱う。"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any

JST = timezone(timedelta(hours=9), name="JST")


def now_jst() -> datetime:
    return datetime.now(JST)


def iso(dt: datetime) -> str:
    return dt.astimezone(JST).isoformat(timespec="seconds")


@dataclass
class Observation:
    """1メトリックの1観測値。"""

    slug: str
    value: float
    observed_at: str  # ISO8601 (JST)。データ提供元の観測時刻
    detail: dict[str, Any] = field(default_factory=dict)
    fetched_at: str = field(default_factory=lambda: iso(now_jst()))

    @property
    def date(self) -> str:
        return self.observed_at[:10]
