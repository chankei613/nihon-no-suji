"""estat.py のテスト。

⚠️ fixtures/estat_meta_population.json と estat_data_population.json は
   実際のe-Statレスポンスではなく、公開仕様書どおりの構造で作った合成データ。
   appId取得後に実レスポンスで一度必ず確認すること（README/ロードマップに記載）。
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
        # 千人単位 → 人に換算、最新月(2026年08月)の値
        self.assertEqual(obs.value, 123_880_000)
        self.assertEqual(obs.detail["time_code"], "2026080000")

    def test_helpers_normalize_single_dict_to_list(self):
        from collectors import estat
        self.assertEqual(estat._as_list(None), [])
        self.assertEqual(estat._as_list({"a": 1}), [{"a": 1}])
        self.assertEqual(estat._as_list([{"a": 1}, {"b": 2}]), [{"a": 1}, {"b": 2}])

    def test_code_by_name_matches_substring(self):
        from collectors import estat
        meta = {
            "GET_META_INFO": {"METADATA_INF": {"CLASS_OBJ": [
                {"@id": "cat01", "CLASS": [
                    {"@code": "100", "@name": "総数"},
                    {"@code": "200", "@name": "男"},
                ]},
            ]}}
        }
        self.assertEqual(estat._code_by_name(meta, "cat01", ("総数",)), "100")
        self.assertIsNone(estat._code_by_name(meta, "cat01", ("該当なし",)))


if __name__ == "__main__":
    unittest.main()
