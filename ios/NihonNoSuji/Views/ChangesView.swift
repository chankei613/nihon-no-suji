import SwiftUI

/// 「変化」タブ。今日どの数字が大きく動いたかを、変化スコア順で。
struct ChangesView: View {
    @Environment(DataStore.self) private var store

    var body: some View {
        NavigationStack {
            Group {
                switch store.changes {
                case .loading:
                    ProgressView().frame(maxWidth: .infinity, maxHeight: .infinity)
                case .failed(let msg):
                    ContentUnavailableView("読み込めません", systemImage: "wifi.slash", description: Text(msg))
                case .loaded(let feed, _):
                    list(feed)
                }
            }
            .background(Theme.bg)
            .navigationTitle("変化")
            .navigationBarTitleDisplayMode(.inline)
        }
    }

    private func list(_ feed: ChangesFeed) -> some View {
        ScrollView {
            LazyVStack(spacing: 0) {
                ForEach(Array(feed.changes.enumerated()), id: \.element.id) { i, row in
                    VStack(alignment: .leading, spacing: 8) {
                        HStack {
                            Text(row.name)
                                .font(.system(size: 13))
                                .foregroundStyle(Theme.sub)
                            Spacer()
                            Text(row.label)
                                .font(.system(size: 11))
                                .foregroundStyle(scoreColor(row.score))
                        }
                        HStack(alignment: .firstTextBaseline) {
                            Text(row.valueDisplay)
                                .font(.system(size: 30, weight: .semibold))
                                .foregroundStyle(Theme.ink)
                                .monospacedDigit()
                            Spacer()
                            if row.change.available {
                                Text("\(Theme.arrow(row.change.direction)) \(row.change.display)")
                                    .font(.system(size: 15))
                                    .foregroundStyle(Theme.changeColor(row.change.direction))
                                    .monospacedDigit()
                            }
                        }
                        if !row.caption.isEmpty {
                            Text(row.caption)
                                .font(.system(size: 13))
                                .foregroundStyle(Theme.ink.opacity(0.6))
                        }
                    }
                    .padding(.vertical, 20)
                    if i < feed.changes.count - 1 {
                        Divider().overlay(Theme.hairline)
                    }
                }
            }
            .padding(.horizontal, 22)
            .padding(.top, 4)
        }
        .refreshable { await store.loadChanges() }
    }

    private func scoreColor(_ score: Double?) -> Color {
        guard let s = score else { return Theme.sub }
        return s >= 1.5 ? Theme.accent : Theme.sub
    }
}

#Preview {
    ChangesView().environment(DataStore())
}
