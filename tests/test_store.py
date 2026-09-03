import tempfile
import unittest
from pathlib import Path

from core import store
from core.models import Observation


def M(**kw):
    base = dict(slug="x", name="テスト", category="自然", unit="", value_type="number",
               comparison_type="absolute", daily_agg="last", collector="c",
               source="s", source_url="u")
    base.update(kw)
    return base


class RecordObservationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        store.HISTORY_DIR = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _rec(self, slug, value, date, agg="last", detail=None):
        obs = Observation(slug=slug, value=value,
                          observed_at=f"{date}T12:00:00+09:00", detail=detail or {})
        store.record_observation(obs, M(slug=slug, daily_agg=agg))

    def test_new_day_appends(self):
        self._rec("t", 10, "2026-09-01")
        self._rec("t", 20, "2026-09-02")
        h = store.load_history("t")
        self.assertEqual([r["value"] for r in h], [10, 20])

    def test_same_day_last_overwrites(self):
        self._rec("t", 10, "2026-09-01", agg="last")
        self._rec("t", 30, "2026-09-01", agg="last")
        h = store.load_history("t")
        self.assertEqual(len(h), 1)
        self.assertEqual(h[0]["value"], 30)
        self.assertEqual(h[0]["runs"], 2)

    def test_same_day_max_keeps_higher_and_its_detail(self):
        self._rec("t", 30, "2026-09-01", agg="max", detail={"place": "A"})
        self._rec("t", 20, "2026-09-01", agg="max", detail={"place": "B"})
        h = store.load_history("t")
        self.assertEqual(h[0]["value"], 30)
        self.assertEqual(h[0]["detail"]["place"], "A")  # 値とdetailが一致

    def test_same_day_min_keeps_lower(self):
        self._rec("t", 5, "2026-09-01", agg="min")
        self._rec("t", 9, "2026-09-01", agg="min")
        self.assertEqual(store.load_history("t")[0]["value"], 5)

    def test_history_stays_sorted(self):
        self._rec("t", 1, "2026-09-03")
        self._rec("t", 2, "2026-09-01")
        self._rec("t", 3, "2026-09-02")
        self.assertEqual([r["date"] for r in store.load_history("t")],
                         ["2026-09-01", "2026-09-02", "2026-09-03"])


class ComputeChangeTests(unittest.TestCase):
    def c(self, metric, cur, prev):
        return store.compute_change(metric, {"value": cur, "date": "2026-09-02"},
                                    {"value": prev, "date": "2026-09-01"})

    def test_no_prev_returns_unavailable(self):
        r = store.compute_change(M(), {"value": 1, "date": "x"}, None)
        self.assertFalse(r["available"])

    def test_absolute(self):
        r = self.c(M(unit="℃"), 38.2, 36.8)
        self.assertEqual(r["direction"], "up")
        self.assertIn("1.4", r["display"])
        self.assertAlmostEqual(r["value"], 1.4, places=1)

    def test_percentage(self):
        r = self.c(M(comparison_type="percentage"), 110, 100)
        self.assertEqual(r["display"], "+10.0%")

    def test_percentage_point(self):
        r = self.c(M(comparison_type="percentage_point", unit="%"), 91, 89)
        self.assertEqual(r["display"], "+2.0pt")

    def test_time_earlier(self):
        r = self.c(M(value_type="time"), 313, 314)  # 1分早い
        self.assertEqual(r["direction"], "down")
        self.assertIn("早く", r["display"])

    def test_duration(self):
        r = self.c(M(value_type="duration"), 770, 773)
        self.assertEqual(r["display"], "-3分")

    def test_moon_wrap_correction(self):
        r = self.c(M(value_type="moon"), 0.5, 29.0)  # 周期またぎ
        self.assertGreaterEqual(r["value"], 0.9)     # -28.5 ではなく +1 付近
        self.assertLessEqual(r["value"], 1.2)

    def test_flat(self):
        r = self.c(M(), 5.0, 5.0)
        self.assertEqual(r["direction"], "flat")


class ChangeScoreTests(unittest.TestCase):
    def test_needs_five_deltas(self):
        hist = [{"value": v, "date": f"2026-09-0{i+1}"} for i, v in enumerate([1, 2, 3])]
        r = store._change_score(M(), hist, {"available": True})
        self.assertIsNone(r["score"])
        self.assertEqual(r["label"], "データ蓄積中")

    def test_big_jump_scores_high(self):
        vals = [10, 11, 9, 10, 11, 9, 40]  # 普段±1、今日+31
        hist = [{"value": v, "date": f"2026-09-{i+1:02d}"} for i, v in enumerate(vals)]
        r = store._change_score(M(), hist, {"available": True})
        self.assertGreater(r["score"], 3.0)
        self.assertEqual(r["label"], "かなり珍しい変化")

    def test_smooth_trend_not_flagged(self):
        # なめらかに毎日 -2 ずつ → 外れ値ではない
        vals = [100 - 2 * i for i in range(15)]
        hist = [{"value": v, "date": f"2026-09-{i+1:02d}"} for i, v in enumerate(vals)]
        r = store._change_score(M(), hist, {"available": True})
        self.assertEqual(r["label"], "通常の範囲")

    def test_countdown_and_astro_excluded(self):
        hist = [{"value": v, "date": f"2026-09-{i+1:02d}"} for i, v in enumerate(range(15, 0, -1))]
        r1 = store._change_score(M(trend="countdown"), hist, {"available": True})
        r2 = store._change_score(M(collector="astro"), hist, {"available": True})
        self.assertIsNone(r1["score"])
        self.assertIsNone(r2["score"])
        self.assertEqual(r1["label"], "決まった動き")


if __name__ == "__main__":
    unittest.main()
