"""Offline HTML and archived report bridge checks. Run with python tests/test_report_ui.py."""
import json
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend import Api
from reporting import build_report, render_document
from test_reporting import sample


def main():
    with tempfile.TemporaryDirectory() as folder, sync_playwright() as playwright:
        base = Path(folder)
        row = sample(cpu=0)
        row['name'] = '<img src=x onerror="window.injected=1">'
        row['outputs']['display current-configuration'] = '</script><img src=x onerror="window.injected=1">'
        rows = [row, dict(host='192.0.2.2', name='failed', vendor='', status='fail', error='timeout')]
        run = dict(id='old-run', started='2026-10-24T12:00:00', total=4, state='cancelled', results=rows,
                   count=2, ok=1, warn=0, fail=1)
        report = build_report(run, rows)
        path = base / 'report.html'
        path.write_text(render_document(report, rows, ROOT / 'ui'), encoding='utf-8')
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width':1480, 'height':1040}, offline=True)
        page = context.new_page()
        errors, external = [], []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('request', lambda request: external.append(request.url) if request.url.startswith(('http:', 'https:')) else None)
        page.goto(path.as_uri())
        expect(page.locator('.report-summary tbody tr')).to_have_count(2)
        expect(page.locator('.report-charts>section')).to_have_count(4)
        expect(page.locator('.report-stat.ok strong')).to_have_text('1')
        expect(page.locator('.report-stat.fail strong')).to_have_text('1')
        assert page.locator('img').count() == 0
        page.locator('[data-report-search]').fill('192.0.2.1')
        expect(page.locator('.report-summary tbody tr:visible')).to_have_count(1)
        page.locator('[data-report-jump]').first.click()
        detail = page.locator('.report-device').first
        expect(detail).to_have_attribute('open', '')
        output = detail.locator('.report-raw .report-output').last
        output.locator('summary').click()
        expect(output.locator('pre')).to_contain_text('</script><img')
        assert page.evaluate('window.injected') is None
        page.screenshot(path=str(ROOT / 'offline-report-preview.png'), full_page=True)
        assert not external and not errors, (external, errors)
        # Empty / wholly failed archives still render and filter offline.
        for index, devices in enumerate(([], rows[1:])):
            path2 = base / f'edge-{index}.html'
            path2.write_text(render_document(build_report(dict(id='edge', total=3), devices), devices, ROOT / 'ui'), encoding='utf-8')
            page.goto(path2.as_uri())
            expect(page.locator('.report-summary tbody tr')).to_have_count(len(devices))
            expect(page.locator('.report-charts')).to_contain_text('暂无有效读数')
        print('PASS: offline HTML charts, filters, details, escaping, empty/all-failed archives, no network')
        context.close()

        api = Api(base / 'store')
        api._store.history = [run]
        api._store.save()
        archive = base / 'store' / 'reports' / run['id']
        archive.mkdir(parents=True)
        (archive / 'results.json').write_text(json.dumps(rows), encoding='utf-8')
        # No live assets: all report data and lazy output belong to the archive.
        archived_report, snapshot = api.get_report(run['id']), api.snapshot()
        script = ('window.loads=0;window.pywebview={api:{snapshot:async()=>(SNAPSHOT),'
                  'get_report:async()=>(REPORT),get_result:async()=>{window.loads++;'
                  'if(window.loads===1)throw new Error("模拟读取失败");return ROW;}}};')
        script = script.replace('SNAPSHOT', json.dumps(snapshot)).replace('REPORT', json.dumps(archived_report)).replace('ROW', json.dumps(row))
        page = browser.new_page(viewport={'width':1480,'height':1040})
        page.add_init_script(script)
        page.goto('http://127.0.0.1:8767/#reports')
        page.wait_for_function("typeof app==='object'")
        page.evaluate('app.init()')
        expect(page.locator('.inspection-report')).to_be_visible()
        expect(page.locator('.report-summary tbody tr')).to_have_count(2)
        assert page.evaluate('window.loads') == 0
        page.locator('[data-report-jump]').first.click()
        expect(page.locator('.report-retry')).to_be_visible()
        page.locator('.report-retry').click()
        expect(page.locator('.report-device').first.locator('.report-raw')).to_have_attribute('data-loaded','true')
        assert page.evaluate('window.loads') == 2
        expect(page.locator('.report-device').first.locator('.report-raw')).to_contain_text('</script><img')
        assert page.evaluate('window.injected') is None
        browser.close()
        print('PASS: deleted-asset historical report, lazy raw loading, failed load retry and escaping')


if __name__ == '__main__':
    main()
