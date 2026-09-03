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
