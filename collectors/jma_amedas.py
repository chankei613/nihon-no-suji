"""気象庁アメダスの全地点実況（1ファイル）から、複数の「地点数系」の数字。

    const/amedastable.json  … 地点マスタ（名前・緯度経度）
    data/latest_time.txt    … 最新観測時刻
    data/map/{ts}.json      … 全地点の temp/humidity/wind/precip …（10分ごと）

しきい値超えの地点数は、同じ日のうちに一度でも超えた地点を積み上げる
（時間帯で観測地点のピークがずれるため、瞬間値のカウントだと過小になる）。
積雪は冬しか map.json に載らないので、無ければそのメトリックは出さない。
"""
from __future__ import annotations

import json

from core import registry, store
from core.http import fetch
from core.models import Observation, now_jst

TABLE_URL = "https://www.jma.go.jp/bosai/amedas/const/amedastable.json"
LATEST_URL = "https://www.jma.go.jp/bosai/amedas/data/latest_time.txt"
MAP_URL = "https://www.jma.go.jp/bosai/amedas/data/map/{ts}.json"


def _field(entry: dict, key: str) -> float | None:
    v = entry.get(key)
    if isinstance(v, list) and v and isinstance(v[0], (int, float)):
        # flag: 0=正常。1以上は欠測・資料不足など
        if len(v) > 1 and isinstance(v[1], int) and v[1] not in (0,):
            return None
        return float(v[0])
    return None


def _accumulate_stations(slug: str, current: set[str]) -> list[str]:
    prior = set(store.today_detail(slug).get("station_ids", []))
    return sorted(prior | current)


def collect() -> list[Observation]:
    try:
        latest = fetch(LATEST_URL, timeout=15).decode("utf-8").strip()
        ts = latest[:19].replace("-", "").replace("T", "").replace(":", "")
        table = json.loads(fetch(TABLE_URL, timeout=20))
        obs_map = json.loads(fetch(MAP_URL.format(ts=ts), timeout=20))
    except Exception as exc:  # noqa: BLE001
        print(f"  ! jma_amedas: {exc}")
        return []

    def name(sid: str) -> str:
        return (table.get(sid) or {}).get("kjName", sid)

    observed_at = latest[:19] + "+09:00" if len(latest) >= 19 else \
        now_jst().replace(second=0, microsecond=0).isoformat(timespec="seconds")

    temps = {sid: t for sid, e in obs_map.items() if (t := _field(e, "temp")) is not None}
    winds = {sid: w for sid, e in obs_map.items() if (w := _field(e, "wind")) is not None}
    hums = {sid: h for sid, e in obs_map.items() if (h := _field(e, "humidity")) is not None}
    snows = {sid: s for sid, e in obs_map.items() if (s := _field(e, "snow")) is not None}
    rain10 = {sid: r for sid, e in obs_map.items() if (r := _field(e, "precipitation10m")) is not None}
    rain1h = {sid: r for sid, e in obs_map.items() if (r := _field(e, "precipitation1h")) is not None}
    rain3h = {sid: r for sid, e in obs_map.items() if (r := _field(e, "precipitation3h")) is not None}
    # 気圧は標高100m以下の局のみ（現地気圧≒海面気圧とみなせる）
    pressures = {
        sid: p for sid, e in obs_map.items()
        if (p := _field(e, "pressure")) is not None
        and ((table.get(sid) or {}).get("alt") or 9999) <= 100
    }

    out: list[Observation] = []

    # --- しきい値超えの地点数（当日累積） ---
    def threshold_count(slug: str, ids: set[str], cap: str) -> Observation:
        acc = _accumulate_stations(slug, ids)
        return Observation(slug, len(acc), observed_at,
                           {"station_ids": acc, "now": len(ids), "caption": cap})

    if temps:
        hot35 = {s for s, t in temps.items() if t >= 35.0}
        hot30 = {s for s, t in temps.items() if t >= 30.0}
        cold0 = {s for s, t in temps.items() if t < 0.0}
        out.append(threshold_count("hot-points-35", hot35, "きょう35℃以上になった地点"))
        out.append(threshold_count("hot-points-30", hot30, "きょう30℃以上になった地点"))
        out.append(threshold_count("cold-points-0", cold0, "きょう0℃を下回った地点"))

        # 真冬日（一度も0℃以上にならなかった地点）／熱帯夜（一度も25℃を下回らなかった地点）
        # は「しきい値を破った地点」の逆なので、自分の detail に
        # 破った地点の集合と観測した地点の集合を両方積み上げて差分を取る。
        # ※ 暦日（0-24時JST）で区切っており、熱帯夜の本来の定義（夕方-翌朝）とは厳密には異なる近似。
        def complement_count(slug: str, broke_key: str, seen_key: str,
                             broke_now: set[str], seen_now: set[str], cap_yes: str, cap_no: str) -> Observation:
            prior = store.today_detail(slug)
            broke = sorted(set(prior.get(broke_key, [])) | broke_now)
            seen = sorted(set(prior.get(seen_key, [])) | seen_now)
            n = len(set(seen) - set(broke))
            return Observation(slug, n, observed_at, {
                broke_key: broke, seen_key: seen,
                "caption": cap_yes if n else cap_no,
            })

        mild_now = {s for s, t in temps.items() if t >= 0.0}
        out.append(complement_count("ice-day-points", "mild_station_ids", "reported_station_ids",
                                    mild_now, set(temps.keys()),
                                    "きょう一度も0℃以上にならなかった地点（真冬日）", "きょうは全地点が0℃以上になった"))

        cool_now = {s for s, t in temps.items() if t < 25.0}
        out.append(complement_count("tropical-night-points", "cool_station_ids", "reported_station_ids",
                                    cool_now, set(temps.keys()),
                                    "きょう一度も25℃を下回らなかった地点（熱帯夜）", "きょうは全地点が25℃を下回った"))

        # 気温差は「人が住む地点どうし」で見たいので山岳（標高1000m超）を除く
        def lowland(sid: str) -> bool:
            return ((table.get(sid) or {}).get("alt") or 0) <= 1000
        low = {s: t for s, t in temps.items() if lowland(s)} or temps
        hot_s = max(low, key=low.get)
        cold_s = min(low, key=low.get)
        spread = round(low[hot_s] - low[cold_s], 1)
        out.append(Observation("national-temp-spread", spread, observed_at, {
            "hot": {"place": name(hot_s), "temp": low[hot_s]},
            "cold": {"place": name(cold_s), "temp": low[cold_s]},
            "caption": f"{name(hot_s)}{low[hot_s]:g}℃ と {name(cold_s)}{low[cold_s]:g}℃ の差",
        }))

    if rain10:
        wet = {s for s, r in rain10.items() if r > 0}
        out.append(threshold_count("rain-points", wet, "きょう雨が降った地点"))
    if rain1h:
        rs = max(rain1h, key=rain1h.get)
        if rain1h[rs] > 0:
            v = rain1h[rs]
            note = "バケツをひっくり返したような雨" if v >= 30 else \
                   "激しい雨" if v >= 20 else "この1時間でいちばん降った"
            out.append(Observation("max-precip-1h", round(v, 1), observed_at, {
                "place": name(rs), "caption": f"{name(rs)}｜{note}",
            }))
    if rain3h:
        rs = max(rain3h, key=rain3h.get)
        if rain3h[rs] > 0:
            out.append(Observation("max-precip-3h", round(rain3h[rs], 1), observed_at, {
                "place": name(rs), "caption": f"{name(rs)}｜この3時間でいちばん激しく降った",
            }))

    if pressures:
        ps = min(pressures, key=pressures.get)
        p = pressures[ps]
        if p < 990:
            pc = f"{name(ps)}｜台風や発達した低気圧が近い"
        elif p >= 1022:
            pc = f"{name(ps)}｜強い高気圧に覆われている"
        else:
            pc = f"{name(ps)}｜全国でいちばん気圧が低い"
        out.append(Observation("min-pressure", round(p, 1), observed_at,
                               {"place": name(ps), "caption": pc}))

    if winds:
        ws = max(winds, key=winds.get)
        out.append(Observation("max-wind", round(winds[ws], 1), observed_at, {
            "place": name(ws), "caption": f"{name(ws)}｜全国でいちばん風が強い（10分平均）",
        }))

    if hums:
        hs = min(hums, key=hums.get)
        out.append(Observation("min-humidity", round(hums[hs], 0), observed_at, {
            "place": name(hs), "caption": f"{name(hs)}｜全国でいちばん空気が乾いている",
        }))

    # --- 東京の日照時間（sun1h を当日ぶん積み上げ） ---
    tokyo = obs_map.get("44132")
    if tokyo is not None:
        sun_h = _field(tokyo, "sun1h")
        if sun_h is not None:
            prior = store.today_detail("tokyo-sunshine-hours")
            total_min = float(prior.get("total_minutes", 0.0))
            if prior.get("last_observed_at") != observed_at:
                total_min = round(total_min + sun_h * 60, 1)
            out.append(Observation("tokyo-sunshine-hours", int(round(total_min)), observed_at, {
                "total_minutes": total_min, "last_observed_at": observed_at,
                "caption": "きょうはまだ日照なし" if total_min == 0 else "きょうの東京の日照時間（ここまでの積算）",
            }))

    # --- 富士山頂の気温 ---
    if "50066" in temps:
        ft = temps["50066"]
        if ft <= -10:
            fc = "真冬並みの厳しい寒さ"
        elif ft <= 0:
            fc = "氷点下。街とはまるで別世界"
        elif ft < 10:
            fc = "夏でもひんやり"
        else:
            fc = "富士山頂も暖かい"
        out.append(Observation("fuji-temp", round(ft, 1), observed_at,
                               {"place": "富士山（標高3775m）", "caption": fc}))

    # --- 積雪（冬のみ map.json に出現） ---
    if snows:
        snow_pts = {s for s, v in snows.items() if v > 0}
        if snow_pts:
            acc = _accumulate_stations("snow-points", snow_pts)
            out.append(Observation("snow-points", len(acc), observed_at,
                                   {"station_ids": acc, "now": len(snow_pts),
                                    "caption": "雪が積もっている地点"}))
        ss = max(snows, key=snows.get)
        if snows[ss] > 0:
            out.append(Observation("max-snow", round(snows[ss], 0), observed_at, {
                "place": name(ss), "caption": f"{name(ss)}｜全国でいちばん雪が深い",
            }))

    return [o for o in out if o.slug in registry.BY_SLUG]
