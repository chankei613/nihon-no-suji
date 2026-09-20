import Charts
import StoreKit
import SwiftUI

struct MetricDetailView: View {
    let metric: Metric
    @Environment(DataStore.self) private var store
    @Environment(FavoritesStore.self) private var favorites
    @Environment(\.requestReview) private var requestReview
    @State private var detail: MetricDetail?

    private var history: [MetricDetail.Point] {
        if let h = detail?.history, h.count >= 2 { return h }
        // 詳細JSONが取れないとき（オフライン等）は sparklines.json の点で代用
        if case .loaded(let spark, _) = store.sparklines,
           let s = spark.series.first(where: { $0.slug == metric.slug }) {
            return s.points
        }
        return detail?.history ?? []
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                header
                if let badge = metric.badge { badgeRow(badge) }
                block { comparisonRow }
                block { observationRow }
                block { historySection }
                sourceFooter
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.horizontal, 22)
            .padding(.top, 8)
            .padding(.bottom, 40)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .background(Theme.bg.ignoresSafeArea())
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    favorites.toggle(metric.slug)
                    if favorites.isFavorite(metric.slug) {
                        ReviewRequester.recordSuccess(requestReview: requestReview)
                    }
                } label: {
                    Image(systemName: favorites.isFavorite(metric.slug) ? "star.fill" : "star")
                }
                .accessibilityLabel(favorites.isFavorite(metric.slug) ? "わたしから外す" : "わたしに追加")
            }
        }
        .task { detail = await store.metricDetail(metric.slug) }
    }

    // MARK: - パーツ

    private var header: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 6) {
                Image(systemName: Theme.categorySymbol(metric.category)).font(.system(size: 11))
                Text(metric.category).font(.system(size: 12, weight: .semibold))
            }
            .foregroundStyle(Theme.sub)

            Text(metric.name).font(.system(size: 15)).foregroundStyle(Theme.ink)

            bigValue
                .monospacedDigit()
                .lineLimit(1)
                .minimumScaleFactor(0.5)

            if !metric.caption.isEmpty {
                Text(metric.caption)
                    .font(.system(size: 15))
                    .foregroundStyle(Theme.ink.opacity(0.7))
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.top, 12)
        .padding(.bottom, 24)
    }

    private var bigValue: Text {
        let (num, suffix) = MetricCard.splitUnit(metric.valueDisplay)
        var t = Text(num).font(.system(size: 58, weight: .medium)).foregroundStyle(Theme.ink)
        if !suffix.isEmpty {
            t = t + Text(suffix).font(.system(size: 26, weight: .medium))
                .foregroundStyle(Theme.ink.opacity(0.75))
        }
        return t
    }

    private func badgeRow(_ badge: String) -> some View {
        Text(badge)
            .font(.system(size: 12, weight: .semibold))
            .foregroundStyle(Theme.accent)
            .padding(.horizontal, 10).padding(.vertical, 5)
            .background(Theme.accent.opacity(0.10), in: Capsule())
            .padding(.bottom, 20)
    }

    private var comparisonRow: some View {
        VStack(alignment: .leading, spacing: 10) {
            sectionTitle("きのうから")
            if metric.change.available {
                HStack(alignment: .firstTextBaseline, spacing: 10) {
                    Text("\(Theme.arrow(metric.change.direction)) \(metric.change.display)")
                        .font(.system(size: 22, weight: .medium))
                        .foregroundStyle(Theme.changeColor(metric.change.direction))
                        .monospacedDigit()
                    if let prevText = prevValueText() {
                        Text(prevText).font(.system(size: 13)).foregroundStyle(Theme.sub)
                    }
                }
            } else {
                Text("きのうの記録がまだありません")
                    .font(.system(size: 14)).foregroundStyle(Theme.sub)
            }
        }
    }

    private var observationLines: [(String, String)] {
        let d = metric.detail
        var lines: [(String, String)] = []
        if let place = d?.place {
            lines.append(("観測地点", [place, d?.pref].compactMap { $0 }.joined(separator: "・")))
        }
        if let phase = d?.phase { lines.append(("月の様子", phase)) }
        lines.append(("観測時刻", timeText(metric.observedAt)))
        return lines
    }

    private var observationRow: some View {
        VStack(alignment: .leading, spacing: 10) {
            sectionTitle("観測")
            ForEach(observationLines, id: \.0) { row in
                HStack {
                    Text(row.0).font(.system(size: 13)).foregroundStyle(Theme.sub)
                    Spacer()
                    Text(row.1).font(.system(size: 14)).foregroundStyle(Theme.ink)
                }
            }
        }
    }

    @ViewBuilder private var historySection: some View {
        VStack(alignment: .leading, spacing: 14) {
            sectionTitle("うつりかわり")
            if history.count >= 5 {
                chart
                summaryStats
            } else if history.count >= 2 {
                recentList
            } else {
                Text("あすから、ここに変化のグラフが出てきます。")
                    .font(.system(size: 13)).foregroundStyle(Theme.sub)
            }
        }
    }

    private var chart: some View {
        Chart(history.suffix(30)) { p in
            AreaMark(x: .value("日", p.date), y: .value(metric.unit, p.value))
                .foregroundStyle(Theme.accent.opacity(0.12))
            LineMark(x: .value("日", p.date), y: .value(metric.unit, p.value))
                .interpolationMethod(.monotone)
                .foregroundStyle(Theme.ink)
        }
        .chartXAxis(.hidden)
        .chartYAxis {
            AxisMarks(position: .leading) { AxisValueLabel().font(.system(size: 10)) }
        }
        .frame(height: 170)
    }

    private var recentList: some View {
        let rows = Array(history.suffix(7).reversed())
        return VStack(spacing: 0) {
            ForEach(Array(rows.enumerated()), id: \.element.id) { i, p in
                HStack {
                    Text(shortDate(p.date)).font(.system(size: 13)).foregroundStyle(Theme.sub)
                    Spacer()
                    Text(formatted(p.value) + metric.unit)
                        .font(.system(size: 14)).foregroundStyle(Theme.ink).monospacedDigit()
                }
                .padding(.vertical, 9)
                if i < rows.count - 1 { Divider().overlay(Theme.hairline) }
            }
        }
    }

    private var summaryStats: some View {
        let recent = history.suffix(30).map(\.value)
        let mn = detail?.summary.min30d ?? recent.min()
        let mx = detail?.summary.max30d ?? recent.max()
        let avg = detail?.summary.avg30d ?? (recent.isEmpty ? nil : recent.reduce(0, +) / Double(recent.count))
        return HStack(spacing: 22) {
            stat("30日 最小", mn)
            stat("30日 平均", avg)
            stat("30日 最大", mx)
        }
        .padding(.top, 4)
    }

    private func stat(_ label: String, _ value: Double?) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(label).font(.system(size: 11)).foregroundStyle(Theme.sub)
            Text(value.map { formatted($0) + metric.unit } ?? "—")
                .font(.system(size: 15, weight: .medium)).monospacedDigit()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var sourceFooter: some View {
        VStack(alignment: .leading, spacing: 0) {
            Divider().overlay(Theme.hairline)
            Link(destination: URL(string: metric.source.url) ?? URL(string: "https://www.jma.go.jp")!) {
                HStack(spacing: 4) {
                    Text("出典：\(metric.source.name)")
                    Image(systemName: "arrow.up.right").font(.system(size: 9))
                }
                .font(.system(size: 12))
                .foregroundStyle(Theme.sub)
            }
            .padding(.top, 16)
        }
    }

    // MARK: - helper

    private func block<Content: View>(@ViewBuilder _ content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            Divider().overlay(Theme.hairline)
            content().padding(.vertical, 22)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func sectionTitle(_ t: String) -> some View {
        Text(t).font(.system(size: 12, weight: .semibold)).foregroundStyle(Theme.sub)
    }

    private func prevValueText() -> String? {
        // 履歴の前日レコードから「きのう X」。時刻系（月齢など）は phase 有無で判定して除外。
        guard metric.detail?.phase == nil, history.count >= 2 else { return nil }
        let prev = history[history.count - 2].value
        return "きのう \(formatted(prev))\(metric.unit)"
    }

    private func formatted(_ v: Double) -> String {
        v == v.rounded() ? String(Int(v)) : String(format: "%.1f", v)
    }

    private func shortDate(_ iso: String) -> String {
        let f = DateFormatter(); f.dateFormat = "yyyy-MM-dd"
        guard let d = f.date(from: iso) else { return iso }
        f.locale = Locale(identifier: "ja_JP"); f.dateFormat = "M/d（E）"
        return f.string(from: d)
    }

    private func timeText(_ iso: String) -> String {
        let f = ISO8601DateFormatter()
        guard let d = f.date(from: iso) else { return iso }
        let out = DateFormatter()
        out.locale = Locale(identifier: "ja_JP")
        out.dateFormat = "M月d日 HH:mm"
        return out.string(from: d)
    }
}
