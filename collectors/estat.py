"""e-Stat（政府統計の総合窓口）API から、人口など社会統計。

利用には無料の appId が要る（環境変数 ESTAT_APP_ID）。未設定の間はこの collector
は何もせず終了する（他の collector には影響しない）。

appId の取り方: https://www.e-stat.go.jp/mypage/user/preregister で登録
→ メール確認 → マイページ「API機能」で即時発行。

統計表(statsDataId)ごとに分類コードの構成が違うため、まず getMetaInfo で
メタ情報を取り、「総数」的なコードを名前から動的に選んでから getStatsData を叩く。

参考: e-Stat API仕様 https://www.e-stat.go.jp/api/api-info/e-stat-manual3-0
実レスポンスで確認済み: 2026-09-05（statsDataId=0003443838 人口推計）
"""
from __future__ import annotations

import json
import os

from core.http import fetch
from core.models import Observation, now_jst

BASE = "https://api.e-stat.go.jp/rest/3.0/app/json"

# 分類軸の中から「合計」を意味するコードを選ぶための手がかり
_TOTAL_HINTS = ("総数", "総人口", "男女計", "全国", "合計", "全age")


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
    """分類オブジェクト一覧。実レスポンスは METADATA_INF > CLASS_INF > CLASS_OBJ。"""
    inf = meta["GET_META_INFO"]["METADATA_INF"]
    node = inf.get("CLASS_INF", inf)
    return _as_list(node.get("CLASS_OBJ"))


def _cd_param(class_id: str) -> str:
    """分類軸ID → getStatsData の絞り込みパラメータ名（"cat01"→"cdCat01", "area"→"cdArea"）。"""
    return "cd" + class_id[:1].upper() + class_id[1:]


def _total_filters(meta: dict) -> dict:
    """各分類軸について、選択肢が複数あるものは「総数」相当のコードで絞り込む。

    時間軸(time)は最新値がほしいので絞らない。選択肢が1つだけの軸も指定不要。
    どの選択肢が「総数」か判定できない軸があると、絞り込み漏れで別カテゴリの値を
    拾ってしまう危険があるため、その場合は黙って進めずエラーにする。
    """
    filters: dict[str, str] = {}
    for obj in _class_objs(meta):
        cid = obj.get("@id", "")
        if cid == "time":
            continue
        classes = _as_list(obj.get("CLASS"))
        if len(classes) <= 1:
            continue
        code = next((c.get("@code") for c in classes
                     if any(h in c.get("@name", "") for h in _TOTAL_HINTS)), None)
        if code is None:
            raise ValueError(f"「総数」相当のコードが見つからない分類軸: {cid}")
        filters[_cd_param(cid)] = code
    return filters


def _values(data: dict) -> list[dict]:
    return _as_list(data["GET_STATS_DATA"]["STATISTICAL_DATA"]["DATA_INF"]["VALUE"])


def _latest_by_time(values: list[dict]) -> dict | None:
    good = [v for v in values if v.get("$") not in (None, "", "-", "***", "X")]
    return max(good, key=lambda v: v.get("@time", ""), default=None)


def _scale(unit: str) -> int:
    """単位表記から人数へのスケール（"万人"→10000 など）。"""
    if "百万" in unit:
        return 1_000_000
    if "万" in unit:
        return 10_000
    if "千" in unit:
        return 1_000
    return 1


# ---------------------------------------------------------------- 個別の統計

def _fetch_population(app_id: str) -> Observation | None:
    stats_data_id = "0003443838"  # 人口推計 各月1日現在人口（概算値）
    try:
        meta = _get("getMetaInfo", appId=app_id, statsDataId=stats_data_id)
        filters = {"appId": app_id, "statsDataId": stats_data_id, "metaGetFlg": "N"}
        filters.update(_total_filters(meta))
        data = _get("getStatsData", **filters)
        v = _latest_by_time(_values(data))
        if v is None:
            print("  ! estat population: 値が取れない")
            return None
        unit = v.get("@unit", "")
        value = float(v["$"]) * _scale(unit)
        return Observation(
            "japan-population", round(value),
            now_jst().date().isoformat() + "T00:00:00+09:00",
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
