import Charts
import SwiftUI

struct MetricDetailView: View {
    let metric: Metric
    @Environment(DataStore.self) private var store
    @Environment(FavoritesStore.self) private var favorites
    @State private var detail: MetricDetail?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                VStack(alignment: .leading, spacing: 10) {
                    Text(metric.name).font(.system(size: 14)).foregroundStyle(Theme.sub)
                    HStack(alignment: .firstTextBaseline, spacing: 12) {
                        Text(metric.valueDisplay)
                            .font(.system(size: 52, weight: .semibold).width(.condensed))
                            .monospacedDigit()
                        if metric.change.available {
                            Text("\(Theme.arrow(metric.change.direction)) \(metric.change.display)")
                                .font(.system(size: 16))
                                .foregroundStyle(Theme.changeColor(metric.change.direction))
                        }
                    }
                    Text(metric.caption)
                        .font(.system(size: 14))
                        .foregroundStyle(Theme.ink.opacity(0.65))
                }

                if let d = detail, d.history.count >= 2 {
                    chart(d)
                    summary(d)
                } else {
                    Text("履歴を集計中です")
                        .font(.system(size: 13))
                        .foregroundStyle(Theme.sub)
                }

                Link(destination: URL(string: metric.source.url) ?? URL(string: "https://www.jma.go.jp")!) {
                    Text("出典：\(metric.source.name)")
                        .font(.system(size: 12))
                        .foregroundStyle(Theme.sub)
                }
            }
            .padding(22)
        }
        .background(Theme.bg)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    favorites.toggle(metric.slug)
                } label: {
                    Image(systemName: favorites.isFavorite(metric.slug) ? "star.fill" : "star")
                }
                .accessibilityLabel(favorites.isFavorite(metric.slug) ? "わたしの数字から外す" : "わたしの数字に追加")
            }
        }
        .task { detail = await store.metricDetail(metric.slug) }
    }

    private func chart(_ d: MetricDetail) -> some View {
        Chart(d.history.suffix(30)) { p in
            LineMark(x: .value("日", p.date), y: .value(d.unit, p.value))
                .interpolationMethod(.monotone)
                .foregroundStyle(Theme.ink)
        }
        .chartXAxis(.hidden)
        .frame(height: 160)
    }

    private func summary(_ d: MetricDetail) -> some View {
        HStack(spacing: 20) {
            stat("30日 最小", d.summary.min30d)
            stat("30日 平均", d.summary.avg30d)
            stat("30日 最大", d.summary.max30d)
        }
    }

    private func stat(_ label: String, _ value: Double?) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label).font(.system(size: 11)).foregroundStyle(Theme.sub)
            Text(value.map { formatted($0) } ?? "—")
                .font(.system(size: 15, weight: .medium))
                .monospacedDigit()
        }
    }

    private func formatted(_ v: Double) -> String {
        v == v.rounded() ? String(Int(v)) : String(format: "%.1f", v)
    }
}
