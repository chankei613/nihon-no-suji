import SwiftUI

/// 読み込み中の控えめな表示（「静かな観測」らしく）
struct LoadingView: View {
    @State private var phase = 0.0

    var body: some View {
        VStack(spacing: 14) {
            Text("日本の数字")
                .font(.system(size: 15, weight: .semibold))
                .tracking(1)
                .foregroundStyle(Theme.sub)
            HStack(spacing: 6) {
                ForEach(0..<3, id: \.self) { i in
                    Circle()
                        .fill(Theme.faint)
                        .frame(width: 5, height: 5)
                        .opacity(phase == Double(i) ? 1 : 0.3)
                }
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Theme.bg)
        .task {
            while !Task.isCancelled {
                try? await Task.sleep(for: .milliseconds(320))
                withAnimation(.easeInOut(duration: 0.3)) { phase = (phase + 1).truncatingRemainder(dividingBy: 3) }
            }
        }
    }
}

#Preview { LoadingView() }
