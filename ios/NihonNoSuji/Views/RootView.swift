import SwiftUI

struct RootView: View {
    var body: some View {
        TabView {
            TodayView()
                .tabItem { Label("今日", systemImage: "sun.max") }
            ChangesView()
                .tabItem { Label("変化", systemImage: "arrow.up.arrow.down") }
            MetricsListView()
                .tabItem { Label("数字", systemImage: "number") }
            FavoritesView()
                .tabItem { Label("わたし", systemImage: "star") }
        }
    }
}

#Preview {
    RootView()
        .environment(DataStore())
        .environment(FavoritesStore())
}
