import SwiftUI

struct TodayView: View {
    @Environment(DataStore.self) private var store
    @Environment(FavoritesStore.self) private var favorites

    var body: some View {
        NavigationStack {
            Group {
                switch store.today {
                case .loading:
                    ProgressView().frame(maxWidth: .infinity, maxHeight: .infinity)
                case .failed(let msg):
                    ContentUnavailableView("読み込めません", systemImage: "wifi.slash",
                                           description: Text(msg))
                case .loaded(let feed, let stale):
                    feedList(feed, stale: stale)
                }
            }
            .background(Theme.bg)
            .navigationTitle("日本の数字")
            .navigationBarTitleDisplayMode(.inline)
            .navigationDestination(for: Metric.self) { MetricDetailView(metric: $0) }
        }
    }

    private func feedList(_ feed: TodayFeed, stale: Bool) -> some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 0, pinnedViews: [.sectionHeaders]) {
                Text(headline(feed.date))
                    .font(.system(size: 13))
                    .foregroundStyle(Theme.sub)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.top, 6)

                let favs = favorites.ordered(from: feed.metrics)
                if !favs.isEmpty {
                    section(title: "わたしの数字", symbol: "star.fill", metrics: favs)
                }

                ForEach(Theme.sorted(categories(feed.metrics)), id: \.self) { cat in
                    section(title: cat,
                            symbol: Theme.categorySymbol(cat),
                            metrics: feed.metrics.filter { $0.category == cat })
                }

                footer(stale: stale)
            }
            .padding(.horizontal, 22)
        }
        .refreshable { await store.loadToday() }
    }

    @ViewBuilder
    private func section(title: String, symbol: String, metrics: [Metric]) -> some View {
        Section {
            ForEach(metrics) { metric in
                NavigationLink(value: metric) {
                    MetricCard(metric: metric, isFavorite: favorites.isFavorite(metric.slug))
                }
                .buttonStyle(.plain)
                .contextMenu {
                    Button {
                        favorites.toggle(metric.slug)
                    } label: {
                        Label(favorites.isFavorite(metric.slug) ? "わたしの数字から外す" : "わたしの数字に追加",
                              systemImage: favorites.isFavorite(metric.slug) ? "star.slash" : "star")
                    }
                }
                if metric.id != metrics.last?.id {
                    Divider().overlay(Theme.hairline)
                }
            }
        } header: {
            HStack(spacing: 6) {
                Image(systemName: symbol).font(.system(size: 11))
                Text(title).font(.system(size: 12, weight: .semibold))
            }
            .foregroundStyle(Theme.sub)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.top, 26).padding(.bottom, 10)
            .background(Theme.bg)
        }
    }

    private func footer(stale: Bool) -> some View {
        VStack(spacing: 6) {
            if stale {
                Text("オフライン表示（サンプルデータ）")
            }
            Text("長押しで「わたしの数字」に追加")
            Text("昨日から、日本はどう変わった？")
        }
        .font(.system(size: 11))
        .foregroundStyle(Theme.sub)
        .frame(maxWidth: .infinity)
        .padding(.top, 36).padding(.bottom, 24)
    }

    private func categories(_ metrics: [Metric]) -> [String] {
        var seen: [String] = []
        for m in metrics where !seen.contains(m.category) { seen.append(m.category) }
        return seen
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
    TodayView()
        .environment(DataStore())
        .environment(FavoritesStore())
}
