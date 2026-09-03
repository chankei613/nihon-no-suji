"""東京電力パワーグリッド でんき予報CSVから、当日ピークの電力使用率。

https://www.tepco.co.jp/forecast/html/images/juyo-s1-j.csv （Shift_JIS・約5分更新）
複数セクションからなるCSV。先頭に "YYYY/M/D H:MM UPDATE"。
"""
from __future__ import annotations

import re
from datetime import datetime

from core.http import fetch
from core.models import JST, Observation, now_jst

URL = "https://www.tepco.co.jp/forecast/html/images/juyo-s1-j.csv"


def _num(s: str) -> float | None:
    try:
        return float(s.strip())
    except (ValueError, AttributeError):
        return None


def _caption(usage: float, timeband: str) -> str:
    if usage >= 97:
        return "きょうは電力の余裕がとても小さい"
    if usage >= 95:
        return "きょうは電力の余裕が少なめ"
    if timeband:
        return f"ピークは{timeband}の見込み"
    return "電力の需給は落ち着いている"


def collect() -> list[Observation]:
    try:
        text = fetch(URL, timeout=20).decode("shift_jis", errors="replace")
    except Exception as exc:  # noqa: BLE001
        print(f"  ! tepco_pg: {exc}")
        return []

    lines = [ln.strip() for ln in text.splitlines()]
    year = now_jst().year
    m0 = re.match(r"(\d{4})/(\d{1,2})/(\d{1,2})", lines[0]) if lines else None
    if m0:
        year = int(m0.group(1))

    peak: dict = {}
    for i, ln in enumerate(lines):
        if ln.startswith("ピーク時供給力") and i + 1 < len(lines):
            f = lines[i + 1].split(",")
            if len(f) >= 6:
                peak = {
                    "supply": _num(f[0]),
                    "timeband": f[1].strip(),
                    "upd_date": f[2].strip(),
                    "upd_time": f[3].strip(),
                    "reserve_rate": _num(f[4]),
                    "usage_rate": _num(f[5]),
                }
        if ln.startswith("予想最大電力(万kW)") and i + 1 < len(lines):
            f = lines[i + 1].split(",")
            if f:
                peak["forecast_peak_demand"] = _num(f[0])

    # 時間別セクション（先頭が "DATE,TIME,当日実績(万kW)"）の最新実績行 = 直近の実需要。
    # このCSVには "DATE,TIME," で始まる行が複数あるので、最初の当日実績セクションだけ読む。
    current_demand = None
    current_time = None
    current_rate = None
    for i, ln in enumerate(lines):
        if ln.startswith("DATE,TIME,当日実績(万kW)"):
            for row in lines[i + 1:]:
                if not row or not row[0].isdigit():
                    break
                f = row.split(",")
                if len(f) >= 3 and (_num(f[2]) or 0) > 0:  # 未来の時間帯は 0 埋め
                    current_demand = _num(f[2])
                    current_time = f[1].strip()
                    current_rate = _num(f[5]) if len(f) >= 6 else None
            break

    # 太陽光（5分間隔値）セクション … 当日ピークの太陽光率
    solar_peak_rate = None
    solar_peak_mw = None
    for i, ln in enumerate(lines):
        if ln.startswith("DATE,TIME,太陽光"):
            for row in lines[i + 1:]:
                if not row or not row[0].isdigit():
                    break
                f = row.split(",")
                if len(f) >= 4 and (_num(f[3]) or 0) > 0:
                    r = _num(f[3])
                    if solar_peak_rate is None or r > solar_peak_rate:
                        solar_peak_rate, solar_peak_mw = r, _num(f[2])
            break

    usage = peak.get("usage_rate")
    if usage is None:
        print("  ! tepco_pg: 使用率が取れなかった")
        return []

    # 観測時刻 = 供給力情報の更新時刻
    observed_at = now_jst().replace(second=0, microsecond=0).isoformat(timespec="seconds")
    ud, ut = peak.get("upd_date"), peak.get("upd_time")
    if ud and ut and re.match(r"\d{1,2}/\d{1,2}", ud) and re.match(r"\d{1,2}:\d{2}", ut):
        mo, d = (int(x) for x in ud.split("/"))
        h, mi = (int(x) for x in ut.split(":"))
        try:
            observed_at = datetime(year, mo, d, h, mi, tzinfo=JST).isoformat(timespec="seconds")
        except ValueError:
            pass

    detail = {
        "reserve_rate": peak.get("reserve_rate"),
        "peak_supply_10MW": peak.get("supply"),
        "forecast_peak_demand_10MW": peak.get("forecast_peak_demand"),
        "current_demand_10MW": current_demand,
        "current_demand_time": current_time,
        "current_usage_rate": current_rate,
        "peak_timeband": peak.get("timeband"),
        "area": "東京",
        "caption": _caption(usage, peak.get("timeband", "")),
    }
    out = [Observation(slug="elec-usage-tokyo", value=round(usage, 1),
                       observed_at=observed_at, detail=detail)]

    if solar_peak_rate is not None:
        out.append(Observation(
            slug="solar-share-tokyo",
            value=round(solar_peak_rate, 1),
            observed_at=observed_at,
            detail={"peak_output_10MW": solar_peak_mw, "area": "東京",
                    "caption": f"きょうのピークで電力の{solar_peak_rate:g}%を太陽光がまかなった"},
        ))
    return out
