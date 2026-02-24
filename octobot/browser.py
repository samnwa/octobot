import os
import glob
import tempfile
from pathlib import Path

_manager = None


_lib_paths_set = False


def _setup_library_paths():
    global _lib_paths_set
    if _lib_paths_set:
        return
    _lib_paths_set = True

    import subprocess
    try:
        chrome_path = None
        for cache_dir in [Path.cwd() / ".cache" / "ms-playwright", Path.home() / ".cache" / "ms-playwright"]:
            if cache_dir.exists():
                shells = list(cache_dir.rglob("chrome-headless-shell"))
                if shells:
                    chrome_path = str(shells[0])
                    break

        if not chrome_path:
            return

        result = subprocess.run(
            ["ldd", chrome_path],
            capture_output=True, text=True, timeout=5
        )
        missing_libs = []
        for line in result.stdout.split("\n"):
            if "not found" in line:
                lib_name = line.strip().split()[0]
                missing_libs.append(lib_name)

        if not missing_libs:
            return

        extra_paths = set()
        nix_lib_dirs = set()
        for p in os.environ.get("PATH", "").split(":"):
            base = p.rstrip("/")
            if base.endswith("/bin"):
                pkg_dir = base[:-4]
                lib_dir = pkg_dir + "/lib"
                if os.path.isdir(lib_dir):
                    nix_lib_dirs.add(lib_dir)
                refs_result = subprocess.run(
                    ["nix-store", "--query", "--references", pkg_dir],
                    capture_output=True, text=True, timeout=3
                )
                if refs_result.returncode == 0:
                    for ref_line in refs_result.stdout.strip().split("\n"):
                        ref_lib = ref_line.strip() + "/lib"
                        if os.path.isdir(ref_lib):
                            nix_lib_dirs.add(ref_lib)

        for lib_name in missing_libs:
            for lib_dir in nix_lib_dirs:
                if os.path.exists(os.path.join(lib_dir, lib_name)):
                    extra_paths.add(lib_dir)

        if extra_paths:
            existing = os.environ.get("LD_LIBRARY_PATH", "")
            new_paths = ":".join(extra_paths)
            os.environ["LD_LIBRARY_PATH"] = f"{new_paths}:{existing}" if existing else new_paths

    except Exception:
        pass


def get_browser_manager():
    global _manager
    if _manager is None:
        _manager = BrowserManager()
    return _manager


def close_browser():
    global _manager
    if _manager is not None:
        _manager.close()
        _manager = None


class BrowserManager:
    def __init__(self):
        self._playwright = None
        self._browser = None
        self._page = None

    def _ensure_browser(self):
        if self._page is not None:
            return
        _setup_library_paths()
        from playwright.sync_api import sync_playwright
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=True)
        self._page = self._browser.new_page()

    def navigate(self, url, timeout=30000):
        self._ensure_browser()
        try:
            self._page.goto(url, timeout=timeout, wait_until="domcontentloaded")
        except Exception as e:
            return {"error": f"Navigation failed: {str(e)}"}
        title = self._page.title()
        text = self._page.inner_text("body")
        if len(text) > 20000:
            text = text[:20000] + "\n... [truncated]"
        return {
            "url": self._page.url,
            "title": title,
            "text": text,
        }

    def screenshot(self):
        self._ensure_browser()
        screenshot_dir = Path(tempfile.gettempdir()) / "octobot_screenshots"
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        existing = list(screenshot_dir.glob("screenshot_*.png"))
        idx = len(existing) + 1
        path = screenshot_dir / f"screenshot_{idx}.png"
        self._page.screenshot(path=str(path), full_page=False)
        return {
            "path": str(path),
            "url": self._page.url,
            "title": self._page.title(),
        }

    def click(self, selector, timeout=5000):
        self._ensure_browser()
        try:
            self._page.click(selector, timeout=timeout)
            return {"status": "ok", "selector": selector}
        except Exception as e:
            return {"error": f"Click failed: {str(e)}"}

    def type_text(self, selector, text, timeout=5000):
        self._ensure_browser()
        try:
            self._page.fill(selector, text, timeout=timeout)
            return {"status": "ok", "selector": selector, "text_length": len(text)}
        except Exception as e:
            return {"error": f"Type failed: {str(e)}"}

    def get_text(self, selector=None):
        self._ensure_browser()
        try:
            if selector:
                text = self._page.inner_text(selector)
            else:
                text = self._page.inner_text("body")
            if len(text) > 30000:
                text = text[:30000] + "\n... [truncated]"
            return {
                "text": text,
                "url": self._page.url,
                "title": self._page.title(),
            }
        except Exception as e:
            return {"error": f"Get text failed: {str(e)}"}

    def close(self):
        if self._page:
            try:
                self._page.close()
            except Exception:
                pass
            self._page = None
        if self._browser:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._playwright:
            try:
                self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
