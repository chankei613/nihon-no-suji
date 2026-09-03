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

    var id: String { slug }

    enum CodingKeys: String, CodingKey {
        case slug, name, category, unit, caption, stale, change, source
        case valueDisplay = "value_display"
        case observedAt = "observed_at"
        case asOf = "as_of"
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
