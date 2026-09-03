import SwiftUI

/// 「今日」画面の1枚。大きな数字 ＋ 右に前日比 ＋ 下に一言。
struct MetricCard: View {
    let name: String
    let valueDisplay: String
    let change: Change
    let caption: String
    let asOf: String?
    let stale: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 6) {
                Text(name)
                    .font(.system(size: 13))
                    .foregroundStyle(Theme.sub)
                if stale, let asOf {
                    Text("\(asOf) 時点")
                        .font(.system(size: 11))
                        .foregroundStyle(Theme.sub.opacity(0.7))
                }
            }

            HStack(alignment: .firstTextBaseline, spacing: 12) {
                Text(valueDisplay)
                    .font(.bigNumber)
                    .foregroundStyle(Theme.ink)
                    .monospacedDigit()
                Spacer(minLength: 8)
                if change.available {
                    Text("\(Theme.arrow(change.direction)) \(change.display)")
                        .font(.system(size: 15))
                        .foregroundStyle(Theme.changeColor(change.direction))
                        .monospacedDigit()
                } else {
                    Text("—")
                        .font(.system(size: 15))
                        .foregroundStyle(Theme.hairline)
                }
            }

            if !caption.isEmpty {
                Text(caption)
                    .font(.system(size: 13.5))
                    .foregroundStyle(Theme.ink.opacity(0.65))
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.vertical, 24)
    }
}

extension MetricCard {
    init(metric m: Metric) {
        self.init(name: m.name, valueDisplay: m.valueDisplay, change: m.change,
                  caption: m.caption, asOf: m.asOf, stale: m.stale)
    }
}
