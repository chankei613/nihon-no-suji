import Foundation
import Observation

/// お気に入りにした数字（slug）。端末内に保存（企画書「わたしの日本」）。
@Observable
@MainActor
final class FavoritesStore {
    private(set) var slugs: [String]

    private let key = "favorite_slugs"

    init() {
        slugs = UserDefaults.standard.stringArray(forKey: key) ?? []
    }

    func isFavorite(_ slug: String) -> Bool {
        slugs.contains(slug)
    }

    func toggle(_ slug: String) {
        if let i = slugs.firstIndex(of: slug) {
            slugs.remove(at: i)
        } else {
            slugs.append(slug)
        }
        persist()
    }

    func remove(atOffsets offsets: IndexSet) {
        slugs.remove(atOffsets: offsets)
        persist()
    }

    func move(fromOffsets source: IndexSet, toOffset destination: Int) {
        slugs.move(fromOffsets: source, toOffset: destination)
        persist()
    }

    private func persist() {
        UserDefaults.standard.set(slugs, forKey: key)
    }

    /// お気に入りを登録順で、渡された metrics から取り出す
    func ordered(from metrics: [Metric]) -> [Metric] {
        let bySlug = Dictionary(uniqueKeysWithValues: metrics.map { ($0.slug, $0) })
        return slugs.compactMap { bySlug[$0] }
    }
}
