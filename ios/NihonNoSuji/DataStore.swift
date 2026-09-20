import Foundation
import Observation

enum Config {
    /// 公開APIのベースURL（GitHub Pages。collect.yml が毎時 api/ を配信する）。
    /// nil にするとバンドルのサンプルだけで動く。
    static let apiBaseURL: URL? = URL(string: "https://chankei613.github.io/nihon-no-suji/api/")
    static let supportURL = URL(string: "https://chankei613.github.io/nihon-no-suji/support.html")!
    static let privacyURL = URL(string: "https://chankei613.github.io/nihon-no-suji/privacy.html")!
}

enum LoadState<T> {
    case loading
    case loaded(T, stale: Bool)   // stale = ネット未取得でサンプル表示中
    case failed(String)
}

@Observable
@MainActor
final class DataStore {
    var today: LoadState<TodayFeed> = .loading
    var changes: LoadState<ChangesFeed> = .loading
    var sparklines: LoadState<SparklineFeed> = .loading

    private let decoder = JSONDecoder()

    func loadAll() async {
        await loadToday()
        await loadChanges()
        await loadSparklines()
    }

    func loadToday() async {
        today = await fetch("today", TodayFeed.self)
    }

    func loadChanges() async {
        changes = await fetch("changes", ChangesFeed.self)
    }

    func loadSparklines() async {
        sparklines = await fetch("sparklines", SparklineFeed.self)
    }

    func metricDetail(_ slug: String) async -> MetricDetail? {
        if let remote: MetricDetail = try? await remote("metrics/\(slug)") { return remote }
        return bundled(slug)
    }

    // MARK: -

    private func fetch<T: Decodable>(_ name: String, _ type: T.Type) async -> LoadState<T> {
        if let value: T = try? await remote(name) {
            return .loaded(value, stale: false)
        }
        if let sample: T = bundled("\(name).sample") {
            return .loaded(sample, stale: Config.apiBaseURL != nil)
        }
        return .failed("データを読み込めませんでした")
    }

    private func remote<T: Decodable>(_ path: String) async throws -> T {
        guard let base = Config.apiBaseURL else { throw URLError(.unsupportedURL) }
        var req = URLRequest(url: base.appendingPathComponent("\(path).json"))
        req.cachePolicy = .reloadRevalidatingCacheData
        req.timeoutInterval = 12
        let (data, _) = try await URLSession.shared.data(for: req)
        return try decoder.decode(T.self, from: data)
    }

    private func bundled<T: Decodable>(_ resource: String) -> T? {
        guard let url = Bundle.main.url(forResource: resource, withExtension: "json"),
              let data = try? Data(contentsOf: url) else { return nil }
        return try? decoder.decode(T.self, from: data)
    }
}
