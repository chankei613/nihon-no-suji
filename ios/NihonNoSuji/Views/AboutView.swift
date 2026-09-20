import SwiftUI

/// 「このアプリについて」。出典・免責・サポート/プライバシーへのリンク。
struct AboutView: View {
    @Environment(\.dismiss) private var dismiss

    private var version: String {
        let v = Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? ""
        let b = Bundle.main.object(forInfoDictionaryKey: "CFBundleVersion") as? String ?? ""
        return "\(v) (\(b))"
    }

    static let credits = [
        "気象庁",
        "P2P地震情報 API（元データ：気象庁）",
        "国土交通省 近畿地方整備局・関東地方整備局",
        "東京電力パワーグリッド株式会社",
        "資源エネルギー庁",
        "日本銀行",
        "総務省統計局",
        "厚生労働省",
    ]

    var body: some View {
        NavigationStack {
            List {
                Section {
                    Text("日本の公開データを「今日の値＋前日比」で静かに眺めるアプリです。")
                        .font(.system(size: 14)).foregroundStyle(Theme.ink)
                    LabeledContent("バージョン", value: version)
                }

                Section("出典") {
                    ForEach(Self.credits, id: \.self) { Text($0).font(.system(size: 14)) }
                    Text("公開データを加工して表示しています。天文計算（月の出入りなど）は本アプリ独自の計算で、数分程度の誤差があります。")
                        .font(.system(size: 12)).foregroundStyle(Theme.sub)
                    Text("このサービスは、政府統計総合窓口（e-Stat）のAPI機能を使用していますが、サービスの内容は国によって保証されたものではありません。")
                        .font(.system(size: 12)).foregroundStyle(Theme.sub)
                }

                Section("ご注意") {
                    Text("数字は参考情報です。遅延・欠落・誤りが生じることがあります。警報・地震・台風など防災に関わる判断は、気象庁・自治体などの公式情報をご確認ください。")
                        .font(.system(size: 13)).foregroundStyle(Theme.ink)
                }

                Section {
                    Link("サポート", destination: Config.supportURL)
                    Link("プライバシーポリシー", destination: Config.privacyURL)
                }
            }
            .scrollContentBackground(.hidden)
            .background(Theme.bg)
            .navigationTitle("このアプリについて")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) { Button("閉じる") { dismiss() } }
            }
        }
    }
}

#Preview { AboutView() }
