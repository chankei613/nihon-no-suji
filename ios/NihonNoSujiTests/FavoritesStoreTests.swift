import XCTest
@testable import NihonNoSuji

@MainActor
final class FavoritesStoreTests: XCTestCase {

    override func setUp() {
        UserDefaults.standard.removeObject(forKey: "favorite_slugs")
    }

    func testToggleAddsAndRemoves() {
        let s = FavoritesStore()
        XCTAssertFalse(s.isFavorite("max-temp"))
        s.toggle("max-temp")
        XCTAssertTrue(s.isFavorite("max-temp"))
        s.toggle("max-temp")
        XCTAssertFalse(s.isFavorite("max-temp"))
    }

    func testPersistsAcrossInstances() {
        let a = FavoritesStore()
        a.toggle("biwako-level")
        a.toggle("quakes-24h")
        let b = FavoritesStore()
        XCTAssertEqual(b.slugs, ["biwako-level", "quakes-24h"])
    }

    func testReorderAndDelete() {
        let s = FavoritesStore()
        ["a", "b", "c"].forEach { s.toggle($0) }
        s.move(fromOffsets: IndexSet(integer: 0), toOffset: 3)
        XCTAssertEqual(s.slugs, ["b", "c", "a"])
        s.remove(atOffsets: IndexSet(integer: 1))
        XCTAssertEqual(s.slugs, ["b", "a"])
    }

    func testOrderedFollowsRegistrationOrder() {
        let s = FavoritesStore()
        s.toggle("quakes-24h")
        s.toggle("max-temp")
        let metrics = [
            makeMetric("max-temp"), makeMetric("quakes-24h"), makeMetric("other"),
        ]
        XCTAssertEqual(s.ordered(from: metrics).map(\.slug), ["quakes-24h", "max-temp"])
    }

    private func makeMetric(_ slug: String) -> Metric {
        let json = """
        {"slug":"\(slug)","name":"n","category":"自然","unit":"","value":0,"value_display":"0",
         "observed_at":"x","as_of":"x","stale":false,
         "change":{"type":"absolute","available":false},
         "caption":"","source":{"name":"s","url":"u"}}
        """.data(using: .utf8)!
        return try! JSONDecoder().decode(Metric.self, from: json)
    }
}
