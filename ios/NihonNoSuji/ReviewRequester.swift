import StoreKit
import SwiftUI

/// 成功体験（数字をお気に入りに追加）のたびに呼ぶ。回数・間隔の条件を満たしたときだけ評価ダイアログを依頼する。
enum ReviewRequester {
    private static let successCountKey = "reviewRequester.successCount"
    private static let lastRequestKey = "reviewRequester.lastRequestDate"
    private static let minSuccessesBeforeAsk = 3
    private static let minDaysBetweenAsks = 90.0

    @MainActor
    static func recordSuccess(requestReview: RequestReviewAction) {
        let defaults = UserDefaults.standard
        let count = defaults.integer(forKey: successCountKey) + 1
        defaults.set(count, forKey: successCountKey)
        guard count >= minSuccessesBeforeAsk else { return }

        if let last = defaults.object(forKey: lastRequestKey) as? Date,
           Date().timeIntervalSince(last) < minDaysBetweenAsks * 86400 {
            return
        }
        defaults.set(Date(), forKey: lastRequestKey)
        defaults.set(0, forKey: successCountKey)
        requestReview()
    }
}
