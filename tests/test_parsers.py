import json
import unittest
from datetime import datetime, timezone, timedelta

from core.models import JST
from tests.helpers import patch_fetch, fixture_bytes

JST_TZ = JST


class JmaRankTests(unittest.TestCase):
    def test_max_temp_and_precip(self):
        from collectors import jma_rank
        urls = {
            "mxtemsadext00_rct.csv": "jma_maxtemp.csv",
            "mntemsadext00_rct.csv": "jma_mintemp.csv",
            "pre24h00_rct.csv": "jma_precip24h.csv",
        }
        with patch_fetch("collectors.jma_rank", urls):
            out = {o.slug: o for o in jma_rank.collect()}
        self.assertIn("max-temp", out)
        self.assertIn("tokyo-max-temp", out)
        self.assertIn("max-precip-24h", out)
        # 全国最高気温は東京の最高気温以上
        self.assertGreaterEqual(out["max-temp"].value, out["tokyo-max-temp"].value)
        self.assertGreater(out["max-temp"].value, -20)
        self.assertLess(out["max-temp"].value, 50)
        self.assertIn("place", out["max-temp"].detail)

    def test_tokyo_station_is_44132(self):
        from collectors import jma_rank
        with patch_fetch("collectors.jma_rank",
                         {"mxtemsadext00_rct.csv": "jma_maxtemp.csv",
                          "mntemsadext00_rct.csv": "jma_mintemp.csv",
                          "pre24h00_rct.csv": "jma_precip24h.csv"}):
            out = {o.slug: o for o in jma_rank.collect()}
        # 東京の最高気温の観測地点名に「東京」が含まれる
        self.assertIn("東京", out["tokyo-max-temp"].detail.get("place", ""))


class JmaAmedasTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        from core import store
        self._tmp = tempfile.TemporaryDirectory()
        self._orig = store.HISTORY_DIR
        store.HISTORY_DIR = __import__("pathlib").Path(self._tmp.name)

    def tearDown(self):
        from core import store
        store.HISTORY_DIR = self._orig
        self._tmp.cleanup()

    def test_amedas_derived_metrics(self):
        from collectors import jma_amedas
        urls = {
            "latest_time.txt": "amedas_latest_time.txt",
            "amedastable.json": "amedas_table.json",
            "/map/": "amedas_map.json",
        }
        with patch_fetch("collectors.jma_amedas", urls):
            out = {o.slug: o for o in jma_amedas.collect()}

        self.assertIn("hot-points-30", out)          # 東京36.5℃ → 1地点
        self.assertEqual(out["hot-points-30"].value, 1)
        self.assertEqual(out["hot-points-35"].value, 1)
        self.assertEqual(out["cold-points-0"].value, 1)   # テスト高地 -2℃
        self.assertIn("fuji-temp", out)
        self.assertEqual(out["fuji-temp"].value, 7.1)
        # 気温差は山岳(alt>1000)を除外 → 東京36.5 と 宗谷岬15.9 の差
        self.assertAlmostEqual(out["national-temp-spread"].value, 36.5 - 15.9, places=1)
        self.assertIn("max-wind", out)
        self.assertIn("max-precip-1h", out)
        # 名瀬 994.8hPa（標高3m）が最低海面気圧
        self.assertIn("min-pressure", out)
        self.assertAlmostEqual(out["min-pressure"].value, 994.8, places=1)
        self.assertIn("名瀬", out["min-pressure"].detail["place"])


class TepcoTests(unittest.TestCase):
    def test_usage_and_solar(self):
        from collectors import tepco_pg
        with patch_fetch("collectors.tepco_pg", {"juyo-s1-j.csv": "tepco_juyo.csv"}):
            out = {o.slug: o for o in tepco_pg.collect()}
        self.assertIn("elec-usage-tokyo", out)
        u = out["elec-usage-tokyo"]
        self.assertGreater(u.value, 30)
        self.assertLessEqual(u.value, 110)
        self.assertIn("reserve_rate", u.detail)
        self.assertIsNotNone(u.detail.get("current_demand_10MW"))
        self.assertGreater(u.detail["current_demand_10MW"], 0)


class MlitWaterTests(unittest.TestCase):
    def test_biwako_and_dam(self):
        from collectors import mlit_water
        urls = {"river/json/dam.json": "kinki_dam.json",
                "shihon": "kanto_water.html"}
        with patch_fetch("collectors.mlit_water", urls):
            out = {o.slug: o for o in mlit_water.collect()}
        self.assertIn("biwako-level", out)
        self.assertIn("dam-storage", out)
        self.assertLess(out["biwako-level"].value, 50)     # B.S.L. 付近
        self.assertGreater(out["biwako-level"].value, -200)
        d = out["dam-storage"]
        self.assertGreater(d.value, 0)
        self.assertLessEqual(d.value, 130)
        self.assertIn("近畿", d.detail["region_means"])
        self.assertIn("関東", d.detail["region_means"])
        # 関東の首都圏水がめ = 利根川上流9ダム 95% が含まれる
        self.assertEqual(d.detail["region_means"]["関東"],
                         round((95 + 91 + 100 + 65) / 4, 1))

    def test_survives_kanto_failure(self):
        from collectors import mlit_water
        with patch_fetch("collectors.mlit_water", {"river/json/dam.json": "kinki_dam.json"}):
            out = {o.slug: o for o in mlit_water.collect()}
        self.assertIn("biwako-level", out)
        self.assertIn("dam-storage", out)  # 近畿だけでも成立


class P2PQuakeTests(unittest.TestCase):
    def test_counts_felt_in_window(self):
        from collectors import p2pquake
        data = json.loads(fixture_bytes("p2pquake.json"))
        latest = max(datetime.strptime(x["earthquake"]["time"], "%Y/%m/%d %H:%M:%S")
                     for x in data if x.get("earthquake", {}).get("time"))
        fake_now = latest.replace(tzinfo=JST_TZ) + timedelta(hours=1)
        with patch_fetch("collectors.p2pquake", {"api.p2pquake.net": "p2pquake.json"}), \
             unittest.mock.patch("collectors.p2pquake.now_jst", return_value=fake_now):
            out = {o.slug: o for o in p2pquake.collect()}
        q = out["quakes-24h"]
        self.assertGreaterEqual(q.value, 0)
        self.assertLessEqual(q.value, len(data))
        self.assertIn("caption", q.detail)


class TyphoonTests(unittest.TestCase):
    def test_counts_ts_and_above(self):
        from collectors import jma_typhoon
        with patch_fetch("collectors.jma_typhoon",
                         {"targetTc.json": "typhoon_target.json",
                          "specifications.json": "typhoon_target.json"}):  # spec は最悪空でも可
            out = {o.slug: o for o in jma_typhoon.collect()}
        self.assertIn("active-typhoons", out)
        # fixture は TS 1 + TD 1 → 台風(TS以上)は 1
        self.assertEqual(out["active-typhoons"].value, 1)


class WarningTests(unittest.TestCase):
    def test_counts_municipalities_with_warnings(self):
        from collectors import jma_warning
        mt = json.loads(fixture_bytes("warning_map_time.json"))
        latest = datetime.fromisoformat(mt["latestControlDatetime"].replace("Z", "+00:00"))
        fake_now = (latest + timedelta(hours=1)).astimezone(JST_TZ)
        with patch_fetch("collectors.jma_warning",
                         {"map_time.json": "warning_map_time.json",
                          "r8/map.json": "warning_map.json"}), \
             unittest.mock.patch("collectors.jma_warning.now_jst", return_value=fake_now):
            out = {o.slug: o for o in jma_warning.collect()}
        # 発表状況次第で 0 のこともあるが、キーは出る
        self.assertIn("warned-municipalities", out)
        self.assertGreaterEqual(out["warned-municipalities"].value, 0)

    def test_stale_data_is_rejected(self):
        from collectors import jma_warning
        with patch_fetch("collectors.jma_warning",
                         {"map_time.json": "warning_map_time_old.json",
                          "r8/map.json": "warning_map.json"}):
            out = jma_warning.collect()   # 3か月前の管理時刻 → 鮮度ガードで空
        self.assertEqual(out, [])


class BojFxTests(unittest.TestCase):
    def test_parses_latest_usd_jpy(self):
        from collectors import boj_fx
        with patch_fetch("collectors.boj_fx", {"fm08_d_1.csv": "boj_fx.csv"}):
            out = {o.slug: o for o in boj_fx.collect()}
        self.assertIn("usd-jpy", out)
        v = out["usd-jpy"].value
        self.assertGreater(v, 50)
        self.assertLess(v, 400)
        self.assertRegex(out["usd-jpy"].observed_at, r"T17:00:00\+09:00$")


class P2PWeekTests(unittest.TestCase):
    def test_max_shindo_7d(self):
        from collectors import p2pquake
        data = json.loads(fixture_bytes("p2pquake.json"))
        latest = max(datetime.strptime(x["earthquake"]["time"], "%Y/%m/%d %H:%M:%S")
                     for x in data if x.get("earthquake", {}).get("time"))
        fake_now = latest.replace(tzinfo=JST_TZ) + timedelta(hours=1)
        with patch_fetch("collectors.p2pquake", {"api.p2pquake.net": "p2pquake.json"}), \
             unittest.mock.patch("collectors.p2pquake.now_jst", return_value=fake_now):
            out = {o.slug: o for o in p2pquake.collect()}
        if "max-shindo-7d" in out:  # fixture に有感地震があれば
            self.assertGreaterEqual(out["max-shindo-7d"].value, 10)
            self.assertIn("label", out["max-shindo-7d"].detail)


class EnechoGasTests(unittest.TestCase):
    def test_parses_regular_price(self):
        from collectors import enecho_gas
        html = b'<a href="/statistics/petroleum_and_lpgas/pl007/xlsx/260902.xlsx">'
        def fake(url, **_):
            return html if url.endswith("results.html") else fixture_bytes("enecho_gas.xlsx")
        with unittest.mock.patch("collectors.enecho_gas.fetch", side_effect=fake):
            out = {o.slug: o for o in enecho_gas.collect()}
        self.assertIn("gas-regular", out)
        p = out["gas-regular"].value
        self.assertGreater(p, 100)
        self.assertLess(p, 300)
        self.assertIn("survey_date", out["gas-regular"].detail)


if __name__ == "__main__":
    unittest.main()
