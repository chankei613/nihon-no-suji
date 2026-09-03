import SwiftUI

/// 「今日」画面の1枚。
/// 上：記録バッジ（あれば）／数字の名前　中：大きな数字＋前日比　下：一言
struct MetricCard: View {
    let metric: Metric
    var isFavorite: Bool = false

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            // 記録バッジ（今日ならではの意味）
            if let badge = metric.badge {
                Text(badge)
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundStyle(Theme.accent)
                    .padding(.horizontal, 7).padding(.vertical, 2)
                    .background(Theme.accent.opacity(0.10), in: Capsule())
            }

            HStack(spacing: 5) {
                Text(metric.name)
                    .font(.system(size: 13))
                    .foregroundStyle(Theme.sub)
                if isFavorite {
                    Image(systemName: "star.fill")
                        .font(.system(size: 9))
                        .foregroundStyle(Theme.sub.opacity(0.6))
                }
                if metric.stale {
                    Text("・\(metric.asOf) 時点")
                        .font(.system(size: 11))
                        .foregroundStyle(Theme.sub.opacity(0.7))
                }
            }

            HStack(alignment: .firstTextBaseline, spacing: 12) {
                Text(metric.valueDisplay)
                    .font(.bigNumber)
                    .foregroundStyle(Theme.ink)
                    .monospacedDigit()
                    .lineLimit(1)
                    .minimumScaleFactor(0.6)
                Spacer(minLength: 8)
                changeLabel
            }

            if !metric.caption.isEmpty {
                Text(metric.caption)
                    .font(.system(size: 13.5))
                    .foregroundStyle(Theme.ink.opacity(0.62))
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.vertical, 22)
        .contentShape(Rectangle())
    }

    @ViewBuilder private var changeLabel: some View {
        if metric.change.available {
            VStack(alignment: .trailing, spacing: 1) {
                Text("\(Theme.arrow(metric.change.direction)) \(metric.change.display)")
                    .font(.system(size: 16, weight: .medium))
                    .foregroundStyle(Theme.changeColor(metric.change.direction))
                    .monospacedDigit()
                Text("きのう比")
                    .font(.system(size: 10))
                    .foregroundStyle(Theme.sub.opacity(0.7))
            }
        } else {
            Text("きのうの記録なし")
                .font(.system(size: 11))
                .foregroundStyle(Theme.sub.opacity(0.6))
        }
    }
}
