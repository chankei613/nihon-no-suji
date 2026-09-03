import XCTest
@testable import NihonNoSuji

final class ModelTests: XCTestCase {

    func testDecodeTodayFeed() throws {
        let json = """
        {
          "generated_at": "2026-09-03T14:00:00+09:00",
          "date": "2026-09-03",
          "metrics": [{
            "slug": "max-temp", "name": "全国最高気温", "category": "自然", "unit": "℃",
            "value": 34.8, "value_display": "34.8℃",
            "observed_at": "2026-09-03T13:00:00+09:00", "as_of": "2026-09-03", "stale": false,
            "change": {"type":"absolute","available":true,"value":-3.1,"display":"-3.1℃","direction":"down"},
            "caption": "前原｜きょう日本でいちばん暑い",
            "source": {"name":"気象庁","url":"https://www.jma.go.jp"}
          }]
        }
        """.data(using: .utf8)!

        let feed = try JSONDecoder().decode(TodayFeed.self, from: json)
        XCTAssertEqual(feed.date, "2026-09-03")
        XCTAssertEqual(feed.metrics.count, 1)
        let m = feed.metrics[0]
        XCTAssertEqual(m.valueDisplay, "34.8℃")
        XCTAssertEqual(m.change.direction, .down)
        XCTAssertEqual(m.change.value, -3.1)
    }

    func testDecodeChangeWithMissingFields() throws {
        let json = #"{"type":"absolute","available":false}"#.data(using: .utf8)!
        let change = try JSONDecoder().decode(Change.self, from: json)
        XCTAssertFalse(change.available)
        XCTAssertEqual(change.direction, .flat)
        XCTAssertEqual(change.display, "—")
    }

    func testDecodeBundledSample() throws {
        let bundle = Bundle(identifier: "com.cometcat.NihonNoSuji")
        guard let url = bundle?.url(forResource: "today.sample", withExtension: "json") else {
            throw XCTSkip("バンドルにサンプルが無い環境ではスキップ")
        }
        let feed = try JSONDecoder().decode(TodayFeed.self, from: Data(contentsOf: url))
        XCTAssertGreaterThan(feed.metrics.count, 10)
    }

    func testArrowMapping() {
        XCTAssertEqual(Theme.arrow(.up), "↑")
        XCTAssertEqual(Theme.arrow(.down), "↓")
        XCTAssertEqual(Theme.arrow(.unknown), "")
    }
}
