"""日本銀行の時系列統計から、東京市場のドル・円レート（17時時点）。

    https://www.stat-search.boj.or.jp/ssi/mtshtml/csv/fm08_d_1.csv
    先頭に説明行が続き、そのあと「YYYY/MM/DD,17時時点,中心相場」の日次データ。
    土日祝は NA。平日でも公表は2営業日ほど遅れる。
"""
from __future__ import annotations

import csv
import io
import re

from core.http import fetch
from core.models import Observation, now_jst

URL = "https://www.stat-search.boj.or.jp/ssi/mtshtml/csv/fm08_d_1.csv"
_DATE = re.compile(r"^\d{4}/\d{1,2}/\d{1,2}$")


def _num(s: str) -> float | None:
    try:
        return float(s.strip())
    except (ValueError, AttributeError):
        return None


def collect() -> list[Observation]:
    try:
        text = fetch(URL, timeout=20).decode("shift_jis", errors="replace")
    except Exception as exc:  # noqa: BLE001
        print(f"  ! boj_fx: {exc}")
        return []

    latest_date = None
    latest_val = None
    for row in csv.reader(io.StringIO(text)):
        if not row or not _DATE.match(row[0].strip()):
            continue
        v17 = _num(row[1]) if len(row) > 1 else None
        vmid = _num(row[2]) if len(row) > 2 else None
        v = v17 if v17 is not None else vmid
        if v is not None:
            latest_date, latest_val = row[0].strip(), v

    if latest_val is None:
        print("  ! boj_fx: 有効な値が無い")
        return []

    y, m, d = latest_date.split("/")
    observed_at = f"{int(y):04d}-{int(m):02d}-{int(d):02d}T17:00:00+09:00"

    return [Observation("usd-jpy", round(latest_val, 2), observed_at, {
        "market": "東京市場・17時時点",
        "as_of": latest_date,
        "caption": f"1ドル＝{latest_val:g}円（{int(m)}月{int(d)}日）",
    })]
