"""気象庁の気象警報から、いま警報が発表されている市町村数。

    warning/data/warning/map.json … 全国の警報・注意報を1ファイルに集約

※ このエンドポイントは配信が遅れる/古いことがあるため、reportDatetime が
   6時間より古ければ何も出さない（古い値で埋めない）。
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta

from core.http import fetch
from core.models import JST, Observation, now_jst

URL = "https://www.jma.go.jp/bosai/warning/data/warning/map.json"

# 警報コード（02-08）＋ 特別警報コード（32-38）
WARNING_CODES = {"02", "03", "04", "05", "06", "07", "08"}
EMERGENCY_CODES = {"32", "33", "35", "36", "37", "38"}
ACTIVE = {"発表", "継続"}


def collect() -> list[Observation]:
    try:
        data = json.loads(fetch(URL, timeout=20))
    except Exception as exc:  # noqa: BLE001
        print(f"  ! jma_warning: {exc}")
        return []

    entries = data if isinstance(data, list) else [data]

    latest_report = None
    warned: set[str] = set()
    emergency: set[str] = set()

    for entry in entries:
        rd = entry.get("reportDatetime")
        if rd:
            try:
                dt = datetime.fromisoformat(rd)
                latest_report = dt if latest_report is None else max(latest_report, dt)
            except ValueError:
                pass
        for at in entry.get("areaTypes", []):
            for area in at.get("areas", []):
                code = str(area.get("code", ""))
                if len(code) < 7:  # 市町村レベルのみ
                    continue
                for w in area.get("warnings", []):
                    if w.get("status") not in ACTIVE:
                        continue
                    c = w.get("code")
                    if c in EMERGENCY_CODES:
                        emergency.add(code)
                        warned.add(code)
                    elif c in WARNING_CODES:
                        warned.add(code)

    if latest_report is None:
        print("  ! jma_warning: reportDatetime が無い")
        return []
    age = now_jst() - latest_report.astimezone(JST)
    if age > timedelta(hours=6):
        print(f"  ! jma_warning: データが古い（{latest_report:%Y-%m-%d %H:%M}）ので採用しない")
        return []

    n = len(warned)
    if n == 0:
        caption = "いま気象警報は出ていない"
    elif emergency:
        caption = f"特別警報が{len(emergency)}市町村に発表中"
    else:
        caption = f"{n}市町村に気象警報"

    return [Observation("warned-municipalities", n,
                        latest_report.astimezone(JST).isoformat(timespec="seconds"),
                        {"emergency_count": len(emergency), "caption": caption,
                         "report_datetime": latest_report.isoformat()})]
