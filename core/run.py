"""Collector を順に実行し、履歴へ保存して静的APIを再生成する。

    python -m core.run            # 全 collector
    python -m core.run jma_rank   # 指定した collector だけ

GitHub Actions から毎時呼ばれる。1つの collector が失敗しても他は続行する。
"""
from __future__ import annotations

import importlib
import sys
import traceback

from core import registry
from core import store

COLLECTORS = ["jma_rank", "mlit_water", "tepco_pg", "p2pquake", "astro"]


def main(argv: list[str]) -> int:
    targets = [a for a in argv if a in COLLECTORS] or COLLECTORS
    total_obs = 0
    failures: list[str] = []

    for name in targets:
        print(f"[{name}]")
        try:
            mod = importlib.import_module(f"collectors.{name}")
            observations = mod.collect()
        except Exception:  # noqa: BLE001
            print(f"  !! collector crashed:\n{traceback.format_exc()}")
            failures.append(name)
            continue

        for obs in observations:
            metric = registry.BY_SLUG.get(obs.slug)
            if metric is None:
                print(f"  ? 未登録メトリック: {obs.slug}")
                continue
            store.record_observation(obs, metric)
            disp = obs.detail.get("time") or obs.value
            print(f"  ✓ {obs.slug}: {disp}  @ {obs.observed_at}")
            total_obs += 1

    result = store.build_api()
    print(f"\napi更新: {result['metrics_with_data']} メトリック / {total_obs} 観測 / {result['generated_at']}")
    if failures:
        print(f"失敗した collector: {', '.join(failures)}")
    # collector 全滅のときだけ非ゼロ終了（一部失敗は許容）
    return 1 if len(failures) == len(targets) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
