import Foundation

// api/today.json
struct TodayFeed: Codable {
    let generatedAt: String
    let date: String
    let metrics: [Metric]

    enum CodingKeys: String, CodingKey {
        case generatedAt = "generated_at"
        case date, metrics
    }
}

struct Metric: Codable, Identifiable, Hashable {
    let slug: String
    let name: String
    let category: String
    let unit: String
    let valueDisplay: String
    let observedAt: String
    let asOf: String
    let stale: Bool
    let change: Change
    let caption: String
    let source: Source
    let detail: MetricInlineDetail?
    let highlight: Bool
    let highlightReason: String?

    var id: String { slug }

    /// この数字が「今日ならではの意味」を持つか（記録更新など）。カードで強調する。
    var badge: String? {
        if let r = highlightReason { return r }
        if detail?.allTimeRecord == true { return "観測史上1位" }
        if detail?.yearExtreme == true { return "今年いちばん" }
        return nil
    }

    enum CodingKeys: String, CodingKey {
        case slug, name, category, unit, caption, stale, change, source, detail, highlight
        case valueDisplay = "value_display"
        case observedAt = "observed_at"
        case asOf = "as_of"
        case highlightReason = "highlight_reason"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        slug = try c.decode(String.self, forKey: .slug)
        name = try c.decode(String.self, forKey: .name)
        category = try c.decode(String.self, forKey: .category)
        unit = try c.decode(String.self, forKey: .unit)
        valueDisplay = try c.decode(String.self, forKey: .valueDisplay)
        observedAt = try c.decode(String.self, forKey: .observedAt)
        asOf = try c.decode(String.self, forKey: .asOf)
        stale = try c.decode(Bool.self, forKey: .stale)
        change = try c.decode(Change.self, forKey: .change)
        caption = try c.decode(String.self, forKey: .caption)
        source = try c.decode(Source.self, forKey: .source)
        detail = try c.decodeIfPresent(MetricInlineDetail.self, forKey: .detail)
        highlight = try c.decodeIfPresent(Bool.self, forKey: .highlight) ?? false
        highlightReason = try c.decodeIfPresent(String.self, forKey: .highlightReason)
    }
}

/// today.json の detail は数字ごとに形が違う。使うキーだけ拾う。
struct MetricInlineDetail: Codable, Hashable {
    let place: String?
    let pref: String?
    let yearExtreme: Bool?
    let allTimeRecord: Bool?
    let phase: String?

    enum CodingKeys: String, CodingKey {
        case place, pref, phase
        case yearExtreme = "year_extreme"
        case allTimeRecord = "all_time_record"
    }
}

struct Change: Codable, Hashable {
    let type: String
    let available: Bool
    let display: String
    let direction: Direction
    let value: Double?

    enum Direction: String, Codable, Hashable {
        case up, down, flat
        case unknown = ""
    }

    enum CodingKeys: String, CodingKey {
        case type, available, display, direction, value
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        type = try c.decodeIfPresent(String.self, forKey: .type) ?? "absolute"
        available = try c.decodeIfPresent(Bool.self, forKey: .available) ?? false
        display = try c.decodeIfPresent(String.self, forKey: .display) ?? "—"
        direction = (try? c.decode(Direction.self, forKey: .direction)) ?? .flat
        value = try c.decodeIfPresent(Double.self, forKey: .value)
    }
}

struct Source: Codable, Hashable {
    let name: String
    let url: String
}

// api/changes.json
struct ChangesFeed: Codable {
    let generatedAt: String
    let date: String
    let changes: [ChangeRow]

    enum CodingKeys: String, CodingKey {
        case generatedAt = "generated_at"
        case date, changes
    }
}

struct ChangeRow: Codable, Identifiable, Hashable {
    let slug: String
    let name: String
    let category: String
    let valueDisplay: String
    let change: Change
    let caption: String
    let score: Double?
    let label: String

    var id: String { slug }

    enum CodingKeys: String, CodingKey {
        case slug, name, category, change, caption, score, label
        case valueDisplay = "value_display"
    }
}

// api/sparklines.json
struct SparklineFeed: Codable {
    let generatedAt: String
    let series: [SparkSeries]

    enum CodingKeys: String, CodingKey {
        case generatedAt = "generated_at"
        case series
    }
}

struct SparkSeries: Codable, Identifiable {
    let slug: String
    let name: String
    let category: String
    let unit: String
    let valueDisplay: String
    let change: Change
    let points: [MetricDetail.Point]

    var id: String { slug }

    enum CodingKeys: String, CodingKey {
        case slug, name, category, unit, change, points
        case valueDisplay = "value_display"
    }
}

// api/metrics/{slug}.json
struct MetricDetail: Codable {
    let slug: String
    let name: String
    let unit: String
    let updatedAt: String
    let summary: Summary
    let history: [Point]

    enum CodingKeys: String, CodingKey {
        case slug, name, unit, summary, history
        case updatedAt = "updated_at"
    }

    struct Summary: Codable {
        let count: Int
        let min30d: Double?
        let max30d: Double?
        let avg30d: Double?

        enum CodingKeys: String, CodingKey {
            case count
            case min30d = "min_30d"
            case max30d = "max_30d"
            case avg30d = "avg_30d"
        }
    }

    struct Point: Codable, Identifiable {
        let date: String
        let value: Double
        var id: String { date }
    }
}
