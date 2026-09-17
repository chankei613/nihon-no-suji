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
    # observed_at は「予報対象日」ではなく「取得した今日」にする（他collectorと同じ規約）。
    # 対象日はdetail["for_date"]に別途持たせる。ここを対象日にしてしまうと、
    # 履歴の日付キーが常に「あした」にずれて stale 判定が壊れる（あすの予報が
    # 毎回「古い」扱いになるバグがあった）。
    today = now_jst().date().isoformat()
    fetched_at = f"{today}T05:00:00+09:00"

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
        hi, lo = max(vals), min(vals)
        out.append(Observation("tokyo-forecast-max", float(hi), fetched_at, {
            "for_date": target,
            "caption": ("あすは猛暑日の予想" if hi >= 35 else
                        "あすは真夏日の予想" if hi >= 30 else
                        "あすは涼しい予想" if hi < 20 else "あすの東京の最高気温の予想"),
        }))
        if len(vals) >= 2:
            out.append(Observation("tokyo-forecast-min", float(lo), fetched_at, {
                "for_date": target,
                "caption": ("あすは冷え込む予想" if lo < 5 else
                            "あすは熱帯夜の予想" if lo >= 25 else "あすの東京の最低気温の予想"),
            }))
        break

    # --- 週間予報：この先いちばん暑くなりそうな日 ---
    weekly = data[1] if len(data) > 1 else None
    if weekly:
        for ts in weekly.get("timeSeries", []):
            a = _area(ts.get("areas", []), "東京")
            if not a or "tempsMax" not in a:
                continue
            pairs = [(d[:10], _int(v)) for d, v in zip(ts["timeDefines"], a["tempsMax"])
                     if _int(v) is not None]
            if pairs:
                best_date, best_val = max(pairs, key=lambda p: p[1])
                out.append(Observation("tokyo-week-max-forecast", float(best_val), fetched_at, {
                    "for_date": best_date,
                    "caption": f"{int(best_date[5:7])}月{int(best_date[8:10])}日ごろがいちばん暑くなりそう",
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
        out.append(Observation("tokyo-forecast-pop", float(pop), fetched_at, {
            "for_date": target,
            "caption": ("あすは雨の可能性が高い" if pop >= 60 else
                        "あすは所により雨" if pop >= 30 else "あすは雨の心配は少ない"),
        }))
        break

    return out
