"""気象庁の火山情報から、噴火警戒レベル2以上の火山数。

    const/volcano_list.json  … 全国の火山一覧（コード・名前・座標。約120火山）
    data/warning/{code}.json … 火山ごとの噴火警報・予報（最新報のみ。未発表の火山は404）

一覧APIには現在の警戒レベルが載っていないため、火山ごとに個別取得して
「噴火警報・予報（対象火山）」の項目名（例: "レベル３（入山規制）"）からレベルを読む。
404は「レベル1相当・特記事項なし」を意味することが多いのでエラー扱いにせず読み飛ばす
（ここでリトライすると120火山ぶん無駄に待つため retries=1 で1回だけ試す）。
"""
from __future__ import annotations

import json
import re

from core.http import fetch
from core.models import Observation, now_jst

BASE = "https://www.jma.go.jp/bosai/volcano"
LIST_URL = f"{BASE}/const/volcano_list.json"
WARNING_URL = f"{BASE}/data/warning/{{code}}.json"

LEVEL_RE = re.compile(r"レベル([1-5１-５])")
_ZEN2HAN = str.maketrans("１２３４５", "12345")


def _level_from_report(report: dict) -> int | None:
    for info in report.get("volcanoInfos", []):
        if info.get("type") != "噴火警報・予報（対象火山）":
            continue
        for item in info.get("items", []):
            m = LEVEL_RE.search(item.get("name", ""))
            if m:
                return int(m.group(1).translate(_ZEN2HAN))
    return None


def collect() -> list[Observation]:
    try:
        volcanoes = json.loads(fetch(LIST_URL, timeout=15))
    except Exception as exc:  # noqa: BLE001
        print(f"  ! jma_volcano: {exc}")
        return []

    observed_at = now_jst().replace(microsecond=0).isoformat(timespec="seconds")
    active: list[dict] = []
    checked = 0
    for v in volcanoes:
        code = v.get("code")
        if not code:
            continue
        try:
            report = json.loads(fetch(WARNING_URL.format(code=code), timeout=10, retries=1))
        except Exception:  # noqa: BLE001
            continue
        checked += 1
        level = _level_from_report(report)
        if level is not None and level >= 2:
            active.append({"code": code, "name": v.get("name_jp"), "level": level})

    if checked == 0:
        print("  ! jma_volcano: どの火山も取得できなかった")
        return []

    n = len(active)
    active.sort(key=lambda a: -a["level"])
    if n == 0:
        caption = "噴火警戒レベル2以上の火山はいまない"
    else:
        top = active[0]
        caption = f"{top['name']}（レベル{top['level']}）など{n}火山で警戒レベル2以上"

    return [Observation("volcano-alert-points", n, observed_at, {
        "volcanoes": active, "checked": checked, "caption": caption,
    })]
