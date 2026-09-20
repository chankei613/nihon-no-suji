# 日本の数字 — iOS アプリ（v1.0・App Store 審査提出済み）

SwiftUI。企画書 Phase 3 の「今日 / 変化 / 数字」3画面。
UIは「静かな観測」（`docs/日本の数字_UIデザインレビュー_改善方針.md`）。

## ビルド

```bash
cd ios
xcodegen generate        # project.yml → NihonNoSuji.xcodeproj（.xcodeproj は git管理外）
open NihonNoSuji.xcodeproj
# または
xcodebuild -scheme NihonNoSuji -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' build
xcodebuild -scheme NihonNoSuji -sdk iphonesimulator -destination 'id=<simulator udid>' test
```

必要: Xcode 26 / XcodeGen（`brew install xcodegen`）。

## データの取り込み

- `NihonNoSuji/Resources/*.sample.json` … 本体パイプラインの `api/*.json` のコピー（オフライン初期表示・プレビュー用）
- `DataStore.swift` の `Config.apiBaseURL` … GitHub Pages（`collect.yml` の deploy ジョブが毎時配信）。
  取得できないときはバンドルのサンプルにフォールバックする。
- サンプルの最新化は手動（リリース前に `api/*.json` を `Resources/*.sample.json` へコピーし、テストでデコード確認）。

## リリース

- 署名: 署名なしで archive → `-exportArchive -allowProvisioningUpdates` で署名（`ios-app-factory/tools/appstore` の手順）。
- 掲載文・審査メモ: `store/listing.json`。スクショ: `NihonNoSujiScreenshots` スキームで撮影 → `store/compose_screenshots.py` で合成。
- バージョンを上げるときは `project.yml` の `MARKETING_VERSION` / `CURRENT_PROJECT_VERSION` / `CFBundleVersion`。

## 構成

```
project.yml                  XcodeGen 定義（bundleId: com.cometcat.NihonNoSuji, team: D5R956CRBE）
NihonNoSuji/
  NihonNoSujiApp.swift        エントリ
  Models.swift                today.json / changes.json / metrics/{slug}.json の Codable
  DataStore.swift             @Observable。リモート優先→バンドルにフォールバック
  Theme.swift                 色・フォント（色は増やさない）
  Views/
    RootView.swift            TabView（今日 / 変化 / 数字）
    TodayView.swift           縦スクロール・1カード1数字
    MetricCard.swift          大きい数字＋前日比＋一言
    ChangesView.swift         変化スコア順
    MetricsListView.swift     カテゴリ別一覧
    MetricDetailView.swift    30日グラフ＋サマリ（Swift Charts）
NihonNoSujiTests/             デコードのテスト
```

## まだやっていない

- ウィジェット
- オンボーディング、通知
- クロスプロモ（同じレーンのアプリが無いため保留）
- アイコンは暫定版（`Assets.xcassets/AppIcon`）
