"""東京の日の出・日の入り・月齢。外部取得なし（NOAA式の自前計算）。

突き合わせ用: 国立天文台 暦計算室 https://eco.mtk.nao.ac.jp/cgi-bin/koyomi/sunmoon.cgi
"""
from __future__ import annotations

import math
from datetime import date

from core.models import Observation, now_jst

# 東京（気象庁の観測地点に近い代表点）
LAT = 35.6544
LON = 139.7447
JST_OFFSET = 9.0
SYNODIC = 29.530588853


def _julian_day(y: int, m: int, d: float) -> float:
    """d は小数可（例: 1.5 は正午）。"""
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    return math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1)) + d + b - 1524.5


def _sun_event(year: int, month: int, day: int, rising: bool, zenith: float = 90.833) -> float | None:
    """返り値: その日の日の出/日の入りの「0時からの分」（JST）。極夜等で無ければ None。"""
    # 年間通日
    n = (_julian_day(year, month, day) - _julian_day(year, 1, 1)) + 1
    lng_hour = LON / 15.0
    t = n + ((6.0 if rising else 18.0) - lng_hour) / 24.0

    m = 0.9856 * t - 3.289
    l = m + 1.916 * math.sin(math.radians(m)) + 0.020 * math.sin(math.radians(2 * m)) + 282.634
    l %= 360.0

    ra = math.degrees(math.atan(0.91764 * math.tan(math.radians(l)))) % 360.0
    ra += (math.floor(l / 90.0) * 90.0) - (math.floor(ra / 90.0) * 90.0)
    ra /= 15.0

    sin_dec = 0.39782 * math.sin(math.radians(l))
    cos_dec = math.cos(math.asin(sin_dec))
    cos_h = (math.cos(math.radians(zenith)) - sin_dec * math.sin(math.radians(LAT))) / (
        cos_dec * math.cos(math.radians(LAT))
    )
    if cos_h > 1 or cos_h < -1:
        return None

    h = (360.0 - math.degrees(math.acos(cos_h))) if rising else math.degrees(math.acos(cos_h))
    h /= 15.0

    local_mean = h + ra - 0.06571 * t - 6.622
    ut = (local_mean - lng_hour) % 24.0
    local = (ut + JST_OFFSET) % 24.0
    return round(local * 60.0, 1)


SEKKI = ["春分", "清明", "穀雨", "立夏", "小満", "芒種", "夏至", "小暑", "大暑",
         "立秋", "処暑", "白露", "秋分", "寒露", "霜降", "立冬", "小雪", "大雪",
         "冬至", "小寒", "大寒", "立春", "雨水", "啓蟄"]


def _solar_longitude(jd: float) -> float:
    """太陽の視黄経（度）。近似式。"""
    d = jd - 2451545.0
    g = math.radians((357.529 + 0.98560028 * d) % 360)
    q = (280.459 + 0.98564736 * d) % 360
    return (q + 1.915 * math.sin(g) + 0.020 * math.sin(2 * g)) % 360


def _next_sekki(year: int, month: int, day: int) -> tuple[str, int]:
    """(次の二十四節気の名前, その日までの日数)。"""
    jd0 = _julian_day(year, month, day + 0.5)  # 正午UT基準でざっくり
    lon0 = _solar_longitude(jd0)
    target = (math.floor(lon0 / 15.0) + 1) * 15.0
    for n in range(1, 20):
        lon = _solar_longitude(jd0 + n)
        # 15度の境界を越えたら到達
        crossed = (lon - lon0) % 360 >= (target - lon0) % 360
        if crossed:
            idx = int(round(target / 15.0)) % 24
            return SEKKI[idx], n
    idx = int(round(target / 15.0)) % 24
    return SEKKI[idx], 15


def _hhmm(minutes: float) -> str:
    m = int(round(minutes))
    return f"{m // 60:02d}:{m % 60:02d}"


def _moon(year: int, month: int, day: int) -> tuple[float, str, int]:
    # 正午JST = 03:00 UTC → 日の小数部 0.125
    jd = _julian_day(year, month, day + (12.0 - JST_OFFSET) / 24.0)
    age = (jd - 2451550.1) % SYNODIC
    full_age = SYNODIC / 2.0
    to_full = (full_age - age) if age <= full_age else (SYNODIC - age + full_age)
    phases = [
        (1.85, "新月"), (5.54, "三日月"), (9.23, "上弦の月"), (12.91, "十三夜月"),
        (16.61, "満月"), (20.30, "寝待月"), (23.99, "下弦の月"), (27.68, "有明の月"),
    ]
    name = "新月"
    for limit, label in phases:
        if age < limit:
            name = label
            break
    return round(age, 1), name, round(to_full)


def collect() -> list[Observation]:
    now = now_jst()
    y, mo, d = now.year, now.month, now.day
    observed_at = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat(timespec="seconds")
    out: list[Observation] = []

    sunrise = _sun_event(y, mo, d, rising=True)
    sunset = _sun_event(y, mo, d, rising=False)
    if sunrise is not None:
        out.append(Observation("sunrise-tokyo", sunrise, observed_at,
                               {"time": _hhmm(sunrise), "place": "東京"}))
    if sunset is not None:
        out.append(Observation("sunset-tokyo", sunset, observed_at,
                               {"time": _hhmm(sunset), "place": "東京"}))
    if sunrise is not None and sunset is not None:
        length = round(sunset - sunrise, 1)
        h, mi = int(length // 60), int(round(length % 60))
        out.append(Observation("day-length-tokyo", length, observed_at,
                               {"place": "東京", "caption": f"きょうの昼は{h}時間{mi}分"}))

    # 今年の残り日数
    today = date(y, mo, d)
    left = (date(y, 12, 31) - today).days
    passed = (today - date(y, 1, 1)).days
    pct = round(passed / ((date(y, 12, 31) - date(y, 1, 1)).days) * 100)
    out.append(Observation("days-left-year", left, observed_at,
                           {"caption": f"{y}年は{pct}%が過ぎた", "days_passed": passed}))

    sekki_name, sekki_days = _next_sekki(y, mo, d)
    out.append(Observation("days-to-sekki", sekki_days, observed_at,
                           {"next": sekki_name, "caption": f"次の二十四節気「{sekki_name}」まで"}))

    age, phase, to_full = _moon(y, mo, d)
    if 13.5 < age < 16.0:
        cap = "きょうは満月ごろ"
    elif age < 1.4 or age > SYNODIC - 1.4:
        cap = "きょうは新月ごろ"
    else:
        cap = f"次の満月まであと{max(to_full, 0)}日"
    out.append(Observation("moon-age", age, observed_at,
                           {"phase": phase, "days_to_full": to_full, "caption": cap}))
    out.append(Observation("days-to-full-moon", to_full, observed_at,
                           {"phase": phase, "caption": cap}))
    return out
