"""メトリック定義（企画書 §12-13 の metrics 相当）。

comparison_type:
  absolute          … 差をそのまま（℃, mm, 回, 分 …）
  percentage        … 変化率 (%)
  percentage_point  … ポイント差 (pt)

daily_agg … 同じ日に複数回取得したとき、その日の代表値をどう決めるか
  max / min / last

value_type … number / time(分 since 0:00) / moon(0-29.5)
"""
from __future__ import annotations

METRICS: list[dict] = [
    {
        "slug": "max-temp",
        "name": "全国最高気温",
        "category": "自然",
        "unit": "℃",
        "value_type": "number",
        "comparison_type": "absolute",
        "daily_agg": "max",
        "collector": "jma_rank",
        "source": "気象庁「最新の気象データ」",
        "source_url": "https://www.data.jma.go.jp/stats/data/mdrr/tem_rct/alltable/mxtemsadext00_rct.csv",
    },
    {
        "slug": "min-temp",
        "name": "全国最低気温",
        "category": "自然",
        "unit": "℃",
        "value_type": "number",
        "comparison_type": "absolute",
        "daily_agg": "min",
        "collector": "jma_rank",
        "source": "気象庁「最新の気象データ」",
        "source_url": "https://www.data.jma.go.jp/stats/data/mdrr/tem_rct/alltable/mntemsadext00_rct.csv",
    },
    {
        "slug": "max-precip-24h",
        "name": "全国最大24時間降水量",
        "category": "自然",
        "unit": "mm",
        "value_type": "number",
        "comparison_type": "absolute",
        "daily_agg": "max",
        "collector": "jma_rank",
        "source": "気象庁「最新の気象データ」",
        "source_url": "https://www.data.jma.go.jp/stats/data/mdrr/pre_rct/alltable/pre24h00_rct.csv",
    },
    {
        "slug": "biwako-level",
        "name": "琵琶湖の水位",
        "category": "自然",
        "unit": "cm",
        "value_type": "number",
        "comparison_type": "absolute",
        "daily_agg": "last",
        "collector": "mlit_water",
        "source": "国土交通省 近畿地方整備局",
        "source_url": "https://www.kkr.mlit.go.jp/river/json/dam.json",
    },
    {
        "slug": "dam-storage",
        "name": "主要ダムの貯水率",
        "category": "自然",
        "unit": "%",
        "value_type": "number",
        "comparison_type": "percentage_point",
        "daily_agg": "last",
        "collector": "mlit_water",
        "source": "国土交通省 近畿・関東地方整備局",
        "source_url": "https://www.kkr.mlit.go.jp/river/json/dam.json",
    },
    {
        "slug": "elec-usage-tokyo",
        "name": "東京エリアの電力使用率",
        "category": "インフラ",
        "unit": "%",
        "value_type": "number",
        "comparison_type": "percentage_point",
        "daily_agg": "last",
        "collector": "tepco_pg",
        "source": "東京電力パワーグリッド でんき予報",
        "source_url": "https://www.tepco.co.jp/forecast/html/images/juyo-s1-j.csv",
    },
    {
        "slug": "quakes-24h",
        "name": "地震回数（過去24時間・震度1以上）",
        "category": "防災",
        "unit": "回",
        "value_type": "number",
        "comparison_type": "absolute",
        "daily_agg": "last",
        "collector": "p2pquake",
        "source": "P2P地震情報 API（元データ：気象庁）",
        "source_url": "https://api.p2pquake.net/v2/history?codes=551",
    },
    {
        "slug": "sunset-tokyo",
        "name": "東京の日の入り時刻",
        "category": "こよみ",
        "unit": "",
        "value_type": "time",
        "comparison_type": "absolute",
        "daily_agg": "last",
        "collector": "astro",
        "source": "自前天文計算（NOAA式）",
        "source_url": "https://eco.mtk.nao.ac.jp/koyomi/",
    },
    {
        "slug": "sunrise-tokyo",
        "name": "東京の日の出時刻",
        "category": "こよみ",
        "unit": "",
        "value_type": "time",
        "comparison_type": "absolute",
        "daily_agg": "last",
        "collector": "astro",
        "source": "自前天文計算（NOAA式）",
        "source_url": "https://eco.mtk.nao.ac.jp/koyomi/",
    },
    {
        "slug": "moon-age",
        "name": "月齢",
        "category": "こよみ",
        "unit": "",
        "value_type": "moon",
        "comparison_type": "absolute",
        "daily_agg": "last",
        "collector": "astro",
        "source": "自前天文計算",
        "source_url": "https://eco.mtk.nao.ac.jp/koyomi/",
    },
]

BY_SLUG: dict[str, dict] = {m["slug"]: m for m in METRICS}


def metrics_for(collector: str) -> list[dict]:
    return [m for m in METRICS if m["collector"] == collector]
