"""気象庁の気象警報から、いま警報が発表されている市町村数。

    warning/data/r8/map.json      … 全国の警報・注意報（発表官署ごとの最新報の配列）
    warning/data/r8/map_time.json … 最新の管理時刻（鮮度チェック用）

※ 旧 warning/data/warning/*.json は 2026-05 で凍結。現行は data/r8/。
   鮮度が6時間より古ければ何も出さない（古い値で埋めない）。
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from core.http import fetch
from core.models import JST, Observation, now_jst

MAP_URL = "https://www.jma.go.jp/bosai/warning/data/r8/map.json"
TIME_URL = "https://www.jma.go.jp/bosai/warning/data/r8/map_time.json"

WARNING_CODES = {"02", "03", "04", "05", "06", "07", "08"}
EMERGENCY_CODES = {"32", "33", "35", "36", "37", "38"}
HEAVY_RAIN_CODE = "03"  # 大雨警報
FLOOD_CODE = "04"       # 洪水警報
NONE_STATUS = "発表警報・注意報はなし"
ACTIVE_STATUS = {"発表", "継続"}


def _freshness_ok() -> tuple[bool, datetime | None]:
    try:
        t = json.loads(fetch(TIME_URL, timeout=15)).get("latestControlDatetime")
        dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
        return (now_jst() - dt.astimezone(JST)) <= timedelta(hours=6), dt.astimezone(JST)
    except Exception:  # noqa: BLE001
        return False, None


def collect() -> list[Observation]:
    fresh, latest = _freshness_ok()
    if not fresh:
        print(f"  ! jma_warning: r8データが古い/取得不可（{latest}）ので採用しない")
        return []

    try:
        reports = json.loads(fetch(MAP_URL, timeout=20))
    except Exception as exc:  # noqa: BLE001
        print(f"  ! jma_warning: {exc}")
        return []

    # 発表官署ごとの最新報で上書きしたいので reportDatetime 昇順に処理
    reports.sort(key=lambda r: r.get("reportDatetime", ""))

    # areaCode -> 現在有効な警報コードの集合
    state: dict[str, set[str]] = {}
    for rep in reports:
        for item in (rep.get("warning") or {}).get("class20Items", []):
            code = str(item.get("areaCode", ""))
            if len(code) < 7:
                continue
            kinds = item.get("kinds", [])
            if any(k.get("status") == NONE_STATUS for k in kinds):
                state[code] = set()
                continue
            cur = state.setdefault(code, set())
            for k in kinds:
                c, st = k.get("code"), k.get("status")
                if c not in WARNING_CODES and c not in EMERGENCY_CODES:
                    continue
                if st in ACTIVE_STATUS:
                    cur.add(c)
                elif st == "解除":
                    cur.discard(c)

    warned = {a for a, codes in state.items() if codes}
    emergency = {a for a, codes in state.items() if codes & EMERGENCY_CODES}

    n = len(warned)
    if n == 0:
        caption = "いま気象警報は出ていない"
    elif emergency:
        caption = f"特別警報が{len(emergency)}市町村に発表中"
    else:
        caption = f"{n}市町村に気象警報"

    heavy_rain = {a for a, codes in state.items() if HEAVY_RAIN_CODE in codes}
    flood = {a for a, codes in state.items() if FLOOD_CODE in codes}

    observed_at = (latest or now_jst()).isoformat(timespec="seconds")
    out = [Observation("warned-municipalities", n, observed_at,
                       {"emergency_count": len(emergency), "caption": caption})]
    out.append(Observation("heavy-rain-warned-municipalities", len(heavy_rain), observed_at, {
        "caption": f"{len(heavy_rain)}市町村に大雨警報" if heavy_rain else "いま大雨警報は出ていない",
    }))
    out.append(Observation("flood-warned-municipalities", len(flood), observed_at, {
        "caption": f"{len(flood)}市町村に洪水警報" if flood else "いま洪水警報は出ていない",
    }))
    return out
