import unittest
from datetime import date

from collectors import astro


class SunTests(unittest.TestCase):
    def test_tokyo_sunrise_sunset_known_date(self):
        # 2026-09-03 東京: 日の出 ≒ 5:14、日の入り ≒ 18:07（±3分）
        sr = astro._sun_event(2026, 9, 3, rising=True)
        ss = astro._sun_event(2026, 9, 3, rising=False)
        self.assertAlmostEqual(sr, 5 * 60 + 14, delta=4)
        self.assertAlmostEqual(ss, 18 * 60 + 7, delta=4)

    def test_summer_day_longer_than_winter(self):
        june = (astro._sun_event(2026, 6, 21, rising=False)
                - astro._sun_event(2026, 6, 21, rising=True))
        dec = (astro._sun_event(2026, 12, 21, rising=False)
               - astro._sun_event(2026, 12, 21, rising=True))
        self.assertGreater(june, dec + 120)  # 夏至は冬至より2時間以上長い

    def test_summer_solstice_is_longest(self):
        solstice = (astro._sun_event(2026, 6, 21, rising=False)
                    - astro._sun_event(2026, 6, 21, rising=True))
        self.assertGreater(solstice, 14 * 60)  # 東京の夏至は約14時間35分


class MoonTests(unittest.TestCase):
    def test_moon_age_in_range(self):
        for mo in range(1, 13):
            age, _phase, _to_full = astro._moon(2026, mo, 15)
            self.assertGreaterEqual(age, 0)
            self.assertLess(age, astro.SYNODIC)

    def test_moon_age_advances_about_one_per_day(self):
        a1, *_ = astro._moon(2026, 9, 10)
        a2, *_ = astro._moon(2026, 9, 11)
        diff = (a2 - a1) % astro.SYNODIC
        self.assertAlmostEqual(diff, 1.0, delta=0.15)

    def test_moonrise_later_each_day(self):
        r1, _ = astro._moon_events(2026, 9, 10)
        r2, _ = astro._moon_events(2026, 9, 11)
        if r1 is not None and r2 is not None:
            delta = (r2 - r1) % 1440
            self.assertGreater(delta, 20)   # 毎日およそ50分遅れる
            self.assertLess(delta, 90)


class SekkiTests(unittest.TestCase):
    def test_next_sekki_from_early_september(self):
        name, days = astro._next_sekki(2026, 9, 3)
        self.assertEqual(name, "白露")           # 9/7ごろ
        self.assertGreaterEqual(days, 2)
        self.assertLessEqual(days, 6)

    def test_days_always_positive_and_bounded(self):
        for mo in range(1, 13):
            _, days = astro._next_sekki(2026, mo, 1)
            self.assertGreater(days, 0)
            self.assertLessEqual(days, 16)


class CollectTests(unittest.TestCase):
    def test_collect_for_past_date_is_deterministic(self):
        a = {o.slug: o.value for o in astro.collect(for_date=date(2026, 5, 1))}
        b = {o.slug: o.value for o in astro.collect(for_date=date(2026, 5, 1))}
        self.assertEqual(a, b)
        self.assertIn("sunrise-tokyo", a)
        self.assertIn("day-length-tokyo", a)

    def test_days_left_year(self):
        obs = {o.slug: o for o in astro.collect(for_date=date(2026, 12, 31))}
        self.assertEqual(obs["days-left-year"].value, 0)


if __name__ == "__main__":
    unittest.main()
