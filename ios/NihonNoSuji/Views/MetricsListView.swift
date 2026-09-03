import SwiftUI

/// 「数字」タブ。カテゴリ別の一覧。行の★でお気に入り登録。
struct MetricsListView: View {
    @Environment(DataStore.self) private var store
    @Environment(FavoritesStore.self) private var favorites

    var body: some View {
        NavigationStack {
            Group {
                switch store.today {
                case .loaded(let feed, _):
                    List {
                        ForEach(Theme.sorted(categories(feed.metrics)), id: \.self) { cat in
                            Section(cat) {
                                ForEach(feed.metrics.filter { $0.category == cat }) { m in
                                    row(m)
                                }
                            }
                        }
                    }
                    .listStyle(.plain)
                    .navigationDestination(for: Metric.self) { MetricDetailView(metric: $0) }
                default:
                    ProgressView().frame(maxWidth: .infinity, maxHeight: .infinity)
                }
            }
            .background(Theme.bg)
            .navigationTitle("数字")
            .navigationBarTitleDisplayMode(.inline)
        }
    }

    private func row(_ m: Metric) -> some View {
        HStack(spacing: 10) {
            Button {
                favorites.toggle(m.slug)
            } label: {
                Image(systemName: favorites.isFavorite(m.slug) ? "star.fill" : "star")
                    .font(.system(size: 13))
                    .foregroundStyle(favorites.isFavorite(m.slug) ? Theme.accent : Theme.sub.opacity(0.5))
            }
            .buttonStyle(.plain)

            NavigationLink(value: m) {
                HStack {
                    Text(m.name).font(.system(size: 15))
                    Spacer()
                    Text(m.valueDisplay)
                        .font(.system(size: 15))
                        .foregroundStyle(Theme.sub)
                        .monospacedDigit()
                }
            }
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
