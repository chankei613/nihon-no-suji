"""estat.py のテスト。

fixtures/estat_meta_population.json と estat_data_population.json は
実レスポンス（statsDataId=0003443838・2026-09-05 に実 appId で確認）の構造に
合わせた縮小版。
"""
import os
import unittest
from unittest import mock

from tests.helpers import patch_fetch


class EstatDormantTests(unittest.TestCase):
    def test_no_appid_returns_empty_without_error(self):
        from collectors import estat
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(estat.collect(), [])

    def test_empty_appid_is_treated_as_unset(self):
        from collectors import estat
        with mock.patch.dict(os.environ, {"ESTAT_APP_ID": "  "}, clear=True):
            self.assertEqual(estat.collect(), [])


class EstatPopulationTests(unittest.TestCase):
    def test_parses_synthetic_response_and_resolves_codes_by_name(self):
        from collectors import estat
        urls = {
            "getMetaInfo": "estat_meta_population.json",
            "getStatsData": "estat_data_population.json",
        }
        with patch_fetch("collectors.estat", urls), \
             mock.patch.dict(os.environ, {"ESTAT_APP_ID": "dummy"}, clear=True):
            out = {o.slug: o for o in estat.collect()}
        self.assertIn("japan-population", out)
        obs = out["japan-population"]
        # 万人単位 → 人に換算、最新月(2026年8月)の値
        self.assertEqual(obs.value, 122_680_000)
        self.assertEqual(obs.detail["time_code"], "2026000808")

    def test_helpers_normalize_single_dict_to_list(self):
        from collectors import estat
        self.assertEqual(estat._as_list(None), [])
        self.assertEqual(estat._as_list({"a": 1}), [{"a": 1}])
        self.assertEqual(estat._as_list([{"a": 1}, {"b": 2}]), [{"a": 1}, {"b": 2}])

    def test_scale_from_unit(self):
        from collectors import estat
        self.assertEqual(estat._scale("万人"), 10_000)
        self.assertEqual(estat._scale("千人"), 1_000)
        self.assertEqual(estat._scale("百万人"), 1_000_000)
        self.assertEqual(estat._scale("人"), 1)

    def test_total_filters_picks_soudou_and_skips_single_axes(self):
        from collectors import estat
        from tests.helpers import fixture_bytes
        import json
        meta = json.loads(fixture_bytes("estat_meta_population.json"))
        filters = estat._total_filters(meta)
        # 男女別→男女計, 年齢5歳階級→総数。単一選択肢の tab/cat01/cat04/area と time は入らない
        self.assertEqual(filters, {"cdCat02": "000", "cdCat03": "01000"})

    def test_total_filters_raises_when_axis_has_no_total_hint(self):
        from collectors import estat
        meta = {
            "GET_META_INFO": {"METADATA_INF": {"CLASS_INF": {"CLASS_OBJ": [
                {"@id": "cat01", "CLASS": [
                    {"@code": "100", "@name": "Aランク"},
                    {"@code": "200", "@name": "Bランク"},
                ]},
            ]}}}
        }
        with self.assertRaises(ValueError):
            estat._total_filters(meta)


class EstatAllMetricsTests(unittest.TestCase):
    """collect() が呼ぶ5つの _fetch_xxx() すべてを、statsDataId ごとに
    別のfixtureへ振り分けて検証する。population以外はgetMetaInfoを
    呼ばず直接getStatsDataを叩く実装なので、patch_fetchの単純なURL部分一致
    （1キー1fixture）では書けない。"""

    def test_collect_returns_all_five_metrics_with_expected_values(self):
        from collectors import estat
        from tests.helpers import fixture_bytes

        routes = {
            "getMetaInfo": "estat_meta_population.json",
            "statsDataId=0003443838": "estat_data_population.json",
            "statsDataId=0003005865": "estat_data_unemployment.json",
            "statsDataId=0004052037": "estat_data_cpi.json",
            "statsDataId=0003446462": "estat_data_job_openings.json",
            "statsDataId=0003423633": "estat_data_tokyo_migration.json",
        }

        def fake_fetch(url, **_kw):
            for needle, fname in routes.items():
                if needle in url:
                    return fixture_bytes(fname)
            raise AssertionError(f"想定外のURL: {url}")

        with mock.patch("collectors.estat.fetch", side_effect=fake_fetch), \
             mock.patch.dict(os.environ, {"ESTAT_APP_ID": "dummy"}, clear=True):
            out = {o.slug: o for o in estat.collect()}

        self.assertEqual(len(out), 5)
        self.assertEqual(out["japan-population"].value, 122_680_000)
        # 最新時点(2026年7月)の値を拾っていること（古い6月の値ではない）
        self.assertEqual(out["unemployment-rate"].value, 2.4)
        self.assertEqual(out["cpi-yoy"].value, 1.9)
        self.assertEqual(out["job-openings-ratio"].value, 1.18)
        self.assertEqual(out["tokyo-net-migration"].value, -801)

    def test_one_metric_failing_does_not_break_the_others(self):
        """有効求人倍率のテーブルだけ壊れていても、他の4件は正しく返る
        （1メトリック1メトリック try/except で囲われていることの保証）。"""
        from collectors import estat
        from tests.helpers import fixture_bytes

        routes = {
            "getMetaInfo": "estat_meta_population.json",
            "statsDataId=0003443838": "estat_data_population.json",
            "statsDataId=0003005865": "estat_data_unemployment.json",
            "statsDataId=0004052037": "estat_data_cpi.json",
            "statsDataId=0003423633": "estat_data_tokyo_migration.json",
        }

        def fake_fetch(url, **_kw):
            if "statsDataId=0003446462" in url:
                raise Exception("network down")
            for needle, fname in routes.items():
                if needle in url:
                    return fixture_bytes(fname)
            raise AssertionError(f"想定外のURL: {url}")

        with mock.patch("collectors.estat.fetch", side_effect=fake_fetch), \
             mock.patch.dict(os.environ, {"ESTAT_APP_ID": "dummy"}, clear=True):
            out = {o.slug: o for o in estat.collect()}

        self.assertNotIn("job-openings-ratio", out)
        self.assertEqual(len(out), 4)
        self.assertIn("japan-population", out)
        self.assertIn("tokyo-net-migration", out)


if __name__ == "__main__":
    unittest.main()
