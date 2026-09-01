# 日本の数字

> 昨日から、日本はどう変わった？

ダム貯水率・気温・電力需要・降水量など、日々変化する日本の公開データを
「今日の値 ＋ 前日比」というシンプルな形で眺めるためのプロジェクト。

- 企画: [docs/日本の数字_企画書.md](docs/日本の数字_企画書.md)
- 候補一覧: [docs/日本の数字_候補100.md](docs/日本の数字_候補100.md)
- 取得検証: [docs/日本の数字_取得検証レポート.md](docs/日本の数字_取得検証レポート.md)
- ロードマップ: [docs/日本の数字_100選ロードマップ.md](docs/日本の数字_100選ロードマップ.md)
- データ仕様: [docs/schema.md](docs/schema.md)

## いま動いているもの（MVP 8種）

| slug | 数字 | 取得元 | 更新 |
|---|---|---|---|
| `max-temp` | 全国最高気温 | 気象庁 ランキングCSV | 毎時 |
| `min-temp` | 全国最低気温 | 気象庁 ランキングCSV | 毎時 |
| `max-precip-24h` | 全国最大24時間降水量 | 気象庁 ランキングCSV | 毎時 |
| `elec-usage-tokyo` | 東京エリアの電力使用率 | 東京電力PG でんき予報 | 毎時 |
| `quakes-24h` | 地震回数（過去24時間） | P2P地震情報 API | 毎時 |
| `sunset-tokyo` | 東京の日の入り時刻 | 自前天文計算 | 日次 |
| `sunrise-tokyo` | 東京の日の出時刻 | 自前天文計算 | 日次 |
| `moon-age` | 月齢 | 自前天文計算 | 日次 |

## 仕組み

```
GitHub Actions (毎時 cron)
   └─ python -m core.run
        ├─ collectors/*.py   … 各ソースから取得・正規化
        ├─ data/history/*.jsonl … 1日1レコードで追記（= 値の履歴。git履歴に残る）
        └─ api/*.json        … 静的API（today / changes / metrics / metrics/{slug}）
   └─ 変化があれば data/ と api/ をコミット＆push
```

外部サービスに依存しない。DBもサーバーも不要。**値が自動で更新され、その履歴がgitに残る**のが v0.1 のゴール。

### 静的API

GitHub Pages で `api/` をそのまま配信（有効化後）:

- `GET /api/today.json` — 今日の全メトリック（値・前日比・一言）
- `GET /api/changes.json` — 前日比を簡易スコア順に
- `GET /api/metrics.json` — メトリック一覧
- `GET /api/metrics/{slug}.json` — 履歴とサマリ

`index.html` は `today.json` を読むだけの最小ビューア（「静かな観測」方向の確認用）。

## ローカル実行

```bash
python3 -m core.run            # 全 collector
python3 -m core.run jma_rank   # 指定 collector のみ
```

依存ライブラリなし（Python 3.11+ 標準ライブラリのみ）。

## ディレクトリ

```
collectors/   各データソースの取得モジュール（1ソース1ファイル）
core/         http取得 / メトリック定義 / 履歴保存 / API生成 / オーケストレータ
data/history/ 値の履歴（jsonl, コミット対象）
api/          生成される静的API（コミット対象）
docs/         企画・調査ドキュメント
ios/          iOSアプリ（未着手。Phase 3）
```

新しい数字を足すときは [docs/日本の数字_100選ロードマップ.md](docs/日本の数字_100選ロードマップ.md) の順序に従う。
