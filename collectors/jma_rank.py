"""気象庁「最新の気象データ」ランキングCSVから全国の最高/最低気温・最大24時間降水量。

CSVはShift_JIS。1行=1観測所。毎時25分ごろ更新。
値の列に加え、平年差・前日差・今年の極値・観測史上1位まで入っているので detail に保存する。
"""
from __future__ import annotations

import csv
import io
import re
from datetime import datetime, timedelta

from core import registry
from core.http import fetch
from core.models import JST, Observation, now_jst

GOOD_QUALITY = {"4", "5", "8"}  # 8=正常, 4/5=速報値（当日途中なので想定内）


def _load(url: str) -> tuple[list[str], list[list[str]]]:
    text = fetch(url, timeout=25).decode("shift_jis", errors="replace")
    reader = csv.reader(io.StringIO(text))
    header = next(reader)
    return header, [r for r in reader if r]


def _col(header: list[str], pattern: str) -> int | None:
    for i, h in enumerate(header):
        if re.search(pattern, h):
            return i
    return None


def _num(s: str | None) -> float | None:
    try:
        return float((s or "").strip())
    except ValueError:
        return None


def _place(s: str) -> str:
    return re.sub(r"（.*?）|\(.*?\)", "", s or "").strip()


def _observed_at(row: list[str], ci_year: int) -> str:
    try:
        y, mo, d, h, mi = (int(row[ci_year + k]) for k in range(5))
        carry = 0
        if h >= 24:
            h, carry = h - 24, 1
        dt = datetime(y, mo, d, h, mi, tzinfo=JST) + timedelta(days=carry)
        return dt.isoformat(timespec="seconds")
    except (ValueError, IndexError):
        return now_jst().replace(second=0, microsecond=0).isoformat(timespec="seconds")


def _caption(slug: str, place: str, value: float) -> str:
    if slug == "max-temp":
        return f"{place}｜きょう日本でいちばん暑い"
    if slug == "min-temp":
        return f"{place}｜きょう日本でいちばん寒い"
    if slug == "max-precip-24h":
        if value <= 0:
            return "全国的に、まとまった雨は降っていない"
        return f"{place}｜この24時間でいちばん降った"
    return place


def _collect_one(m: dict) -> Observation | None:
    header, rows = _load(m["source_url"])
    ci_year = _col(header, r"現在時刻\(年\)")
    is_precip = "precip" in m["slug"]

    if is_precip:
        ci_val = _col(header, r"日の最大値\(mm\)$")
        ci_record = _col(header, r"観測史上1位の値\(mm\)$")
        ci_norm = ci_prevdiff = ci_year_flag = None
    else:
        ci_val = _col(header, r"日の最(高|低)気温\(℃\)$")
        ci_record = _col(header, r"観測史上1位の値（℃）$")
        ci_norm = _col(header, r"^平年差（℃）$")
        ci_prevdiff = _col(header, r"^前日差（℃）$")
        ci_year_flag = _col(header, r"^(今年最高|今季最低)$")
    ci_extreme = _col(header, r"^極値更新$")

    if ci_val is None or ci_year is None:
        raise RuntimeError(f"列が見つからない: {m['slug']}")

    agg = m["daily_agg"]  # max / min
    best_row: list[str] | None = None
    best_val = None
    for row in rows:
        if len(row) <= ci_val:
            continue
        v = _num(row[ci_val])
        if v is None:
            continue
        q = (row[ci_val + 1] or "").strip() if len(row) > ci_val + 1 else ""
        if q not in GOOD_QUALITY:
            continue
        if best_val is None or (agg == "max" and v > best_val) or (agg == "min" and v < best_val):
            best_row, best_val = row, v

    if best_row is None:
        raise RuntimeError(f"有効な値なし: {m['slug']}")

    place = _place(best_row[2]) if len(best_row) > 2 else ""
    pref = re.sub(r"\s+", "", best_row[1]) if len(best_row) > 1 else ""

    detail: dict = {"place": place, "pref": pref, "caption": _caption(m["slug"], place, best_val)}
    for key, ci in (("normal_diff", ci_norm), ("station_prev_diff", ci_prevdiff),
                    ("record_1st", ci_record)):
        if ci is not None and len(best_row) > ci:
            val = _num(best_row[ci])
            if val is not None:
                detail[key] = val
    if ci_year_flag is not None and len(best_row) > ci_year_flag:
        detail["year_extreme"] = (best_row[ci_year_flag] or "").strip() == "1"
    if ci_extreme is not None and len(best_row) > ci_extreme:
        detail["all_time_record"] = (best_row[ci_extreme] or "").strip() == "1"

    return Observation(
        slug=m["slug"],
        value=round(best_val, 2),
        observed_at=_observed_at(best_row, ci_year),
        detail=detail,
    )


def collect() -> list[Observation]:
    out: list[Observation] = []
    for m in registry.metrics_for("jma_rank"):
        try:
            obs = _collect_one(m)
            if obs:
                out.append(obs)
        except Exception as exc:  # noqa: BLE001 - 1メトリック失敗で他を止めない
            print(f"  ! jma_rank {m['slug']}: {exc}")
    return out
