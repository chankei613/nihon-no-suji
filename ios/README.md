# 日本の数字 — iOS アプリ（v0.1 スケルトン）

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
- `DataStore.swift` の `Config.apiBaseURL` … **公開API配信先が決まったら URL を入れるだけ**。
  それまでは `nil` でバンドルのサンプルで動作する。
- 配信先が決まったら、サンプルを最新化する仕組み（Actions で ios/Resources へコピー等）も入れる。

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

- 公開API配信先の決定・接続
- お気に入り（企画書「わたしの日本」）
- ウィジェット
- アイコン（`Assets.xcassets/AppIcon` は空）
- レビュー導線・クロスプロモ（`ios-app-factory` の marketing-playbook 準拠で標準搭載する）
