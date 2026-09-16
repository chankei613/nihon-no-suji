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


if __name__ == "__main__":
    unittest.main()
