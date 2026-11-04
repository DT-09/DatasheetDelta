from playwright.sync_api import sync_playwright


def test_full_browser_investigation_review_and_csv_export():
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto("http://127.0.0.1:8000", wait_until="networkidle")

        page.locator("#access-token").fill("ci-review-token")
        page.locator("#reviewer-name").fill("CI Reviewer")
        page.locator('input[name="reference"]').set_input_files({
            "name": "reference.csv",
            "mimeType": "text/csv",
            "buffer": b"Parameter,Value\nPressure,10 bar\n",
        })
        page.locator('input[name="revised"]').set_input_files({
            "name": "revised.csv",
            "mimeType": "text/csv",
            "buffer": b"Parameter,Value\nPressure,12 bar\n",
        })
        page.locator('button[type="submit"]').click()
        page.get_by_role("heading", name="Change register").wait_for()
        assert page.get_by_text("changed", exact=True).count() >= 1

        page.locator('[data-decision="pressure"]').select_option("confirmed_change")
        page.locator('[data-note="pressure"]').fill("Verified by browser acceptance test.")
        page.locator('[data-save-review="pressure"]').click()
        page.get_by_text("confirmed change", exact=True).wait_for()
        assert page.get_by_text("CI Reviewer", exact=False).count() >= 1

        with page.expect_download() as download_info:
            page.locator("#csv").click()
        download = download_info.value
        assert download.suggested_filename == "datasheetdelta.csv"
        assert not errors
        browser.close()
