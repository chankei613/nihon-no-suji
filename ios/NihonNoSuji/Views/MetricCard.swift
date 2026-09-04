import SwiftUI

/// 「今日」画面の1枚。数字が主役。前日比は右で独立。一言は下に控えめに。
struct MetricCard: View {
    let metric: Metric
    var isFavorite: Bool = false

    private var useSmallNumber: Bool { metric.valueDisplay.count >= 8 }

    var body: some View {
        VStack(alignment: .leading, spacing: 7) {
            if let badge = metric.badge {
                Text(badge)
                    .font(.system(size: 10.5, weight: .semibold))
                    .tracking(0.3)
                    .foregroundStyle(Theme.accent)
                    .padding(.horizontal, 7).padding(.vertical, 2)
                    .background(Theme.accent.opacity(0.10), in: Capsule())
                    .padding(.bottom, 1)
            }

            HStack(spacing: 5) {
                Text(metric.name)
                    .font(.system(size: 12.5))
                    .foregroundStyle(Theme.sub)
                if isFavorite {
                    Image(systemName: "star.fill").font(.system(size: 8))
                        .foregroundStyle(Theme.faint)
                }
                Spacer(minLength: 0)
            }

            HStack(alignment: .lastTextBaseline, spacing: 10) {
                valueText
                    .contentTransition(.numericText())
                    .lineLimit(1)
                    .minimumScaleFactor(0.7)
                Spacer(minLength: 6)
                changeLabel
            }

            if !metric.caption.isEmpty {
                HStack(spacing: 5) {
                    Text(metric.caption)
                        .font(.system(size: 13))
                        .foregroundStyle(Theme.ink.opacity(0.58))
                        .fixedSize(horizontal: false, vertical: true)
                    if metric.stale {
                        Text("· \(shortAsOf)")
                            .font(.system(size: 11))
                            .foregroundStyle(Theme.faint)
                    }
                }
                .padding(.top, 1)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.vertical, 20)
        .contentShape(Rectangle())
    }

    /// 数字本体。末尾の単位（℃・市町村 など）は少し小さく。
    private var valueText: Text {
        let big = useSmallNumber ? Font.bigNumberSmall : Font.bigNumber
        let (num, suffix) = Self.splitUnit(metric.valueDisplay)
        var t = Text(num).font(big).foregroundStyle(Theme.ink)
        if !suffix.isEmpty {
            t = t + Text(suffix)
                .font(.system(size: useSmallNumber ? 18 : 21, weight: .medium))
                .foregroundStyle(Theme.ink.opacity(0.75))
        }
        return t.monospacedDigit()
    }

    static func splitUnit(_ display: String) -> (String, String) {
        // 先頭が数字（-, . 含む）で、末尾に単位らしき文字が続くときだけ分割
        guard let m = display.wholeMatch(of: /^([\-\d.,]+)([^\d:].*)$/) else {
            return (display, "")
        }
        return (String(m.1), String(m.2))
    }

    @ViewBuilder private var changeLabel: some View {
        let style = Theme.changeStyle(metric.change, highlight: metric.highlight)
        if metric.change.available {
            Text("\(Theme.arrow(metric.change.direction)) \(metric.change.display)")
                .font(.system(size: 15, weight: style.weight))
                .foregroundStyle(style.color)
                .monospacedDigit()
                .contentTransition(.numericText())
                .layoutPriority(1)
        } else {
            Text("—")
                .font(.system(size: 15))
                .foregroundStyle(Theme.hairline)
        }
    }

    private var shortAsOf: String {
        // "2026-09-03" -> "9/3時点"
        let parts = metric.asOf.split(separator: "-")
        guard parts.count == 3 else { return metric.asOf }
        return "\(Int(parts[1]) ?? 0)/\(Int(parts[2]) ?? 0)時点"
    }
}
