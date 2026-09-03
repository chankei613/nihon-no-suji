import SwiftUI

struct TodayView: View {
    @Environment(DataStore.self) private var store

    var body: some View {
        NavigationStack {
            Group {
                switch store.today {
                case .loading:
                    ProgressView().frame(maxWidth: .infinity, maxHeight: .infinity)
                case .failed(let msg):
                    ContentUnavailableView("読み込めません", systemImage: "wifi.slash", description: Text(msg))
                case .loaded(let feed, let stale):
                    feedList(feed, stale: stale)
                }
            }
            .background(Theme.bg)
            .navigationTitle("日本の数字")
            .navigationBarTitleDisplayMode(.inline)
        }
    }

    private func feedList(_ feed: TodayFeed, stale: Bool) -> some View {
        ScrollView {
            LazyVStack(spacing: 0) {
                Text(headline(feed.date))
                    .font(.system(size: 13))
                    .foregroundStyle(Theme.sub)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.top, 8)
                    .padding(.bottom, 4)

                ForEach(Array(feed.metrics.enumerated()), id: \.element.id) { index, metric in
                    NavigationLink(value: metric) {
                        MetricCard(metric: metric)
                    }
                    .buttonStyle(.plain)
                    if index < feed.metrics.count - 1 {
                        Divider().overlay(Theme.hairline)
                    }
                }

                if stale {
                    Text("オフライン表示（サンプルデータ）")
                        .font(.system(size: 11))
                        .foregroundStyle(Theme.sub)
                        .padding(.top, 28)
                }
                Text("昨日から、日本はどう変わった？")
                    .font(.system(size: 11))
                    .foregroundStyle(Theme.sub)
                    .padding(.top, stale ? 8 : 40)
                    .padding(.bottom, 24)
            }
            .padding(.horizontal, 22)
        }
        .refreshable { await store.loadToday() }
        .navigationDestination(for: Metric.self) { MetricDetailView(metric: $0) }
    }

    private func headline(_ isoDate: String) -> String {
        let f = DateFormatter()
        f.locale = Locale(identifier: "ja_JP")
        f.dateFormat = "yyyy-MM-dd"
        guard let d = f.date(from: isoDate) else { return "今日の日本" }
        f.dateFormat = "M月d日（E）"
        return "\(f.string(from: d))の日本"
    }
}

#Preview {
    TodayView().environment(DataStore())
}
