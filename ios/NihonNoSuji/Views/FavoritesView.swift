import SwiftUI

/// 「わたし」タブ ＝ 企画書「わたしの日本」。お気に入りの数字だけを並べる。
struct FavoritesView: View {
    @Environment(DataStore.self) private var store
    @Environment(FavoritesStore.self) private var favorites
    @State private var showAbout = false

    var body: some View {
        NavigationStack {
            Group {
                switch store.today {
                case .loaded(let feed, _):
                    content(favorites.ordered(from: feed.metrics))
                case .failed(let msg):
                    ContentUnavailableView("読み込めません", systemImage: "wifi.slash",
                                           description: Text(msg))
                case .loading:
                    ProgressView().frame(maxWidth: .infinity, maxHeight: .infinity)
                }
            }
            .background(Theme.bg)
            .navigationTitle("わたしの数字")
            .navigationBarTitleDisplayMode(.inline)
            .navigationDestination(for: Metric.self) { MetricDetailView(metric: $0) }
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button { showAbout = true } label: { Image(systemName: "info.circle") }
                        .accessibilityLabel("このアプリについて")
                }
            }
            .sheet(isPresented: $showAbout) { AboutView() }
        }
    }

    @ViewBuilder
    private func content(_ metrics: [Metric]) -> some View {
        if metrics.isEmpty {
            ContentUnavailableView {
                Label("まだ登録がありません", systemImage: "star")
            } description: {
                Text("気になる数字を長押し、または詳細画面の ★ で\nここに追加できます。")
            }
        } else {
            List {
                ForEach(metrics) { metric in
                    ZStack(alignment: .leading) {
                        NavigationLink(value: metric) { EmptyView() }.opacity(0)
                        MetricCard(metric: metric, isFavorite: false)
                    }
                    .listRowInsets(EdgeInsets(top: 0, leading: 22, bottom: 0, trailing: 22))
                    .listRowBackground(Theme.bg)
                    .listRowSeparatorTint(Theme.hairline)
                }
                .onDelete { favorites.remove(atOffsets: $0) }
                .onMove { favorites.move(fromOffsets: $0, toOffset: $1) }
            }
            .listStyle(.plain)
            .toolbar { EditButton() }
        }
    }
}

#Preview {
    FavoritesView()
        .environment(DataStore())
        .environment(FavoritesStore())
}
