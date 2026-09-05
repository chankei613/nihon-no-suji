"""e-Stat（政府統計の総合窓口）API から、人口など社会統計。

利用には無料の appId が要る（環境変数 ESTAT_APP_ID）。未設定の間はこの collector
は何もせず終了する（他の collector には影響しない）。

appId の取り方: https://www.e-stat.go.jp/mypage/user/preregister で登録
→ メール確認 → マイページ「API機能」で即時発行。

⚠️ 実際の appId で一度も検証していない（2026-09-05時点）。
   統計表(statsDataId)ごとに分類コードの構成が違うため、まず getMetaInfo で
   コードを名前から動的に解決してから getStatsData を叩く設計にしている。
   appId が使えるようになったら最初の実行結果を必ず確認すること。

参考: e-Stat API仕様 https://www.e-stat.go.jp/api/api-info/e-stat-manual3-0
"""
from __future__ import annotations

import json
import os
from datetime import datetime

from core.http import fetch
from core.models import Observation, now_jst

BASE = "https://api.e-stat.go.jp/rest/3.0/app/json"


def _app_id() -> str | None:
    v = os.environ.get("ESTAT_APP_ID", "").strip()
    return v or None


def _get(path: str, **params) -> dict:
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    return json.loads(fetch(f"{BASE}/{path}?{qs}", timeout=25))


def _as_list(x):
    """e-StatのJSONは要素が1件だけだとdict、複数だとlistになる。常にlistで返す。"""
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def _class_objs(meta: dict) -> list[dict]:
    return _as_list(meta["GET_META_INFO"]["METADATA_INF"]["CLASS_OBJ"])


def _code_by_name(meta: dict, class_id: str, name_substrings: tuple[str, ...]) -> str | None:
    """指定した分類軸(class_id)の中から、名前に name_substrings のどれかを含むコードを探す。"""
    for obj in _class_objs(meta):
        if obj.get("@id") != class_id:
            continue
        for c in _as_list(obj.get("CLASS")):
            name = c.get("@name", "")
            if any(s in name for s in name_substrings):
                return c.get("@code")
    return None


def _values(data: dict) -> list[dict]:
    return _as_list(data["GET_STATS_DATA"]["STATISTICAL_DATA"]["DATA_INF"]["VALUE"])


def _latest_by_time(values: list[dict]) -> dict | None:
    def key(v: dict):
        # @time は "2026000908" のような形式のことが多い（年+月コード等）。文字列比較で概ね時系列順になる。
        return v.get("@time", "")
    good = [v for v in values if v.get("$") not in (None, "", "-", "***")]
    return max(good, key=key, default=None)


# ---------------------------------------------------------------- 個別の統計

def _fetch_population(app_id: str) -> Observation | None:
    stats_data_id = "0003443838"  # 人口推計 各月1日現在人口（概算値）
    try:
        meta = _get("getMetaInfo", appId=app_id, statsDataId=stats_data_id)
        cat01 = _code_by_name(meta, "cat01", ("総数", "男女計"))
        area = _code_by_name(meta, "area", ("全国",))
        filters = {"appId": app_id, "statsDataId": stats_data_id}
        if cat01:
            filters["cdCat01"] = cat01
        if area:
            filters["cdArea"] = area
        data = _get("getStatsData", **filters)
        v = _latest_by_time(_values(data))
        if v is None:
            print("  ! estat population: 値が取れない")
            return None
        value = float(v["$"])
        unit = v.get("@unit", "")
        if "千人" in unit:
            value *= 1000
        return Observation(
            "japan-population", round(value), now_jst().date().isoformat() + "T00:00:00+09:00",
            {"time_code": v.get("@time"), "unit_raw": unit,
             "caption": "総務省統計局 人口推計（各月1日現在・概算値）"},
        )
    except Exception as exc:  # noqa: BLE001
        print(f"  ! estat population: {exc}")
        return None


def collect() -> list[Observation]:
    app_id = _app_id()
    if not app_id:
        print("  (ESTAT_APP_ID 未設定のためスキップ)")
        return []

    out: list[Observation] = []
    pop = _fetch_population(app_id)
    if pop:
        out.append(pop)
    return out
