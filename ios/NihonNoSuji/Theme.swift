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
}

extension Font {
    static let bigNumber = Font.system(size: 44, weight: .semibold).width(.condensed)
}
