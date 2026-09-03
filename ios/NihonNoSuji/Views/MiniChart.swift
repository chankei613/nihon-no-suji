import Charts
import SwiftUI

/// 小さな折れ線（スパークライン）。軸なし。点が少ないときは何も描かない。
struct MiniChart: View {
    let points: [MetricDetail.Point]
    var color: Color = Theme.ink
    var height: CGFloat = 56

    private var minPointsForChart: Int { 4 }

    var body: some View {
        if points.count < minPointsForChart {
            HStack {
                Text("グラフはあと\(max(minPointsForChart - points.count, 1))日ほどで表示されます")
                    .font(.system(size: 11))
                    .foregroundStyle(Theme.sub)
                Spacer()
            }
            .frame(height: height)
        } else {
            Chart {
                ForEach(Array(points.enumerated()), id: \.offset) { i, p in
                    AreaMark(x: .value("i", i), y: .value("v", p.value))
                        .interpolationMethod(.monotone)
                        .foregroundStyle(color.opacity(0.08))
                    LineMark(x: .value("i", i), y: .value("v", p.value))
                        .interpolationMethod(.monotone)
                        .foregroundStyle(color)
                        .lineStyle(.init(lineWidth: 1.5))
                }
                PointMark(x: .value("i", points.count - 1),
                          y: .value("v", points.last!.value))
                    .symbolSize(16)
                    .foregroundStyle(color)
            }
            .chartXAxis(.hidden)
            .chartYAxis(.hidden)
            .chartYScale(domain: yDomain)
            .chartPlotStyle { $0.frame(height: height) }
            .frame(height: height)
            .clipped()
        }
    }

    private var yDomain: ClosedRange<Double> {
        let vs = points.map(\.value)
        let lo = vs.min() ?? 0
        let hi = vs.max() ?? 1
        if hi == lo { return (lo - 1)...(hi + 1) }
        let pad = (hi - lo) * 0.15
        return (lo - pad)...(hi + pad)
    }
}
