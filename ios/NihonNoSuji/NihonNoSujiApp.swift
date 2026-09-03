import SwiftUI

@main
struct NihonNoSujiApp: App {
    @State private var store = DataStore()
    @State private var favorites = FavoritesStore()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(store)
                .environment(favorites)
                .task { await store.loadAll() }
                .tint(Theme.accent)
        }
    }
}
