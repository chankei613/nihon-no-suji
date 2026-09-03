import SwiftUI

/// 「数字」タブ。一覧 ⇄ グラフ を切り替え。行の★でお気に入り。
struct MetricsListView: View {
    @Environment(DataStore.self) private var store
    @Environment(FavoritesStore.self) private var favorites
    @State private var mode: Mode = .list

    enum Mode: String, CaseIterable { case list = "一覧", graph = "グラフ" }

    var body: some View {
        NavigationStack {
            Group {
                if case .loaded(let feed, _) = store.today {
                    VStack(spacing: 0) {
                        Picker("表示", selection: $mode) {
                            ForEach(Mode.allCases, id: \.self) { Text($0.rawValue).tag($0) }
                        }
                        .pickerStyle(.segmented)
                        .padding(.horizontal, 22).padding(.vertical, 10)

                        switch mode {
                        case .list: listView(feed)
                        case .graph: graphView(feed)
                        }
                    }
                    .navigationDestination(for: Metric.self) { MetricDetailView(metric: $0) }
                } else {
                    ProgressView().frame(maxWidth: .infinity, maxHeight: .infinity)
                }
            }
            .background(Theme.bg)
            .navigationTitle("数字")
            .navigationBarTitleDisplayMode(.inline)
        }
    }

    // MARK: 一覧

    private func listView(_ feed: TodayFeed) -> some View {
        List {
            ForEach(Theme.sorted(categories(feed.metrics)), id: \.self) { cat in
                Section(cat) {
                    ForEach(feed.metrics.filter { $0.category == cat }) { m in
                        HStack(spacing: 10) {
                            starButton(m.slug)
                            NavigationLink(value: m) {
                                HStack {
                                    Text(m.name).font(.system(size: 15))
                                    Spacer()
                                    Text(m.valueDisplay).font(.system(size: 15))
                                        .foregroundStyle(Theme.sub).monospacedDigit()
                                }
                            }
                        }
                    }
                }
            }
        }
        .listStyle(.plain)
    }

    // MARK: グラフ

    @ViewBuilder private func graphView(_ feed: TodayFeed) -> some View {
        if case .loaded(let spark, _) = store.sparklines {
            let bySlug = Dictionary(uniqueKeysWithValues: feed.metrics.map { ($0.slug, $0) })
            let ordered = orderedSeries(spark.series, feed.metrics)
            let ready = ordered.filter { $0.points.count >= 4 }
            let soon = ordered.filter { $0.points.count < 4 }
            ScrollView {
                LazyVStack(spacing: 0) {
                    ForEach(ready) { s in
                        if let m = bySlug[s.slug] {
                            NavigationLink(value: m) { graphCard(s) }.buttonStyle(.plain)
                            Divider().overlay(Theme.hairline)
                        }
                    }
                    if !soon.isEmpty {
                        Text("グラフを集計中（あと数日）")
                            .font(.system(size: 12, weight: .semibold))
                            .foregroundStyle(Theme.sub)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(.top, 28).padding(.bottom, 10)
                        ForEach(soon) { s in
                            if let m = bySlug[s.slug] {
                                NavigationLink(value: m) {
                                    HStack {
                                        Text(s.name).font(.system(size: 14)).foregroundStyle(Theme.ink)
                                        Spacer()
                                        Text(s.valueDisplay).font(.system(size: 14))
                                            .foregroundStyle(Theme.sub).monospacedDigit()
                                    }
                                    .padding(.vertical, 12)
                                }
                                .buttonStyle(.plain)
                                Divider().overlay(Theme.hairline)
                            }
                        }
                    }
                }
                .padding(.horizontal, 22)
                .padding(.bottom, 24)
            }
        } else {
            ProgressView().frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }

    private func graphCard(_ s: SparkSeries) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .firstTextBaseline) {
                Text(s.name).font(.system(size: 13)).foregroundStyle(Theme.sub)
                Spacer(minLength: 8)
                Text(s.valueDisplay).font(.system(size: 16, weight: .medium))
                    .foregroundStyle(Theme.ink).monospacedDigit()
                if s.change.available {
                    Text("\(Theme.arrow(s.change.direction)) \(s.change.display)")
                        .font(.system(size: 12))
                        .foregroundStyle(Theme.changeColor(s.change.direction))
                        .monospacedDigit()
                }
                Image(systemName: "chevron.right")
                    .font(.system(size: 11)).foregroundStyle(Theme.sub.opacity(0.5))
            }
            MiniChart(points: s.points, color: Theme.ink, height: 60)
                .frame(maxWidth: .infinity)
        }
        .padding(.vertical, 18)
        .contentShape(Rectangle())
    }

    // MARK: helpers

    private func starButton(_ slug: String) -> some View {
        Button { favorites.toggle(slug) } label: {
            Image(systemName: favorites.isFavorite(slug) ? "star.fill" : "star")
                .font(.system(size: 13))
                .foregroundStyle(favorites.isFavorite(slug) ? Theme.accent : Theme.sub.opacity(0.5))
        }
        .buttonStyle(.plain)
    }

    private func orderedSeries(_ series: [SparkSeries], _ metrics: [Metric]) -> [SparkSeries] {
        let order = Dictionary(uniqueKeysWithValues: metrics.enumerated().map { ($1.slug, $0) })
        let cats = Theme.sorted(categories(metrics))
        let catRank = Dictionary(uniqueKeysWithValues: cats.enumerated().map { ($1, $0) })
        return series.sorted {
            let ca = catRank[$0.category] ?? 99, cb = catRank[$1.category] ?? 99
            if ca != cb { return ca < cb }
            return (order[$0.slug] ?? 0) < (order[$1.slug] ?? 0)
        }
    }

    private func categories(_ metrics: [Metric]) -> [String] {
        var seen: [String] = []
        for m in metrics where !seen.contains(m.category) { seen.append(m.category) }
        return seen
    }
}

#Preview {
    MetricsListView()
        .environment(DataStore())
        .environment(FavoritesStore())
}
