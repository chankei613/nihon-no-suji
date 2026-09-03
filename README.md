# 日本の数字

> 昨日から、日本はどう変わった？

ダム貯水率・気温・電力需要・降水量など、日々変化する日本の公開データを
「今日の値 ＋ 前日比」というシンプルな形で眺めるためのプロジェクト。

- 企画: [docs/日本の数字_企画書.md](docs/日本の数字_企画書.md)
- 候補一覧: [docs/日本の数字_候補100.md](docs/日本の数字_候補100.md)
- 取得検証: [docs/日本の数字_取得検証レポート.md](docs/日本の数字_取得検証レポート.md)
- ロードマップ: [docs/日本の数字_100選ロードマップ.md](docs/日本の数字_100選ロードマップ.md)
- データ仕様: [docs/schema.md](docs/schema.md)

## いま動いているもの（26メトリック）

一覧は [api/metrics.json](api/metrics.json)、今日の値は [api/today.json](api/today.json)。

**MVP 8種**（企画で承認）
`max-temp` 全国最高気温 / `min-temp` 全国最低気温 / `max-precip-24h` 全国最大24時間降水量 /
`biwako-level` 琵琶湖の水位 / `dam-storage` 主要ダムの貯水率 / `elec-usage-tokyo` 東京エリアの電力使用率 /
`quakes-24h` 地震回数（24時間） / `sunset-tokyo` 東京の日の入り時刻

**Phase 2 で追加**（既存エンドポイントの横展開＋計算のみ）
`hot-points-35` `hot-points-30` `cold-points-0`（しきい値を超えた地点数）/
`national-temp-spread` 全国の気温差 / `max-wind` 全国最大風速 / `min-humidity` 全国の最小湿度 /
`snow-points` `max-snow`（冬のみ）/
`sunrise-tokyo` 日の出 / `day-length-tokyo` 昼の長さ / `days-left-year` 今年の残り日数 /
`moon-age` 月齢 / `days-to-full-moon` 次の満月まで

**Phase 3 で追加**
`tokyo-max-temp` 東京の最高気温 / `fuji-temp` 富士山頂の気温 /
`active-typhoons` 発生中の台風の数 / `typhoons-this-year` 今年の台風発生数 /
`warned-municipalities` 気象警報が出ている市町村数 /
`gas-regular` レギュラーガソリン全国平均（週次）/ `days-to-sekki` 次の二十四節気まで

取得元: 気象庁（ランキングCSV・アメダス実況JSON・台風情報・警報 data/r8）/ 国交省 近畿・関東地整 /
東京電力PG でんき予報 / P2P地震情報API / 資源エネルギー庁（石油製品価格xlsx）/ 自前天文計算。

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
