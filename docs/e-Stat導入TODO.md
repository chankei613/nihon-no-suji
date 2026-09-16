# e-Stat 導入 TODO

`collectors/estat.py` は `japan-population`（日本の総人口・推計）を実 appId で検証済み
（2026-09-05・statsDataId=0003443838・値 122,680,000 = 2026年8月概算値）。
ここから先にやること。

## 1. 本番稼働（すぐ）

- [ ] GitHub リポジトリに secret `ESTAT_APP_ID` を登録
      （Settings → Secrets and variables → Actions → New repository secret）
      値はローカルの `.env` の `ESTAT_APP_ID`。ワークフロー側の配線
      （`.github/workflows/collect.yml` の `env: ESTAT_APP_ID`）は済み。
- [ ] 登録後、最初の Actions 実行ログで `✓ japan-population` が出ることを確認
- [ ] 確認できたら `core/run.py` の `EXPECTED_MIN["estat"]` を `0 → 1` に上げる
      （形式変更の早期検知が効くようになる）
- [ ] `api/today.json` で「社会」カテゴリに人口が並ぶこと、`value_display` が
      `122,680,000人` の桁区切り表記になっていることを確認（iOS 側の見た目も）

## 2. 挙動の詰め（人口が数日回ってから）

- [ ] 「更新日だけ動く」挙動の確認。人口推計は月次更新なので、月初に前月比の
      ジャンプが1回出て、あとはフラット。UI の前日比表示がこれで不自然でないか
      （企画書 §4「前回発表比」の考え方に合っているか）を実データで見る
- [ ] 概算値は月ごとにブレる（例: 2026年7月 12293万 → 8月 12268万）。
      必要なら「確定値」系statsDataId への切り替えも検討（ただし公表が遅い）

## 3. メトリック追加（ロードマップ Phase 4 / 100選ロードマップ §Phase 4）

`estat.py` に `_fetch_xxx()` を足して `collect()` に追加、`core/registry.py` に定義。
統計表ごとに分類コード体系が違うので、必ず `getMetaInfo` →
`_total_filters()` で「総数」系を自動選択する既存パターンに乗せる。
statsDataId は e-Stat のサイトで表を特定してから確定させる。

- [ ] 完全失業率（労働力調査）
- [ ] 有効求人倍率（一般職業紹介状況）
- [ ] 消費者物価指数 CPI（前年同月比）
- [ ] 出生数 / 死亡数 / 婚姻件数（人口動態統計・速報）
- [ ] 東京都への転入超過数（住民基本台帳人口移動報告）
- [ ] 訪日外国人数（JNTO 速報 + e-Stat）

各追加時：
1. `python3 -m core.run estat` でローカル確認（`.env` に appId 必須）
2. `git checkout -- data api && git clean -fdq data api` でローカル生成物を捨てる
3. コミットは `collectors/` `core/` `docs/` `tests/` のみ

## メモ

- e-Stat の JSON は要素1件だと dict、複数だと list になる（`_as_list` で吸収済み）
- 単位は「万人」「千人」など表記ゆれ → `_scale()` で吸収
- appId 未設定なら `collect()` は `[]` を返して他 collector に影響しない
- API 仕様: https://www.e-stat.go.jp/api/api-info/e-stat-manual3-0
