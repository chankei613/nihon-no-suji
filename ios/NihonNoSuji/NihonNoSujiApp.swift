import SwiftUI

@main
struct NihonNoSujiApp: App {
    @State private var store = DataStore()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(store)
                .task { await store.loadAll() }
                .tint(Theme.accent)
        }
    }
}
