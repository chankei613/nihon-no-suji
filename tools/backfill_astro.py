"""こよみ系メトリック（自前計算）の履歴を過去にさかのぼって埋める。

日の出入り・月齢・二十四節気などは計算だけで過去の値が出せるので、
グラフが最初から見られるように N 日分を生成する。

    python -m tools.backfill_astro          # 過去120日
    python -m tools.backfill_astro 365       # 日数指定

外部取得が要るメトリック（気温・ダム等）は対象外。
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta

from collectors import astro
from core import registry, store


def main(days: int = 120) -> None:
    today = astro.now_jst().date()
    start = today - timedelta(days=days)

    # slug -> {date -> record}
    buckets: dict[str, dict[str, dict]] = {}
    cur = start
    while cur <= today:
        for obs in astro.collect(for_date=cur):
            rec = {
                "date": obs.date,
                "value": obs.value,
                "observed_at": obs.observed_at,
                "fetched_at": obs.fetched_at,
                "detail": obs.detail,
                "runs": 1,
                "backfilled": True,
            }
            buckets.setdefault(obs.slug, {})[obs.date] = rec
        cur += timedelta(days=1)

    for slug, by_date in buckets.items():
        if slug not in registry.BY_SLUG:
            continue
        existing = {r["date"]: r for r in store.load_history(slug)}
        added = 0
        for dstr, rec in by_date.items():
            if dstr not in existing:          # 実測が既にある日は上書きしない
                existing[dstr] = rec
                added += 1
        records = sorted(existing.values(), key=lambda r: r["date"])
        path = store.HISTORY_DIR / f"{slug}.jsonl"
        path.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n",
            encoding="utf-8",
        )
        print(f"  {slug}: +{added} 日 (計 {len(records)})")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    main(n)
