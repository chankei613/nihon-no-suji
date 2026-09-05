"""Collector を順に実行し、履歴へ保存して静的APIを再生成する。

    python -m core.run            # 全 collector
    python -m core.run jma_rank   # 指定した collector だけ

GitHub Actions から毎時呼ばれる。1つの collector が失敗しても他は続行する。
実行のたびに api/health.json（collector ごとの成否）を書く。
"""
from __future__ import annotations

import importlib
import json
import sys
import traceback

from core import registry
from core import store
from core.models import iso, now_jst

COLLECTORS = ["jma_rank", "jma_amedas", "jma_forecast", "jma_typhoon", "jma_warning",
              "mlit_water", "tepco_pg", "p2pquake", "enecho_gas", "boj_fx", "estat", "astro"]

# collector が正常なら「これ以上の数のメトリック」を返すはず、の目安。
# これを下回ったら degraded 扱いにする（形式変更の早期検知）。
EXPECTED_MIN = {
    "jma_rank": 4, "jma_amedas": 5, "jma_forecast": 1, "jma_typhoon": 1, "jma_warning": 0,
    "mlit_water": 2, "tepco_pg": 1, "p2pquake": 1, "enecho_gas": 1, "boj_fx": 1, "estat": 0, "astro": 7,
}


def main(argv: list[str]) -> int:
    targets = [a for a in argv if a in COLLECTORS] or COLLECTORS
    total_obs = 0
    failures: list[str] = []
    health: dict[str, dict] = {}

    for name in targets:
        print(f"[{name}]")
        n = 0
        status = "ok"
        try:
            mod = importlib.import_module(f"collectors.{name}")
            observations = mod.collect()
        except Exception:  # noqa: BLE001
            print(f"  !! collector crashed:\n{traceback.format_exc()}")
            failures.append(name)
            health[name] = {"status": "error", "metrics": 0, "at": iso(now_jst())}
            continue

        for obs in observations:
            metric = registry.BY_SLUG.get(obs.slug)
            if metric is None:
                print(f"  ? 未登録メトリック: {obs.slug}")
                continue
            store.record_observation(obs, metric)
            disp = obs.detail.get("time") or obs.value
            print(f"  ✓ {obs.slug}: {disp}  @ {obs.observed_at}")
            n += 1
            total_obs += 1

        if n < EXPECTED_MIN.get(name, 0):
            status = "degraded"
            print(f"  ⚠ {name}: {n} メトリックのみ（目安 {EXPECTED_MIN.get(name)}）")
        health[name] = {"status": status, "metrics": n, "at": iso(now_jst())}

    result = store.build_api()

    # 前回の health を引き継いで、今回動かさなかった collector の情報を残す
    health_path = store.API_DIR / "health.json"
    prev = {}
    if health_path.exists():
        try:
            prev = {c["name"]: c for c in json.loads(health_path.read_text())["collectors"]}
        except Exception:  # noqa: BLE001
            prev = {}
    merged = []
    for name in COLLECTORS:
        cur = health.get(name)
        if cur:
            merged.append({"name": name, **cur})
        elif name in prev:
            merged.append(prev[name])
    degraded = [c["name"] for c in merged if c.get("status") in ("error", "degraded")]
    health_path.write_text(json.dumps({
        "generated_at": result["generated_at"],
        "overall": "degraded" if degraded else "ok",
        "degraded": degraded,
        "collectors": merged,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"\napi更新: {result['metrics_with_data']} メトリック / {total_obs} 観測 / {result['generated_at']}")
    if degraded:
        print(f"要注意 collector: {', '.join(degraded)}")
    # collector 全滅のときだけ非ゼロ終了（一部失敗は許容）
    return 1 if len(failures) == len(targets) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
