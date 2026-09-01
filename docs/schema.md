# データ仕様

企画書 §12–13 の `metrics` / `metric_values` / `sources` を、v0.1では
「ファイルだけ」で表現する（DBなし）。

## メトリック定義 — `core/registry.py`

```python
{
  "slug": "max-temp",              # 一意ID。APIパス・ファイル名に使う
  "name": "全国最高気温",
  "category": "自然",               # 自然 / インフラ / 防災 / こよみ / 経済 / 社会 …
  "unit": "℃",
  "value_type": "number",          # number | time(0時からの分) | moon(0-29.5)
  "comparison_type": "absolute",   # absolute | percentage | percentage_point
  "daily_agg": "max",              # 同じ日の複数取得をどう畳むか: max | min | last
  "collector": "jma_rank",         # collectors/jma_rank.py
  "source": "気象庁「最新の気象データ」",
  "source_url": "https://.../mxtemsadext00_rct.csv",
}
```

### comparison_type

| type | 前日比の出し方 | 表示例 |
|---|---|---|
| `absolute` | 今日 − 前日 | `+1.4℃` `-3回` |
| `percentage` | (今日 − 前日) / 前日 × 100 | `+4.2%` |
| `percentage_point` | 今日 − 前日（ポイント） | `+2.0pt` |

`value_type: time` は `absolute` 扱いだが差を「分・早い/遅い」で表示。
`value_type: moon` は周期(29.53)またぎを補正して「+1.0」前後にする。

## 履歴 — `data/history/{slug}.jsonl`

1行 = 1日。JSON Lines。日付昇順。**コミット対象**（値の履歴そのもの）。

```json
{"date":"2026-09-02","value":38.2,"observed_at":"2026-09-02T14:00:00+09:00",
 "fetched_at":"2026-09-02T14:32:10+09:00","runs":6,
 "detail":{"place":"館林","pref":"群馬県","normal_diff":3.1,"record_1st":40.3,
           "year_extreme":true,"caption":"館林｜きょう日本でいちばん暑い"}}
```

- `value` … `daily_agg` で畳んだその日の代表値
- `detail` … 毎回最新の取得で上書き。将来コンテンツ（今年最高・観測史上1位など）の材料も入れる
- `runs` … その日に取得した回数

## 静的API — `api/`

### `api/today.json` … 「今日」画面

```json
{
  "generated_at": "...", "date": "2026-09-02",
  "metrics": [{
    "slug","name","category","unit",
    "value": 38.2, "value_display": "38.2℃",
    "observed_at","as_of","stale": false,
    "change": {"type":"absolute","available":true,"value":1.4,
               "display":"+1.4℃","direction":"up","prev_value":36.8,"prev_date":"2026-09-01"},
    "caption": "館林｜きょう日本でいちばん暑い",
    "detail": { ... },
    "source": {"name","url"}
  }]
}
```

`change.available:false` は前日データがまだ無い状態（初日）。

### `api/changes.json` … 「変化」画面

前日比を簡易スコア（直近30日の前日差の分布に対する z 値）で降順。
履歴5点未満は `score:null, label:"データ蓄積中"`。

### `api/metrics/{slug}.json` … 詳細・グラフ

```json
{"slug","name","unit","comparison_type","value_type","source",
 "updated_at","summary":{"count","min_30d","max_30d","avg_30d","record_1st",...},
 "history":[{"date","value"}, ...],
 "latest_detail":{ ... }}
```

### `api/metrics.json` … 一覧

全メトリックのメタデータ配列。

## 増やすときの原則

ロードマップ（`docs/日本の数字_100選ロードマップ.md`）の順。
外部ソースを増やさず既存エンドポイントから派生できる数字（地点数系など）を優先。
