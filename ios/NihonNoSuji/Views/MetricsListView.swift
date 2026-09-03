import SwiftUI

/// 「数字」タブ。カテゴリ別の一覧。
struct MetricsListView: View {
    @Environment(DataStore.self) private var store

    var body: some View {
        NavigationStack {
            Group {
                switch store.today {
                case .loaded(let feed, _):
                    List {
                        ForEach(categories(feed.metrics), id: \.self) { cat in
                            Section(cat) {
                                ForEach(feed.metrics.filter { $0.category == cat }) { m in
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

    private func categories(_ metrics: [Metric]) -> [String] {
        var seen: [String] = []
        for m in metrics where !seen.contains(m.category) { seen.append(m.category) }
        return seen
    }
}

#Preview {
    MetricsListView().environment(DataStore())
}
