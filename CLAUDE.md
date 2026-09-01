# 日本の数字 — プロジェクト指針

## これは何か

日本の公開データを「今日の値＋前日比」で眺めるアプリ。
コンセプト・UI方針・データ候補・ロードマップは `docs/` にすべてある。**着手前に必ず読む。**

- `docs/日本の数字_企画書.md` … 全体像。判断基準は「その数字、明日も見たい？」
- `docs/日本の数字_UIデザインレビュー_改善方針.md` … 「静かな観測」。統計ダッシュボードにしない
- `docs/日本の数字_候補100.md` … 数字の候補とデータソース一覧
- `docs/日本の数字_取得検証レポート.md` … 検証済みエンドポイント
- `docs/日本の数字_100選ロードマップ.md` … MVP8 → 100 の増やし方
- `docs/schema.md` … メトリック定義・履歴・APIの形

## 最重要方針

- **値が自動更新され続けること**が最優先。凝ったUIより先にデータを回す
- 外部サービス（DB・SaaS）を足さない。GitHub Actions ＋ 静的ファイルで完結させる
- 気象庁の非公式JSONや官庁HTMLは落ちる前提。取得は必ず UA固定・タイムアウト・リトライ・前回値フォールバック
- 依頼されていない数字・機能を勝手に足さない。増やすときはロードマップの順序

## データを1つ足す手順

1. `core/registry.py` の `METRICS` に定義を追加（slug / comparison_type / daily_agg / source）
2. `collectors/<name>.py` に `collect() -> list[Observation]` を実装（既存collectorに相乗り可）
3. `core/run.py` の `COLLECTORS` に collector 名を追加
4. `python3 -m core.run <name>` でローカル確認 → `api/today.json` を見る

## iOSアプリ（ios/ 配下・Phase 3以降）

- SwiftUI。API は GitHub Pages の `api/today.json` などを叩くだけ（バックエンド書かない）
- **アプリの設定・リリース周りで迷ったら `/Users/ajisai_haraguchi/Documents/GitHub/ios-app-factory` を参照する**
  （StoreKit2直叩き / App Store Connect API / fastlane / 課金モデルの決定木 / チェックリスト等の実績がある）
- シークレットはコミットしない。追加したら `.env.example` にも空項目を足す

## コミット

- `data/` と `api/` の自動更新コミットは bot（`nihon-no-suji-bot`）が行う。手で触らない
- コード変更のコミットメッセージは日本語で簡潔に
