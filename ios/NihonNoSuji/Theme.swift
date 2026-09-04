import SwiftUI

/// UIデザインレビュー「静かな観測」に沿った最小限のトークン。
/// 色は増やさない。基本は黒とグレー。前日比だけ、動きの大きさに応じて青の濃さを変える。
enum Theme {
    static let bg = Color(red: 0.980, green: 0.973, blue: 0.957)      // アイボリー
    static let ink = Color(red: 0.106, green: 0.102, blue: 0.094)     // ほぼ黒（少し暖色）
    static let sub = Color(red: 0.545, green: 0.533, blue: 0.510)     // グレー
    static let faint = Color(red: 0.72, green: 0.70, blue: 0.66)      // さらに薄いグレー
    static let hairline = Color(red: 0.902, green: 0.884, blue: 0.847)
    static let accent = Color(red: 0.157, green: 0.404, blue: 0.667)  // 前日比の青
    static let accentSoft = Color(red: 0.42, green: 0.52, blue: 0.62) // 小さな動きの青（くすませる）

    struct ChangeStyle {
        var color: Color
        var weight: Font.Weight
    }

    /// 前日比の見た目。ほとんどの日はくすんだ色、大きく動いた数字だけ鮮やかに。
    static func changeStyle(_ change: Change, highlight: Bool) -> ChangeStyle {
        guard change.available else { return .init(color: faint, weight: .regular) }
        if highlight { return .init(color: accent, weight: .semibold) }
        switch change.direction {
        case .up, .down: return .init(color: accentSoft, weight: .medium)
        case .flat, .unknown: return .init(color: sub, weight: .regular)
        }
    }

    /// 方向だけで色を決める簡易版（変化タブ・グラフ一覧など）
    static func changeColor(_ d: Change.Direction) -> Color {
        switch d {
        case .up, .down: return accentSoft
        case .flat, .unknown: return sub
        }
    }

    static func arrow(_ d: Change.Direction) -> String {
        switch d {
        case .up: return "↑"
        case .down: return "↓"
        case .flat: return "→"
        case .unknown: return ""
        }
    }

    // MARK: カテゴリ

    static let categoryOrder = ["防災", "自然", "インフラ", "経済", "こよみ"]

    static func categorySymbol(_ category: String) -> String {
        switch category {
        case "自然": return "leaf"
        case "防災": return "exclamationmark.triangle"
        case "インフラ": return "bolt"
        case "経済": return "yensign"
        case "こよみ": return "moon.stars"
        default: return "number"
        }
    }

    static func sorted(_ categories: [String]) -> [String] {
        categories.sorted { a, b in
            let ia = categoryOrder.firstIndex(of: a) ?? categoryOrder.count
            let ib = categoryOrder.firstIndex(of: b) ?? categoryOrder.count
            return ia == ib ? a < b : ia < ib
        }
    }
}

extension Font {
    /// 数字カード用。ウェイトは控えめ、字幅は標準（詰めない）。
    static let bigNumber = Font.system(size: 42, weight: .medium)
    static let bigNumberSmall = Font.system(size: 34, weight: .medium)
}

/// セクション見出し（ヘアラインの上にラベル）
struct SectionHeader: View {
    let title: String
    var symbol: String?

    var body: some View {
        HStack(spacing: 5) {
            if let symbol {
                Image(systemName: symbol).font(.system(size: 9))
            }
            Text(title)
                .font(.system(size: 10.5, weight: .semibold))
                .tracking(1.2)
            Spacer()
        }
        .foregroundStyle(Theme.faint)
        .padding(.top, 30)
        .padding(.bottom, 6)
        .background(Theme.bg)
    }
}
