import json
import tempfile
import unittest
from pathlib import Path

from core import registry, store
from core.models import Observation


class BuildApiSmokeTests(unittest.TestCase):
    def setUp(self):
        self._h = tempfile.TemporaryDirectory()
        self._a = tempfile.TemporaryDirectory()
        store.HISTORY_DIR = Path(self._h.name)
        store.API_DIR = Path(self._a.name)
        # 2メトリックに3日分の履歴を作る
        for slug, agg in (("max-temp", "max"), ("sunset-tokyo", "last")):
            for i, d in enumerate(("2026-09-01", "2026-09-02", "2026-09-03")):
                detail = {"time": "18:07"} if slug == "sunset-tokyo" else {"place": "館林"}
                store.record_observation(
                    Observation(slug=slug, value=30 + i, observed_at=f"{d}T12:00:00+09:00",
                                detail=detail),
                    registry.BY_SLUG[slug])

    def tearDown(self):
        self._h.cleanup()
        self._a.cleanup()

    def test_build_api_writes_valid_json(self):
        result = store.build_api()
        self.assertGreaterEqual(result["metrics_with_data"], 2)

        api = Path(self._a.name)
        for name in ("today.json", "changes.json", "metrics.json", "sparklines.json"):
            data = json.loads((api / name).read_text())
            self.assertIn("generated_at", data)

        today = json.loads((api / "today.json").read_text())
        slugs = {m["slug"] for m in today["metrics"]}
        self.assertIn("max-temp", slugs)
        self.assertIn("sunset-tokyo", slugs)

        for m in today["metrics"]:
            self.assertTrue(m["value_display"])            # 空でない
            self.assertIn(m["change"]["direction"], {"up", "down", "flat"})
            if m["slug"] == "sunset-tokyo":
                self.assertRegex(m["value_display"], r"^\d{2}:\d{2}$")

        # per-metric ファイル
        detail = json.loads((api / "metrics" / "max-temp.json").read_text())
        self.assertEqual(len(detail["history"]), 3)
        self.assertEqual(detail["summary"]["count"], 3)

        spark = json.loads((api / "sparklines.json").read_text())
        self.assertEqual(len(spark["series"]), len([m for m in today["metrics"]]))

    def test_changes_sorted_scored_first(self):
        store.build_api()
        changes = json.loads((Path(self._a.name) / "changes.json").read_text())["changes"]
        scored = [c["score"] for c in changes if c["score"] is not None]
        self.assertEqual(scored, sorted(scored, reverse=True))


if __name__ == "__main__":
    unittest.main()
