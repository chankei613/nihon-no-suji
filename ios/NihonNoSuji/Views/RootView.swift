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
        }
    }
}

#Preview {
    RootView().environment(DataStore())
}
