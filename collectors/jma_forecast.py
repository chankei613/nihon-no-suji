"""気象庁の天気予報JSONから、東京の「あした」の予想（最高/最低気温・降水確率）。

    https://www.jma.go.jp/bosai/forecast/data/forecast/130000.json
    d[0] に今日明日の詳細（temps / pops）。
"""
from __future__ import annotations

import json
from collections import defaultdict

from core.http import fetch
from core.models import Observation, now_jst

URL = "https://www.jma.go.jp/bosai/forecast/data/forecast/130000.json"


def _int(s) -> int | None:
    try:
        return int(str(s).strip())
    except (ValueError, TypeError):
        return None


def _area(ts_areas: list, *names: str) -> dict | None:
    for a in ts_areas:
        if a.get("area", {}).get("name") in names:
            return a
    return ts_areas[0] if ts_areas else None


def collect() -> list[Observation]:
    try:
        data = json.loads(fetch(URL, timeout=15))
    except Exception as exc:  # noqa: BLE001
        print(f"  ! jma_forecast: {exc}")
        return []

    detail = data[0]
    out: list[Observation] = []

    # --- 気温 ---
    for ts in detail.get("timeSeries", []):
        a = _area(ts.get("areas", []), "東京")
        if not a or "temps" not in a:
            continue
        by_date: dict[str, list[int]] = defaultdict(list)
        for when, val in zip(ts["timeDefines"], a["temps"]):
            v = _int(val)
            if v is not None:
                by_date[when[:10]].append(v)
        if not by_date:
            continue
        target = max(by_date)  # 最も先の日付＝あした
        vals = by_date[target]
        observed_at = f"{target}T05:00:00+09:00"
        hi, lo = max(vals), min(vals)
        out.append(Observation("tokyo-forecast-max", float(hi), observed_at, {
            "for_date": target,
            "caption": ("あすは猛暑日の予想" if hi >= 35 else
                        "あすは真夏日の予想" if hi >= 30 else
                        "あすは涼しい予想" if hi < 20 else "あすの東京の最高気温の予想"),
        }))
        if len(vals) >= 2:
            out.append(Observation("tokyo-forecast-min", float(lo), observed_at, {
                "for_date": target,
                "caption": ("あすは冷え込む予想" if lo < 5 else
                            "あすは熱帯夜の予想" if lo >= 25 else "あすの東京の最低気温の予想"),
            }))
        break

    # --- 降水確率 ---
    for ts in detail.get("timeSeries", []):
        a = _area(ts.get("areas", []), "東京地方", "東京")
        if not a or "pops" not in a:
            continue
        by_date: dict[str, list[int]] = defaultdict(list)
        for when, val in zip(ts["timeDefines"], a["pops"]):
            v = _int(val)
            if v is not None:
                by_date[when[:10]].append(v)
        if not by_date:
            continue
        target = max(by_date)
        pop = max(by_date[target])
        out.append(Observation("tokyo-forecast-pop", float(pop),
                               f"{target}T05:00:00+09:00", {
            "for_date": target,
            "caption": ("あすは雨の可能性が高い" if pop >= 60 else
                        "あすは所により雨" if pop >= 30 else "あすは雨の心配は少ない"),
        }))
        break

    return out
