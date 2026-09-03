import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from core import run, store
from core.models import Observation


class HealthTests(unittest.TestCase):
    def setUp(self):
        self._h = tempfile.TemporaryDirectory()
        self._a = tempfile.TemporaryDirectory()
        store.HISTORY_DIR = Path(self._h.name)
        store.API_DIR = Path(self._a.name)

    def tearDown(self):
        self._h.cleanup()
        self._a.cleanup()

    def test_health_json_written_with_degraded_flag(self):
        # astro だけ動かす。1メトリックしか返さないよう細工 → degraded
        fake = mock.Mock()
        fake.collect.return_value = [
            Observation(slug="sunset-tokyo", value=1080,
                        observed_at="2026-09-04T00:00:00+09:00", detail={"time": "18:00"})
        ]
        with mock.patch("importlib.import_module", return_value=fake):
            rc = run.main(["astro"])
        self.assertEqual(rc, 0)  # 一部でも動けば 0

        health = json.loads((Path(self._a.name) / "health.json").read_text())
        astro = next(c for c in health["collectors"] if c["name"] == "astro")
        self.assertEqual(astro["metrics"], 1)
        self.assertEqual(astro["status"], "degraded")   # 目安7に届かない
        self.assertIn("astro", health["degraded"])
        self.assertEqual(health["overall"], "degraded")

    def test_crashed_collector_marked_error_but_run_continues(self):
        def boom():
            raise RuntimeError("boom")
        fake = mock.Mock()
        fake.collect.side_effect = boom
        with mock.patch("importlib.import_module", return_value=fake):
            rc = run.main(["p2pquake"])
        self.assertEqual(rc, 1)  # 対象が全滅なら 1
        health = json.loads((Path(self._a.name) / "health.json").read_text())
        p2p = next(c for c in health["collectors"] if c["name"] == "p2pquake")
        self.assertEqual(p2p["status"], "error")


if __name__ == "__main__":
    unittest.main()
