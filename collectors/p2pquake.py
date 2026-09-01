"""P2P地震情報 API から、過去24時間の地震回数（震度1以上）。

GET https://api.p2pquake.net/v2/history?codes=551&limit=100
earthquake.time は "YYYY/MM/DD HH:MM:SS"（JST）。maxScale は 震度×10（10=震度1）。
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta

from core.http import fetch
from core.models import JST, Observation, now_jst

URL = "https://api.p2pquake.net/v2/history?codes=551&limit=100"

SCALE_LABEL = {
    10: "1", 20: "2", 30: "3", 40: "4",
    45: "5弱", 50: "5強", 55: "6弱", 60: "6強", 70: "7",
}


def _label(scale: int) -> str:
    return SCALE_LABEL.get(scale, "不明")


def collect() -> list[Observation]:
    try:
        data = json.loads(fetch(URL, timeout=20))
    except Exception as exc:  # noqa: BLE001
        print(f"  ! p2pquake: {exc}")
        return []

    now = now_jst()
    since = now - timedelta(hours=24)
    window: list[dict] = []
    for item in data:
        eq = item.get("earthquake") or {}
        t = eq.get("time")
        if not t:
            continue
        try:
            dt = datetime.strptime(t, "%Y/%m/%d %H:%M:%S").replace(tzinfo=JST)
        except ValueError:
            continue
        if since <= dt <= now + timedelta(minutes=5):
            window.append({
                "time": dt.isoformat(timespec="seconds"),
                "scale": eq.get("maxScale", -1),
                "name": (eq.get("hypocenter") or {}).get("name") or "",
                "magnitude": (eq.get("hypocenter") or {}).get("magnitude"),
                "depth": (eq.get("hypocenter") or {}).get("depth"),
            })

    felt = [w for w in window if isinstance(w["scale"], int) and w["scale"] >= 10]
    felt.sort(key=lambda w: w["time"])
    count = len(felt)

    strongest = max(
        felt,
        key=lambda w: (w["scale"], w["magnitude"] if isinstance(w["magnitude"], (int, float)) else 0),
        default=None,
    )
    max_mag = max((w["magnitude"] for w in window if isinstance(w["magnitude"], (int, float))),
                  default=None)

    if count == 0:
        caption = "この24時間、震度1以上の地震はなかった"
    else:
        s = strongest
        caption = f"最大は{s['name']}の震度{_label(s['scale'])}" if s and s["name"] else \
                  f"最大は震度{_label(s['scale'])}" if s else f"{count}回"

    detail = {
        "caption": caption,
        "window_hours": 24,
        "max_magnitude": max_mag,
        "strongest": strongest,
        "latest": felt[-1] if felt else None,
        "capped": len(data) >= 100 and count >= 100,
    }
    return [Observation(
        slug="quakes-24h",
        value=count,
        observed_at=now.replace(second=0, microsecond=0).isoformat(timespec="seconds"),
        detail=detail,
    )]
