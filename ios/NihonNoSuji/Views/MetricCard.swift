import SwiftUI

/// 「今日」画面の1枚。数字が主役 = いちばん上・いちばん大きい。
/// 名前は数字の下に小さく。一言は意味があるときだけ添える。
struct MetricCard: View {
    let metric: Metric
    var isFavorite: Bool = false

    private var useSmall: Bool { MetricCard.splitUnit(metric.valueDisplay).0.count >= 7 }

    var body: some View {
        VStack(alignment: .leading, spacing: 9) {
            if let badge = metric.badge {
                Text(badge)
                    .font(.system(size: 10.5, weight: .semibold))
                    .tracking(0.3)
                    .foregroundStyle(Theme.accent)
                    .padding(.horizontal, 7).padding(.vertical, 2)
                    .background(Theme.accent.opacity(0.10), in: Capsule())
            }

            // 数字（主役）＋ 前日比
            HStack(alignment: .firstTextBaseline, spacing: 12) {
                valueText
                    .contentTransition(.numericText())
                    .lineLimit(1)
                    .minimumScaleFactor(0.6)
                Spacer(minLength: 4)
                changeLabel
            }

            // 名前 ＋ 一言（従属情報）
            HStack(alignment: .firstTextBaseline, spacing: 0) {
                Text(metric.name)
                    .font(.system(size: 12.5))
                    .foregroundStyle(Theme.sub)
                if let note = meaningfulCaption {
                    Text("　" + note)
                        .font(.system(size: 12.5))
                        .foregroundStyle(Theme.faint)
                        .lineLimit(1)
                }
                if metric.stale {
                    Text("　\(shortAsOf)")
                        .font(.system(size: 11))
                        .foregroundStyle(Theme.faint)
                }
                Spacer(minLength: 0)
                if isFavorite {
                    Image(systemName: "star.fill").font(.system(size: 8))
                        .foregroundStyle(Theme.faint)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.vertical, 22)
        .contentShape(Rectangle())
    }

    /// 数字本体。末尾の単位は数字より小さく。
    private var valueText: Text {
        let big = Font.system(size: useSmall ? 40 : 52, weight: .medium)
        let unitSize: CGFloat = useSmall ? 19 : 24
        let (num, suffix) = MetricCard.splitUnit(metric.valueDisplay)
        var t = Text(num).font(big).foregroundStyle(Theme.ink)
        if !suffix.isEmpty {
            t = t + Text(suffix)
                .font(.system(size: unitSize, weight: .medium))
                .foregroundStyle(Theme.ink.opacity(0.7))
        }
        return t.monospacedDigit()
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
                .fixedSize()
        } else {
            Text("—")
                .font(.system(size: 15))
                .foregroundStyle(Theme.hairline)
        }
    }

    /// 数字を言い換えただけの一言は出さない（例「21市町村に気象警報」）。
    private var meaningfulCaption: String? {
        let c = metric.caption
        guard !c.isEmpty else { return nil }
        if c.wholeMatch(of: /^[\d,]+(市町村|地点|個|回|mm|cm|℃|%|人).*/) != nil { return nil }
        return c
    }

    static func splitUnit(_ display: String) -> (String, String) {
        guard let m = display.wholeMatch(of: /^([\-\d.,]+)([^\d:].*)$/) else {
            return (display, "")
        }
        return (String(m.1), String(m.2))
    }

    private var shortAsOf: String {
        let p = metric.asOf.split(separator: "-")
        guard p.count == 3 else { return metric.asOf }
        return "\(Int(p[1]) ?? 0)/\(Int(p[2]) ?? 0)時点"
    }
}
