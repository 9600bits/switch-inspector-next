"""Switch Inspector desktop entry point."""
import os
import sys
from pathlib import Path


def main():
    import webview
    from backend import Api
    api = Api()
    resources = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    page = resources / "ui" / "index.html"
    url = page.as_uri() + ("?demo=1" if "--demo" in sys.argv else "")
    window = webview.create_window("Switch Inspector · 交换机巡检工作台", url=url, js_api=api,
                                   width=1480, height=940, min_size=(980, 680), background_color="#f6f8fa")
    api._window = window

    def closing():
        if api._run["state"] in ("running", "cancelling"):
            window.evaluate_js("window.app && window.app.closeWarning()")
            return False
    window.events.closing += closing
    webview.settings["ALLOW_DOWNLOADS"] = False
    webview.start(gui="edgechromium", debug="--debug" in sys.argv)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, "应用未能启动。请确认已安装 Microsoft Edge WebView2，并检查当前账户是否能访问本地数据目录。", "Switch Inspector", 16)
        raise
