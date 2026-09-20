import XCTest

/// App Store 用スクリーンショットの撮影。`NihonNoSujiScreenshots` スキームで実行する（CI の通常テストには含めない）。
/// 実データを取りに行くので、ネットワークが必要。
final class StoreScreenshotTests: XCTestCase {

    func testCapture() throws {
        let app = XCUIApplication()
        // わたしタブに星付きの数字を入れておく（UserDefaults の引数ドメイン）
        app.launchArguments = ["-favorite_slugs", "(max-temp, japan-population, days-to-full-moon)"]
        app.launch()

        let tabs = app.tabBars.firstMatch
        XCTAssertTrue(tabs.waitForExistence(timeout: 15))
        sleep(4)   // 実データの読み込み待ち
        attachShot(app, name: "01-today")

        tabs.buttons["変化"].tap()
        sleep(2)
        attachShot(app, name: "02-changes")

        tabs.buttons["数字"].tap()
        sleep(2)
        attachShot(app, name: "03-list")

        let row = app.staticTexts["全国最高気温"].firstMatch
        XCTAssertTrue(row.waitForExistence(timeout: 5))
        row.tap()
        sleep(3)
        attachShot(app, name: "04-detail")

        app.navigationBars.buttons.firstMatch.tap()
        tabs.buttons["わたし"].tap()
        sleep(2)
        attachShot(app, name: "05-favorites")
    }

    private func attachShot(_ app: XCUIApplication, name: String) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}
