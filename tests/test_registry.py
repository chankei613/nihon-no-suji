import importlib
import unittest

from core import registry
from core.run import COLLECTORS

REQUIRED = {"slug", "name", "category", "unit", "value_type", "comparison_type",
            "daily_agg", "collector", "source", "source_url"}
VALID_COMPARISON = {"absolute", "percentage", "percentage_point"}
VALID_AGG = {"max", "min", "last"}
VALID_VTYPE = {"number", "time", "duration", "moon", "shindo"}


class RegistryTests(unittest.TestCase):

    def test_every_metric_has_required_keys(self):
        for m in registry.METRICS:
            missing = REQUIRED - m.keys()
            self.assertEqual(missing, set(), f"{m.get('slug')} に不足キー: {missing}")

    def test_enum_values_are_valid(self):
        for m in registry.METRICS:
            self.assertIn(m["comparison_type"], VALID_COMPARISON, m["slug"])
            self.assertIn(m["daily_agg"], VALID_AGG, m["slug"])
            self.assertIn(m["value_type"], VALID_VTYPE, m["slug"])

    def test_slugs_are_unique(self):
        slugs = [m["slug"] for m in registry.METRICS]
        self.assertEqual(len(slugs), len(set(slugs)))

    def test_by_slug_matches(self):
        self.assertEqual(len(registry.BY_SLUG), len(registry.METRICS))

    def test_every_collector_module_exists_and_has_collect(self):
        used = {m["collector"] for m in registry.METRICS}
        for name in used:
            self.assertIn(name, COLLECTORS, f"run.py の COLLECTORS に {name} が無い")
            mod = importlib.import_module(f"collectors.{name}")
            self.assertTrue(callable(getattr(mod, "collect", None)))

    def test_time_and_duration_metrics_are_absolute(self):
        for m in registry.METRICS:
            if m["value_type"] in ("time", "duration", "moon"):
                self.assertEqual(m["comparison_type"], "absolute", m["slug"])


if __name__ == "__main__":
    unittest.main()
