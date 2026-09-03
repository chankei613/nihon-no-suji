"""気象庁 台風情報から、いま発生している台風の数。

    targetTc.json … 現在の対象TCのリスト
    {TC}/specifications.json … 名称・階級・中心気圧・位置

夏〜秋の主役カード。台風ゼロの日も「今は台風なし」として成立する。
"""
from __future__ import annotations

import json

from core import store
from core.http import fetch
from core.models import Observation, now_jst

TARGET_URL = "https://www.jma.go.jp/bosai/typhoon/data/targetTc.json"
SPEC_URL = "https://www.jma.go.jp/bosai/typhoon/data/{tc}/specifications.json"

CATEGORY_JP = {"TD": "熱帯低気圧", "TS": "台風", "STS": "強い台風", "TY": "非常に強い台風"}


def _spec(tc: str) -> dict:
    try:
        parts = json.loads(fetch(SPEC_URL.format(tc=tc), timeout=15))
    except Exception:  # noqa: BLE001
        return {}
    title = next((p for p in parts if p.get("part") == "title"), {})
    analysis = next((p for p in parts if isinstance(p.get("part"), dict)
                     and p["part"].get("en") == "Analysis"), {})
    return {
        "number": title.get("typhoonNumber"),
        "name": (title.get("name") or {}).get("jp"),
        "category": (title.get("category") or {}).get("en"),
        "pressure": analysis.get("pressure"),
        "location": analysis.get("location"),
        "course": analysis.get("course"),
    }


def collect() -> list[Observation]:
    try:
        targets = json.loads(fetch(TARGET_URL, timeout=15))
    except Exception as exc:  # noqa: BLE001
        print(f"  ! jma_typhoon: {exc}")
        return []

    observed_at = now_jst().replace(second=0, microsecond=0).isoformat(timespec="seconds")
    tcs = [t for t in targets if t.get("tropicalCyclone")]
    # 台風(TS)以上のみカウント（TD=熱帯低気圧は含めない）
    storms = [t for t in tcs if t.get("category") in ("TS", "STS", "TY")]

    details = []
    for t in storms:
        d = _spec(t["tropicalCyclone"])
        d["typhoon_number"] = t.get("typhoonNumber")
        details.append(d)

    n = len(storms)
    if n == 0:
        caption = "いま発生している台風はない"
    elif n == 1:
        d = details[0]
        num = (d.get("typhoon_number") or "")[-2:].lstrip("0")
        nm = d.get("name") or ""
        loc = d.get("location") or ""
        caption = f"台風{num}号「{nm}」が{loc}".rstrip("がを ")
    else:
        nums = "・".join((d.get("typhoon_number") or "")[-2:].lstrip("0") for d in details)
        caption = f"台風{nums}号が発生中"

    out = [Observation("active-typhoons", n, observed_at,
                       {"typhoons": details, "caption": caption})]

    # 今年の台風発生数 = 今年発生した台風番号の最大（履歴から単調増加で持ち越す）
    yy = now_jst().year % 100
    nums = [int(t["typhoonNumber"][-2:]) for t in tcs
            if (t.get("typhoonNumber") or "").startswith(f"{yy:02d}")]
    seen_max = 0
    for rec in store.load_history("typhoons-this-year"):
        if rec["date"][:4] == str(now_jst().year):
            seen_max = max(seen_max, int(rec["value"]))
    total = max([seen_max] + nums)
    if total > 0:
        out.append(Observation("typhoons-this-year", total, observed_at,
                               {"caption": f"今年はこれまでに{total}個の台風が発生"}))
    return out
