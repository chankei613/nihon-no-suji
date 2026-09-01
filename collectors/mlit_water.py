"""琵琶湖の水位と、主要ダムの貯水率。

- 近畿地方整備局が配信するJSON（琵琶湖水位＋近畿管内12ダムの貯水率）
    https://www.kkr.mlit.go.jp/river/json/dam.json
- 関東地方整備局「首都圏の水資源状況」HTML表（首都圏の水がめ 5グループ）
    https://www.ktr.mlit.go.jp/river/shihon/river_shihon00000226.html

いずれも平日更新。片方が落ちても、取れた分だけで値を作る。
"""
from __future__ import annotations

import html
import json
import re
from datetime import datetime

from core.http import fetch
from core.models import JST, Observation, now_jst

KINKI_JSON = "https://www.kkr.mlit.go.jp/river/json/dam.json"
KANTO_HTML = "https://www.ktr.mlit.go.jp/river/shihon/river_shihon00000226.html"

KINKI_DAM_NAMES = {
    "managawa": "真名川ダム", "kuzuryu": "九頭竜ダム", "amagase": "天ヶ瀬ダム",
    "muro": "室生ダム", "syourenji": "青蓮寺ダム", "takayama": "高山ダム",
    "nunome": "布目ダム", "hiyoshi": "日吉ダム", "hinati": "比奈知ダム",
    "hitokura": "一庫ダム", "otaki": "大滝ダム", "sarutani": "猿谷ダム",
}


def _num(s: str) -> float | None:
    try:
        return float(re.sub(r"[,\s%％]", "", html.unescape(s or "")))
    except (ValueError, TypeError):
        return None


def _kinki() -> tuple[dict | None, list[dict], str | None]:
    """(琵琶湖dict, [ダム{name,rate}], datetime文字列)"""
    data = json.loads(fetch(KINKI_JSON, timeout=20))
    dt = data.get("datetime")
    observed = None
    if dt:
        try:
            observed = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S").replace(tzinfo=JST).isoformat()
        except ValueError:
            pass

    lake = None
    biwako = (((data.get("lake") or {}).get("biwako") or {}).get("suii") or {})
    if biwako.get("today") not in (None, ""):
        v = _num(biwako["today"])
        if v is not None:
            lake = {"value": v, "diff": _num((biwako.get("diff") or ["", ""])[0])}

    dams: list[dict] = []
    for name, d in (data.get("dam") or {}).items():
        rate = _num(((d.get("chosuiritsu") or {}).get("today")))
        if rate is not None:
            dams.append({"name": KINKI_DAM_NAMES.get(name, name), "rate": rate, "region": "近畿"})
    return lake, dams, observed


def _kanto() -> list[dict]:
    t = fetch(KANTO_HTML, timeout=25).decode("utf-8", errors="replace")
    t = re.sub(r"<(script|style).*?</\1>", "", t, flags=re.S)
    out: list[dict] = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", t, flags=re.S):
        cells = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", c))).strip()
                 for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, flags=re.S)]
        cells = [c for c in cells if c]
        if len(cells) >= 4 and "ダム" in cells[0]:
            rate = _num(cells[-1])
            if rate is not None and 0 <= rate <= 130:
                out.append({"name": cells[0], "rate": rate, "region": "関東"})
    return out


def _lake_caption(v: float) -> str:
    if v >= 0:
        return f"基準水位(B.S.L.)より{v:g}cm高い"
    return f"基準水位(B.S.L.)より{abs(v):g}cm低い"


def _dam_caption(mean: float, n: int) -> str:
    if mean >= 90:
        mood = "たっぷり"
    elif mean >= 75:
        mood = "おおむね平年並み"
    elif mean >= 55:
        mood = "やや少なめ"
    else:
        mood = "少なめ"
    return f"主要{n}ダムの平均貯水率（{mood}）"


def collect() -> list[Observation]:
    out: list[Observation] = []
    lake = None
    dams: list[dict] = []
    observed = None

    try:
        lake, dams, observed = _kinki()
    except Exception as exc:  # noqa: BLE001
        print(f"  ! mlit_water 近畿JSON: {exc}")

    try:
        dams += _kanto()
    except Exception as exc:  # noqa: BLE001
        print(f"  ! mlit_water 関東HTML: {exc}")

    observed = observed or now_jst().replace(minute=0, second=0, microsecond=0).isoformat(timespec="seconds")

    if lake is not None:
        out.append(Observation(
            slug="biwako-level",
            value=round(lake["value"], 1),
            observed_at=observed,
            detail={"unit": "cm", "basis": "B.S.L.（琵琶湖基準水位）",
                    "station_diff": lake.get("diff"),
                    "caption": _lake_caption(lake["value"])},
        ))

    if dams:
        rates = [d["rate"] for d in dams]
        mean = sum(rates) / len(rates)
        by_region: dict[str, list[float]] = {}
        for d in dams:
            by_region.setdefault(d["region"], []).append(d["rate"])
        out.append(Observation(
            slug="dam-storage",
            value=round(mean, 1),
            observed_at=observed,
            detail={
                "dam_count": len(dams),
                "region_means": {r: round(sum(v) / len(v), 1) for r, v in by_region.items()},
                "dams": sorted(dams, key=lambda d: d["rate"]),
                "caption": _dam_caption(mean, len(dams)),
            },
        ))

    return out
