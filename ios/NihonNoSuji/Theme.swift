import SwiftUI

/// UIデザインレビュー「静かな観測」に沿った最小限のトークン。
/// 色は増やさない。前日比だけ1色（accent）で、あとは黒とグレー。
enum Theme {
    static let bg = Color(red: 0.980, green: 0.973, blue: 0.957)      // アイボリー
    static let ink = Color(red: 0.102, green: 0.102, blue: 0.102)     // ほぼ黒
    static let sub = Color(red: 0.541, green: 0.541, blue: 0.525)     // グレー
    static let hairline = Color(red: 0.914, green: 0.898, blue: 0.867)
    static let accent = Color(red: 0.184, green: 0.435, blue: 0.702)  // 前日比の青

    static func changeColor(_ d: Change.Direction) -> Color {
        switch d {
        case .up, .down: return accent
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

    /// カテゴリの並び順（今日画面のセクション順）
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
    static let bigNumber = Font.system(size: 44, weight: .semibold).width(.condensed)
}
