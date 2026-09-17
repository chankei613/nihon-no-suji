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
        # 真冬日: 5地点中「テスト高地」(-2.0℃)だけが一度も0℃以上にならず → 1
        self.assertIn("ice-day-points", out)
        self.assertEqual(out["ice-day-points"].value, 1)
        # 熱帯夜: 5地点中 東京36.5℃・47909 28.0℃ の2地点だけが一度も25℃を下回らず → 2
        self.assertIn("tropical-night-points", out)
        self.assertEqual(out["tropical-night-points"].value, 2)
        # 東京の日照時間: sun1h=0.5時間 → 30分の積算
        self.assertIn("tokyo-sunshine-hours", out)
        self.assertEqual(out["tokyo-sunshine-hours"].value, 30)

    def test_ice_and_tropical_night_are_mutually_exclusive_with_reported_total(self):
        """真冬日/熱帯夜地点数は「観測地点数 - しきい値を破った地点数」の差分計算。
        後から集計ロジックを変えたときに、この不変条件が壊れていないかを検証する。"""
        from collectors import jma_amedas
        urls = {
            "latest_time.txt": "amedas_latest_time.txt",
            "amedastable.json": "amedas_table.json",
            "/map/": "amedas_map.json",
        }
        with patch_fetch("collectors.jma_amedas", urls):
            out = {o.slug: o for o in jma_amedas.collect()}
        ice = out["ice-day-points"]
        reported = len(ice.detail["reported_station_ids"])
        broke = len(ice.detail["mild_station_ids"])
        self.assertEqual(ice.value, reported - broke)
        tn = out["tropical-night-points"]
        reported_tn = len(tn.detail["reported_station_ids"])
        broke_tn = len(tn.detail["cool_station_ids"])
        self.assertEqual(tn.value, reported_tn - broke_tn)


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

    def test_heavy_rain_flood_sediment_codes_are_split_out(self):
        """コード03(大雨警報)/04(洪水警報)/49(土砂災害警戒情報)を、
        area毎に1つずつ用意したfixtureで、それぞれ正しい市町村数(=1)に
        分類されることを検証する。土砂災害警戒情報(49)は気象警報・注意報の
        集計(warned-municipalities)とは別枠なので、そちらを汚染しないことも確認する。"""
        from collectors import jma_warning
        mt = json.loads(fixture_bytes("warning_map_time.json"))
        latest = datetime.fromisoformat(mt["latestControlDatetime"].replace("Z", "+00:00"))
        fake_now = (latest + timedelta(hours=1)).astimezone(JST_TZ)
        with patch_fetch("collectors.jma_warning",
                         {"map_time.json": "warning_map_time.json",
                          "r8/map.json": "warning_map_extra_codes.json"}), \
             unittest.mock.patch("collectors.jma_warning.now_jst", return_value=fake_now):
            out = {o.slug: o for o in jma_warning.collect()}

        self.assertEqual(out["heavy-rain-warned-municipalities"].value, 1)
        self.assertEqual(out["flood-warned-municipalities"].value, 1)
        self.assertEqual(out["sediment-warning-municipalities"].value, 1)
        # 大雨・洪水は通常の警報集計にも入るが、土砂災害警戒情報は入らない
        # （9010100と9010200の2件のみが気象警報の集計対象 = areaは3件あるうち2件）
        self.assertEqual(out["warned-municipalities"].value, 2)


class JmaForecastTests(unittest.TestCase):
    def test_tomorrow_tokyo(self):
        from collectors import jma_forecast
        with patch_fetch("collectors.jma_forecast",
                         {"forecast/130000.json": "jma_forecast_130000.json"}):
            out = {o.slug: o for o in jma_forecast.collect()}
        self.assertIn("tokyo-forecast-max", out)
        hi = out["tokyo-forecast-max"].value
        lo = out["tokyo-forecast-min"].value
        self.assertGreaterEqual(hi, lo)          # 最高 >= 最低
        self.assertGreater(hi, -20)
        self.assertLess(hi, 45)
        pop = out["tokyo-forecast-pop"].value
        self.assertGreaterEqual(pop, 0)
        self.assertLessEqual(pop, 100)
        self.assertIn("tokyo-week-max-forecast", out)
        wk = out["tokyo-week-max-forecast"]
        self.assertGreater(wk.value, -20)
        self.assertLess(wk.value, 45)
        self.assertIn("for_date", wk.detail)
        # 観測時刻（=履歴の日付キー）は「取得した今日」。予報対象日はdetail["for_date"]側に持つ
        # （ここを対象日にすると、翌日以降のあすの予報が毎回stale判定されるバグがあった）。
        from core.models import now_jst
        today = now_jst().date().isoformat()
        self.assertEqual(out["tokyo-forecast-max"].date, today)
        for_date = out["tokyo-forecast-max"].detail.get("for_date")
        self.assertRegex(for_date, r"^\d{4}-\d{2}-\d{2}$")
        self.assertNotEqual(for_date, today)  # 対象日は「今日」の観測時刻とは別物


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


class VolcanoTests(unittest.TestCase):
    def test_counts_level2_plus_and_skips_unreported(self):
        """3火山のfixture: 桜島=レベル3(採用), 阿蘇山=レベル1(除外),
        999=個別報告が無い(404相当・スキップ)。レベル2以上は桜島のみ → 1。"""
        from collectors import jma_volcano
        from core.http import FetchError

        def fake_fetch(url, **_kw):
            if "volcano_list" in url or "const/volcano_list.json" in url:
                return fixture_bytes("volcano_list.json")
            if "data/warning/506.json" in url:
                return fixture_bytes("volcano_warning_506.json")
            if "data/warning/503.json" in url:
                return fixture_bytes("volcano_warning_503.json")
            if "data/warning/999.json" in url:
                raise FetchError(f"404: {url}")
            raise AssertionError(f"想定外のURL: {url}")

        with unittest.mock.patch("collectors.jma_volcano.fetch", side_effect=fake_fetch):
            out = {o.slug: o for o in jma_volcano.collect()}

        self.assertIn("volcano-alert-points", out)
        v = out["volcano-alert-points"]
        self.assertEqual(v.value, 1)
        self.assertEqual(v.detail["checked"], 2)   # 999は404でチェック対象に入らない
        names = [x["name"] for x in v.detail["volcanoes"]]
        self.assertIn("桜島", names)
        self.assertNotIn("阿蘇山", names)   # レベル1は対象外

    def test_no_data_returns_empty(self):
        from collectors import jma_volcano
        with unittest.mock.patch("collectors.jma_volcano.fetch",
                                 side_effect=Exception("network down")):
            out = jma_volcano.collect()
        self.assertEqual(out, [])


class SakuraTests(unittest.TestCase):
    def test_counts_stations_with_observed_date(self):
        from collectors import jma_sakura
        kaika_html = """
        <table>
        <tr class='mtx'><th colspan='7'>【関東甲信地方】</th></tr>
        <tr class='mtx'><th>地点名</th><th>観測日</th><th>平年差(日)</th><th>平年日</th><th>昨年差(日)</th><th>昨年日</th><th>種類</th></tr>
        <tr class='mtx'><th scope='row'>東京</th><td> 3月19日</td><td>-5</td><td> 3月24日</td><td>-5</td><td> 3月24日</td><td></td></tr>
        <tr class='mtx'><th scope='row'>水戸</th><td> 3月25日</td><td>-5</td><td> 3月30日</td><td>-2</td><td> 3月27日</td><td></td></tr>
        <tr class='mtx'><th scope='row'>未開花地点</th><td></td><td>--</td><td>--</td><td>--</td><td>--</td><td></td></tr>
        </table>
        """
        mankai_html = kaika_html  # 簡易фixture: 満開も同じ構造で1地点少ない想定は別テストで見る

        def fake_fetch(url, **_kw):
            if "sakura_kaika" in url:
                return kaika_html.encode("utf-8")
            if "sakura_mankai" in url:
                return mankai_html.encode("utf-8")
            raise AssertionError(f"想定外のURL: {url}")

        with unittest.mock.patch("collectors.jma_sakura.fetch", side_effect=fake_fetch):
            out = {o.slug: o for o in jma_sakura.collect()}

        self.assertIn("sakura-kaika-points", out)
        # 「地点名」等のヘッダ行・区域見出し行・未開花(空欄)行はカウントしない → 2地点
        self.assertEqual(out["sakura-kaika-points"].value, 2)
        self.assertEqual(out["sakura-mankai-points"].value, 2)

    def test_partial_failure_still_returns_the_other(self):
        from collectors import jma_sakura

        def fake_fetch(url, **_kw):
            if "sakura_kaika" in url:
                raise Exception("network down")
            if "sakura_mankai" in url:
                return "<tr class='mtx'><th scope='row'>東京</th><td> 4月1日</td></tr>".encode("utf-8")
            raise AssertionError(f"想定外のURL: {url}")

        with unittest.mock.patch("collectors.jma_sakura.fetch", side_effect=fake_fetch):
            out = {o.slug: o for o in jma_sakura.collect()}
        self.assertNotIn("sakura-kaika-points", out)
        self.assertIn("sakura-mankai-points", out)
        self.assertEqual(out["sakura-mankai-points"].value, 1)


if __name__ == "__main__":
    unittest.main()
