"""Optional real-browser integration test. Start app.py before running this file.

Uses Playwright in a development-only environment; no app dependency on it.
Set IR_BROWSER_EXECUTABLE for a system Chromium, and IR_BASE_URL if needed.
"""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get('IR_BASE_URL', 'http://127.0.0.1:5000')


def main():
    errors = []
    with sync_playwright() as playwright:
        options = {'headless': True}
        if os.environ.get('IR_BROWSER_EXECUTABLE'):
            options['executable_path'] = os.environ['IR_BROWSER_EXECUTABLE']
        browser = playwright.chromium.launch(**options)
        context = browser.new_context(viewport={'width': 1440, 'height': 1100}, reduced_motion='reduce')
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(BASE)
        expect(page.locator('.kpi-number')).to_have_text(['10', '27', '64', '4'])
        assert page.evaluate("Chart.getChart('document-chart').data.labels") == [f'd{i}' for i in range(1, 11)]
        page.locator('#help-button').click()
        expect(page.locator('#help-dialog')).to_be_visible()
        page.locator('#close-help').click()
        page.locator('#collapse-sidebar').click()
        assert page.locator('body').evaluate("node => node.classList.contains('sidebar-collapsed')")
        page.locator('#collapse-sidebar').click()
        page.screenshot(path=str(ROOT / 'screenshots/overview.png'), full_page=True)

        page.goto(BASE + '/index')
        expect(page.locator('#selected-term')).to_have_text('machine')
        page.get_by_role('button', name='d5, positions 1, 3, 9', exact=True).click()
        expect(page.locator('#document-preview mark')).to_have_count(3)
        expect(page.locator('#token-strip .hit small')).to_have_text(['1', '3', '9'])
        page.locator('#vocabulary-search').fill('zzzz')
        expect(page.locator('#vocabulary-list')).to_contain_text('No matching terms')
        page.locator('#vocabulary-search').fill('')
        page.screenshot(path=str(ROOT / 'screenshots/positional-index.png'), full_page=True)

        page.goto(BASE + '/analytics')
        expect(page.locator('#matrix-container tbody tr')).to_have_count(27)
        page.get_by_role('button', name='Normalized TF-IDF', exact=True).click()
        page.locator('#matrix-search').fill('machine')
        page.locator('#document-filter').select_option('d5')
        expect(page.locator('#matrix-container tbody td')).to_have_text(['machine', '0.2864'])
        page.locator('#heatmap-mode').click()
        assert '0.286' in page.locator('#matrix-container tbody td').nth(1).get_attribute('title')
        page.locator('#precision').select_option('full')
        assert len(page.locator('#matrix-container tbody td').nth(1).inner_text()) > 6
        page.locator('#density').select_option('compact')
        page.locator('#clear-filters').click()
        expect(page.locator('#matrix-container tbody tr')).to_have_count(27)
        for tab, rows in [('Raw TF', 27), ('Weighted TF', 27), ('DF / IDF', 27), ('TF-IDF', 27), ('Vector lengths', 10), ('Normalized TF-IDF', 27)]:
            page.get_by_role('button', name=tab, exact=True).click()
            expect(page.locator('#matrix-container tbody tr')).to_have_count(rows)
        page.screenshot(path=str(ROOT / 'screenshots/analytics.png'), full_page=True)

        page.goto(BASE + '/search')
        expected = [('machine learning', ['d1.txt', 'd5.txt', 'd10.txt', 'd2.txt', 'd7.txt']),
                    ('data science', ['d5.txt', 'd3.txt', 'd8.txt']),
                    ('machine learning AND data science', ['d5.txt']),
                    ('machine learning AND NOT data science', ['d1.txt', 'd10.txt', 'd2.txt', 'd7.txt'])]
        for query, documents in expected:
            page.get_by_role('button', name=query, exact=True).click()
            expect(page.locator('.result-identity strong')).to_have_text(documents)
            expect(page.locator('#search-button')).to_be_enabled()
        page.locator('.result-card summary').first.click()
        expect(page.locator('.result-card .formula').first).to_contain_text('Σ products')
        page.screenshot(path=str(ROOT / 'screenshots/search-and-not.png'), full_page=True)
        page.get_by_role('button', name='machine learning', exact=True).click()
        expect(page.locator('.result-identity strong')).to_have_text(expected[0][1])
        page.screenshot(path=str(ROOT / 'screenshots/search-phrase.png'), full_page=True)
        page.locator('#phrase-input').fill('unknown')
        page.locator('#phrase-input').press('Enter')
        expect(page.locator('#result-heading')).to_have_text('0 matching documents')
        expect(page.locator('#query-message')).to_contain_text('Not in the collection')
        page.locator('#clear-search').click()
        expect(page.locator('#phrase-input')).to_have_value('')
        page.get_by_role('button', name='machine learning', exact=True).click()
        expect(page.locator('.result-card')).to_have_count(5)

        page.goto(BASE + '/mathematics')
        expect(page.locator('.math-step')).to_have_count(10)
        page.locator('#math-document').select_option('d5')
        assert abs(float(page.locator('.large-value').last.inner_text()) - .3809) < .00005
        page.screenshot(path=str(ROOT / 'screenshots/query-mathematics.png'), full_page=True)

        page.goto(BASE + '/reports')
        expect(page.locator('.export-card')).to_have_count(12)
        expect(page.locator('#exports-count')).to_have_text('12 / 12 FILES READY')
        with page.expect_download() as event:
            page.get_by_role('link', name='Download all results').click()
        download = event.value
        assert download.suggested_filename == 'technology-ir-results.zip'
        assert Path(download.path()).stat().st_size > 1000
        page.screenshot(path=str(ROOT / 'screenshots/exports.png'), full_page=True)

        # Verify that the app loads without external network assets.
        external = []
        page.on('request', lambda req: external.append(req.url) if not req.url.startswith(BASE) else None)
        page.goto(BASE)
        expect(page.locator('.kpi-number')).to_have_count(4)
        assert external == [], external
        page.set_viewport_size({'width': 390, 'height': 844})
        for route in ['/', '/index', '/analytics', '/search', '/mathematics', '/reports']:
            page.goto(BASE + route)
            expect(page.locator('#header-status')).to_have_text('Collection ready')
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), route
            assert not page.locator('#app-error').is_visible(), route
        page.goto(BASE + '/search?preset=0')
        expect(page.locator('.result-card')).to_have_count(5)
        page.screenshot(path=str(ROOT / 'screenshots/mobile-search.png'), full_page=True)
        assert errors == [], errors
        browser.close()
    print('PASS: six pages, four queries, index highlighting, six analytics tabs, filters, heatmap, math selection, ZIP download, local assets, and 390px layout. No browser errors.')


if __name__ == '__main__':
    main()
