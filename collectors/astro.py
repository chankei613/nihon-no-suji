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
    m = int(round(minutes)) % 1440
    return f"{m // 60:02d}:{m % 60:02d}"


def _moon_radec(jd: float) -> tuple[float, float]:
    """月の赤経・赤緯（度）。Schlyter の低精度計算＋主要摂動。"""
    d = jd - 2451543.5
    rad = math.radians

    def norm(x: float) -> float:
        return x % 360.0

    N = norm(125.1228 - 0.0529538083 * d)
    i = 5.1454
    w = norm(318.0634 + 0.1643573223 * d)
    a = 60.2666
    e = 0.054900
    M = norm(115.3654 + 13.0649929509 * d)

    ea = M + (180 / math.pi) * e * math.sin(rad(M)) * (1 + e * math.cos(rad(M)))
    for _ in range(2):
        ea = ea - (ea - (180 / math.pi) * e * math.sin(rad(ea)) - M) / (
            1 - e * math.cos(rad(ea)))

    x = a * (math.cos(rad(ea)) - e)
    y = a * math.sqrt(1 - e * e) * math.sin(rad(ea))
    r = math.hypot(x, y)
    v = norm(math.degrees(math.atan2(y, x)))

    xec = r * (math.cos(rad(N)) * math.cos(rad(v + w))
               - math.sin(rad(N)) * math.sin(rad(v + w)) * math.cos(rad(i)))
    yec = r * (math.sin(rad(N)) * math.cos(rad(v + w))
               + math.cos(rad(N)) * math.sin(rad(v + w)) * math.cos(rad(i)))
    zec = r * math.sin(rad(v + w)) * math.sin(rad(i))

    lon = math.degrees(math.atan2(yec, xec))
    lat = math.degrees(math.atan2(zec, math.hypot(xec, yec)))

    # 主要摂動（太陽の平均引数 Ms, 平均黄経 Ls が必要）
    Ms = norm(356.0470 + 0.9856002585 * d)
    Ls = norm(282.9404 + 4.70935e-5 * d + Ms
              + (180 / math.pi) * 0.016709 * math.sin(rad(Ms)))
    Lm = norm(N + w + M)
    D = norm(Lm - Ls)
    F = norm(Lm - N)

    lon += (-1.274 * math.sin(rad(M - 2 * D))
            + 0.658 * math.sin(rad(2 * D))
            - 0.186 * math.sin(rad(Ms))
            - 0.059 * math.sin(rad(2 * M - 2 * D))
            - 0.057 * math.sin(rad(M - 2 * D + Ms))
            + 0.053 * math.sin(rad(M + 2 * D))
            + 0.046 * math.sin(rad(2 * D - Ms))
            + 0.041 * math.sin(rad(M - Ms))
            - 0.035 * math.sin(rad(D))
            - 0.031 * math.sin(rad(M + Ms)))
    lat += (-0.173 * math.sin(rad(F - 2 * D))
            - 0.055 * math.sin(rad(M - F - 2 * D))
            - 0.046 * math.sin(rad(M + F - 2 * D))
            + 0.033 * math.sin(rad(F + 2 * D))
            + 0.017 * math.sin(rad(2 * M + F)))

    # 黄道傾斜
    ecl = 23.4393 - 3.563e-7 * d
    xe = math.cos(rad(lon)) * math.cos(rad(lat))
    ye = math.sin(rad(lon)) * math.cos(rad(lat))
    ze = math.sin(rad(lat))
    xq = xe
    yq = ye * math.cos(rad(ecl)) - ze * math.sin(rad(ecl))
    zq = ye * math.sin(rad(ecl)) + ze * math.cos(rad(ecl))
    ra = math.degrees(math.atan2(yq, xq)) % 360
    dec = math.degrees(math.atan2(zq, math.hypot(xq, yq)))
    return ra, dec


def _moon_events(year: int, month: int, day: int) -> tuple[float | None, float | None]:
    """(月の出, 月の入り) を 0時からの分(JST)で。見つからなければ None。"""
    rise = sett = None
    prev_alt = None
    for step in range(0, 24 * 6 + 1):  # 10分刻み
        minutes = step * 10
        jd = _julian_day(year, month, day + (minutes / 60.0 - JST_OFFSET) / 24.0)
        ra, dec = _moon_radec(jd)
        # 恒星時
        d = jd - 2451545.0
        gmst = (280.46061837 + 360.98564736629 * d) % 360
        lst = (gmst + LON) % 360
        ha = (lst - ra + 180) % 360 - 180
        alt = math.degrees(math.asin(
            math.sin(math.radians(LAT)) * math.sin(math.radians(dec))
            + math.cos(math.radians(LAT)) * math.cos(math.radians(dec))
            * math.cos(math.radians(ha))))
        alt += 0.125  # 視差 - 大気差 - 視半径 のざっくり補正
        if prev_alt is not None:
            if prev_alt < 0 <= alt and rise is None:
                rise = minutes - 10 * (alt / (alt - prev_alt))
            if prev_alt >= 0 > alt and sett is None:
                sett = minutes - 10 * (alt / (alt - prev_alt))
        prev_alt = alt
    return (round(rise, 1) if rise is not None else None,
            round(sett, 1) if sett is not None else None)


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


def collect(for_date: date | None = None) -> list[Observation]:
    day0 = for_date or now_jst().date()
    y, mo, d = day0.year, day0.month, day0.day
    observed_at = f"{day0.isoformat()}T00:00:00+09:00"
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

    mrise, mset = _moon_events(y, mo, d)
    if mrise is not None:
        out.append(Observation("moonrise-tokyo", mrise, observed_at,
                               {"time": _hhmm(mrise), "place": "東京",
                                "caption": f"月が昇るのは{_hhmm(mrise)}ごろ"}))
    if mset is not None:
        out.append(Observation("moonset-tokyo", mset, observed_at,
                               {"time": _hhmm(mset), "place": "東京",
                                "caption": f"月が沈むのは{_hhmm(mset)}ごろ"}))

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
