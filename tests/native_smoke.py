"""Native WebView2 integration check against isolated test storage."""
import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import webview
from backend import Api


if __name__ == "__main__":
    temp = tempfile.TemporaryDirectory()
    api = Api(temp.name)
    os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = "--remote-debugging-port=9227"
    webview.settings["REMOTE_DEBUGGING_PORT"] = 9227
    root = Path(__file__).resolve().parents[1]
    window = webview.create_window("Switch Inspector · Integration Test", (root / "ui" / "index.html").as_uri(), js_api=api, width=1480, height=1040)
    api._window = window
    outcome = []

    def evaluate_async(script):
        ready = threading.Event()
        values = []
        def received(value):
            values.append(value)
            ready.set()
        window.evaluate_js(script, callback=received)
        assert ready.wait(8), "Desktop bridge did not return"
        return values[0]

    def check():
        try:
            for _ in range(100):
                if window.evaluate_js("!!(window.app && window.app.initialized && window.pywebview && window.pywebview.api.snapshot)"):
                    break
                time.sleep(.1)
            data = evaluate_async("window.pywebview.api.snapshot()")
            assert data["assets"] == [], data
            assert window.evaluate_js("window.app.demo") is False
            record = dict(name="NATIVE-TEST", host="192.0.2.1", vendor="huawei", port=22,
                          group="测试", username="test-account", password="test-password")
            response = evaluate_async("window.app.call('save_asset'," + json.dumps(record) + ")")
            assert response["ok"], response
            evaluate_async("window.app.refresh()")
            assert window.evaluate_js("document.querySelector('.device-name').textContent") == "NATIVE-TEST"
            assert window.evaluate_js("window.app.data.assets[0].password === undefined")
            window.evaluate_js("window.app.enterDemo()")
            assert window.evaluate_js("document.querySelectorAll('.device-name').length") == 6
            outcome.append("PASS: WebView2 desktop bridge, isolated encrypted asset save, real workspace rendering, demo switch")
            (root / "native-smoke.json").write_text(json.dumps({"ok": True, "checks": outcome}), encoding="utf-8")
            # Keep this isolated demonstration open for a native rendering screenshot.
            if "--capture" in sys.argv:
                from playwright.sync_api import sync_playwright
                with sync_playwright() as playwright:
                    browser = playwright.chromium.connect_over_cdp("http://127.0.0.1:9227")
                    page = next(page for context in browser.contexts for page in context.pages if "index.html" in page.url)
                    page.screenshot(path=str(root / "native-preview.png"))
        except Exception as exc:
            outcome.append("FAIL: " + repr(exc))
            (root / "native-smoke.json").write_text(json.dumps({"ok": False, "checks": outcome}), encoding="utf-8")
        finally:
            window.destroy()

    webview.start(check, gui="edgechromium")
    print("\n".join(outcome))
    temp.cleanup()
    if not outcome or outcome[0].startswith("FAIL"):
        raise SystemExit(1)
