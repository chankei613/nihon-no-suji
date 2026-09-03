"""履歴の保存（data/history/{slug}.jsonl）と静的APIの生成（api/）。

- 履歴は1日1レコード。同じ日に複数回取得したら daily_agg（max/min/last）で代表値を更新。
- api/today.json … 「今日」画面用。全メトリックの現在値＋前日比＋一言。
- api/metrics/{slug}.json … 詳細画面・グラフ用の履歴。
- api/metrics.json … メトリック一覧（メタデータ）。
- api/changes.json … 「変化」画面用。前日比を簡易スコアで並べたもの。
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

from core import registry
from core.models import Observation, iso, now_jst

ROOT = Path(__file__).resolve().parent.parent
HISTORY_DIR = ROOT / "data" / "history"
API_DIR = ROOT / "api"


# ---------------------------------------------------------------- 履歴 I/O

def _history_path(slug: str) -> Path:
    return HISTORY_DIR / f"{slug}.jsonl"


def load_history(slug: str) -> list[dict]:
    path = _history_path(slug)
    if not path.exists():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    out.sort(key=lambda r: r["date"])
    return out


def _save_history(slug: str, records: list[dict]) -> None:
    records.sort(key=lambda r: r["date"])
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    body = "\n".join(json.dumps(r, ensure_ascii=False) for r in records)
    _history_path(slug).write_text(body + "\n", encoding="utf-8")


def record_observation(obs: Observation, metric: dict) -> None:
    """1観測を履歴に反映（日単位で upsert）。"""
    records = load_history(obs.slug)
    by_date = {r["date"]: r for r in records}
    agg = metric.get("daily_agg", "last")
    existing = by_date.get(obs.date)

    incoming = {
        "date": obs.date,
        "value": obs.value,
        "observed_at": obs.observed_at,
        "fetched_at": obs.fetched_at,
        "detail": obs.detail,
        "runs": 1,
    }

    if existing is None:
        by_date[obs.date] = incoming
    else:
        runs = existing.get("runs", 1) + 1
        # agg=max/min で旧値を維持する場合は、値・detail・時刻を一貫させるため
        # レコードごと据え置く（caption と value がズレないように）。
        keep_old = (
            (agg == "max" and existing["value"] >= obs.value)
            or (agg == "min" and existing["value"] <= obs.value)
        )
        chosen = existing if keep_old else incoming
        chosen["runs"] = runs
        by_date[obs.date] = chosen

    _save_history(obs.slug, list(by_date.values()))


# ---------------------------------------------------------------- 前日比

def _prev_record(history: list[dict], today_date: str) -> dict | None:
    earlier = [r for r in history if r["date"] < today_date]
    return earlier[-1] if earlier else None


def today_detail(slug: str) -> dict:
    """当日すでに記録済みの detail（同じ日に累積したい collector 向け）。"""
    today = now_jst().date().isoformat()
    for r in load_history(slug):
        if r["date"] == today:
            return r.get("detail", {}) or {}
    return {}


def compute_change(metric: dict, today: dict, prev: dict | None) -> dict:
    ctype = metric["comparison_type"]
    vtype = metric.get("value_type", "number")
    unit = metric.get("unit", "")

    if prev is None:
        return {"type": ctype, "available": False, "direction": "flat",
                "display": "—", "note": "前日データなし"}

    cur, old = today["value"], prev["value"]
    raw = cur - old

    if ctype == "percentage":
        pct = (raw / old * 100.0) if old else 0.0
        val, display = round(pct, 1), f"{pct:+.1f}%"
    elif ctype == "percentage_point":
        val, display = round(raw, 1), f"{raw:+.1f}pt"
    elif vtype == "time":
        mins = int(round(raw))
        val = mins
        if mins == 0:
            display = "±0分"
        else:
            display = f"{abs(mins)}分{'遅く' if mins > 0 else '早く'}"
    elif vtype == "duration":
        mins = int(round(raw))
        val = mins
        display = "±0分" if mins == 0 else f"{mins:+d}分"
    elif vtype == "moon":
        # 月齢は毎日ほぼ +1。周期をまたぐと大きな負値になるので補正
        if raw < -20:
            raw += 29.530588853
        val, display = round(raw, 1), f"{raw:+.1f}"
    else:
        val = round(raw, 2)
        display = f"{raw:+g}{unit}".replace("+0.0", "±0").replace("-0.0", "±0")

    direction = "flat"
    if raw > 1e-9:
        direction = "up"
    elif raw < -1e-9:
        direction = "down"

    return {"type": ctype, "available": True, "value": val,
            "display": display, "direction": direction, "prev_value": old,
            "prev_date": prev["date"]}


# ---------------------------------------------------------------- 表示ヘルパ

def _value_display(metric: dict, record: dict) -> str:
    vtype = metric.get("value_type", "number")
    unit = metric.get("unit", "")
    if vtype == "time":
        return record.get("detail", {}).get("time") or ""
    if vtype == "moon":
        return f"月齢 {record['value']:.1f}"
    if vtype == "duration":
        m = int(round(record["value"]))
        return f"{m // 60}時間{m % 60:02d}分"
    v = record["value"]
    s = f"{v:g}"
    return f"{s}{unit}" if unit else s


def _caption(metric: dict, record: dict, change: dict) -> str:
    detail_cap = (record.get("detail") or {}).get("caption")
    if detail_cap:
        return detail_cap
    if metric.get("value_type") == "time":
        t = (record.get("detail") or {}).get("time", "")
        verb = "昇る" if "日の出" in metric["name"] else "沈む"
        if change.get("available"):
            if change["value"] == 0:
                return f"きのうと同じ時刻に{verb}"
            return f"きのうより{change['display']}なった"
        return f"きょうは{t}ごろに{verb}"
    return metric["name"]


# ---------------------------------------------------------------- API 生成

def _summary(history: list[dict]) -> dict:
    vals = [r["value"] for r in history]
    recent = vals[-30:]
    latest_detail = history[-1].get("detail", {}) if history else {}
    out = {
        "count": len(history),
        "first_date": history[0]["date"] if history else None,
        "last_date": history[-1]["date"] if history else None,
    }
    if recent:
        out["min_30d"] = min(recent)
        out["max_30d"] = max(recent)
        out["avg_30d"] = round(statistics.fmean(recent), 2)
    for k in ("record_1st", "year_extreme", "all_time_record"):
        if k in latest_detail:
            out[k] = latest_detail[k]
    return out


def _change_score(metric: dict, history: list[dict], change: dict) -> dict:
    if not change.get("available"):
        return {"score": None, "label": "前日データなし"}
    deltas = [history[i]["value"] - history[i - 1]["value"] for i in range(1, len(history))]
    deltas = deltas[-30:]
    if len(deltas) < 5:
        return {"score": None, "label": "データ蓄積中"}
    try:
        sd = statistics.pstdev(deltas)
    except statistics.StatisticsError:
        sd = 0.0
    today_delta = history[-1]["value"] - history[-2]["value"]
    if sd <= 1e-9:
        z = 0.0
    else:
        z = today_delta / sd
    score = round(abs(z), 2)
    if score >= 2.5:
        label = "かなり珍しい変化"
    elif score >= 1.5:
        label = "いつもより大きな変化"
    else:
        label = "通常の範囲"
    return {"score": score, "z": round(z, 2), "label": label}


def build_api() -> dict:
    API_DIR.mkdir(parents=True, exist_ok=True)
    (API_DIR / "metrics").mkdir(parents=True, exist_ok=True)
    generated_at = iso(now_jst())
    today_date = now_jst().date().isoformat()

    today_metrics: list[dict] = []
    changes: list[dict] = []
    catalog: list[dict] = []

    for metric in registry.METRICS:
        slug = metric["slug"]
        history = load_history(slug)
        catalog.append({k: metric[k] for k in (
            "slug", "name", "category", "unit", "comparison_type", "value_type", "source")})
        if not history:
            continue

        cur = history[-1]
        prev = _prev_record(history, cur["date"])
        change = compute_change(metric, cur, prev)
        caption = _caption(metric, cur, change)

        card = {
            "slug": slug,
            "name": metric["name"],
            "category": metric["category"],
            "unit": metric["unit"],
            "value": cur["value"],
            "value_display": _value_display(metric, cur),
            "observed_at": cur["observed_at"],
            "as_of": cur["date"],
            "stale": cur["date"] != today_date,
            "change": change,
            "caption": caption,
            "detail": cur.get("detail", {}),
            "source": {"name": metric["source"], "url": metric["source_url"]},
        }
        today_metrics.append(card)

        score = _change_score(metric, history, change)
        changes.append({
            "slug": slug, "name": metric["name"], "category": metric["category"],
            "value_display": card["value_display"], "change": change,
            "caption": caption, **score,
        })

        (API_DIR / "metrics" / f"{slug}.json").write_text(json.dumps({
            "slug": slug,
            "name": metric["name"],
            "unit": metric["unit"],
            "comparison_type": metric["comparison_type"],
            "value_type": metric.get("value_type", "number"),
            "source": {"name": metric["source"], "url": metric["source_url"]},
            "updated_at": generated_at,
            "summary": _summary(history),
            "history": [{"date": r["date"], "value": r["value"]} for r in history],
            "latest_detail": cur.get("detail", {}),
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    changes.sort(key=lambda c: (c["score"] is not None, c["score"] or 0), reverse=True)

    (API_DIR / "today.json").write_text(json.dumps({
        "generated_at": generated_at,
        "date": today_date,
        "metrics": today_metrics,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    (API_DIR / "changes.json").write_text(json.dumps({
        "generated_at": generated_at,
        "date": today_date,
        "changes": changes,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    (API_DIR / "metrics.json").write_text(json.dumps({
        "generated_at": generated_at,
        "metrics": catalog,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # グラフ一覧用：全メトリックの直近スパークライン（1ファイル）
    series: list[dict] = []
    for card in today_metrics:
        hist = load_history(card["slug"])[-60:]
        series.append({
            "slug": card["slug"],
            "name": card["name"],
            "category": card["category"],
            "unit": card["unit"],
            "value_display": card["value_display"],
            "change": card["change"],
            "points": [{"date": r["date"], "value": r["value"]} for r in hist],
        })
    (API_DIR / "sparklines.json").write_text(json.dumps({
        "generated_at": generated_at,
        "series": series,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {"metrics_with_data": len(today_metrics), "generated_at": generated_at}
