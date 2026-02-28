import json
import os
import sys
import shutil
import tempfile
import zipfile
from urllib.request import urlopen, Request
from urllib.error import URLError

REPO = "samnwa/octobot"
GITHUB_API = f"https://api.github.com/repos/{REPO}/releases/latest"
TIMEOUT = 2
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION_FILE = os.path.join(PROJECT_ROOT, "VERSION")


def _read_local_version():
    try:
        with open(VERSION_FILE, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "0.0.0"


def _parse_version(v):
    v = v.lstrip("v")
    parts = v.split(".")
    result = []
    for p in parts:
        try:
            result.append(int(p))
        except ValueError:
            result.append(0)
    while len(result) < 3:
        result.append(0)
    return tuple(result[:3])


def check_for_update():
    try:
        req = Request(GITHUB_API, headers={"User-Agent": "octobot-updater"})
        with urlopen(req, timeout=TIMEOUT) as resp:
            data = json.loads(resp.read().decode())
    except (URLError, OSError, json.JSONDecodeError, TimeoutError):
        return None

    remote_tag = data.get("tag_name", "")
    if not remote_tag:
        return None

    local_ver = _read_local_version()
    remote_ver = remote_tag.lstrip("v")

    if _parse_version(remote_ver) <= _parse_version(local_ver):
        return None

    body = data.get("body", "")
    first_line = ""
    for line in body.split("\n"):
        line = line.strip()
        if line:
            first_line = line
            break

    zip_url = data.get("zipball_url", "")

    return {
        "local_version": local_ver,
        "remote_version": remote_ver,
        "changelog": first_line,
        "zip_url": zip_url,
        "tag": remote_tag,
    }


def _is_git_repo():
    return os.path.isdir(os.path.join(PROJECT_ROOT, ".git"))


def _git_pull():
    import subprocess
    result = subprocess.run(
        ["git", "pull", "origin", "main"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        result = subprocess.run(
            ["git", "pull"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
    return result.returncode == 0, result.stdout + result.stderr


def _download_with_progress(url, dest_path):
    try:
        from rich.progress import Progress, BarColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn
        req = Request(url, headers={"User-Agent": "octobot-updater"})
        resp = urlopen(req, timeout=30)
        total = int(resp.headers.get("Content-Length", 0))

        with Progress(
            "[cyan]Downloading",
            BarColumn(bar_width=40),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
        ) as progress:
            task = progress.add_task("update", total=total or None)
            with open(dest_path, "wb") as f:
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
                    progress.update(task, advance=len(chunk))
    except ImportError:
        req = Request(url, headers={"User-Agent": "octobot-updater"})
        resp = urlopen(req, timeout=30)
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        with open(dest_path, "wb") as f:
            while True:
                chunk = resp.read(8192)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = int(downloaded / total * 100)
                    bar = "█" * (pct // 3) + "░" * (33 - pct // 3)
                    print(f"\r  [{bar}] {pct}%  {downloaded // 1024}KB", end="", flush=True)
        print()


def _safe_extract(zf, tmp_dir):
    tmp_resolved = os.path.realpath(tmp_dir)
    for member in zf.infolist():
        target = os.path.realpath(os.path.join(tmp_dir, member.filename))
        if not target.startswith(tmp_resolved + os.sep) and target != tmp_resolved:
            raise ValueError(f"Unsafe zip entry: {member.filename}")
        zf.extract(member, tmp_dir)


def _extract_zip_update(zip_path):
    tmp_dir = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            _safe_extract(zf, tmp_dir)

        entries = os.listdir(tmp_dir)
        if len(entries) == 1 and os.path.isdir(os.path.join(tmp_dir, entries[0])):
            source_dir = os.path.join(tmp_dir, entries[0])
        else:
            source_dir = tmp_dir

        skip = {".git", "__pycache__", ".env", "config.json", "node_modules", ".venv", "venv"}
        for item in os.listdir(source_dir):
            if item in skip:
                continue
            src = os.path.join(source_dir, item)
            dst = os.path.join(PROJECT_ROOT, item)
            if os.path.isdir(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
        return True
    except Exception as e:
        print(f"\n  Error extracting update: {e}")
        return False
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def apply_update(update_info):
    import subprocess

    if _is_git_repo():
        print("\n  Pulling latest changes from GitHub...\n")
        success, output = _git_pull()
        if not success:
            print(f"  Git pull failed:\n  {output}")
            print("  Try manually: git pull origin main")
            return False
        print(f"  {output.strip()}")
    else:
        zip_url = update_info.get("zip_url", "")
        if not zip_url:
            print("  No download URL available.")
            return False

        print()
        tmp_zip = tempfile.mktemp(suffix=".zip")
        try:
            _download_with_progress(zip_url, tmp_zip)
            print("  Extracting files...")
            if not _extract_zip_update(tmp_zip):
                return False
        finally:
            if os.path.exists(tmp_zip):
                os.remove(tmp_zip)

    print("  Installing dependencies...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "."],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("  Warning: pip install had issues, but files are updated.")

    print(f"\n  Updated to v{update_info['remote_version']}!")
    return True


def display_update_prompt(update_info):
    local_v = update_info["local_version"]
    remote_v = update_info["remote_version"]
    changelog = update_info.get("changelog", "")

    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text

        console = Console()
        content = Text()
        content.append("  Update available: ", style="bold")
        content.append(f"v{local_v}", style="red")
        content.append(" → ", style="bold")
        content.append(f"v{remote_v}", style="green bold")
        if changelog:
            content.append(f"\n  {changelog}", style="dim")

        console.print()
        console.print(Panel(content, border_style="cyan", padding=(0, 1)))
    except ImportError:
        print()
        print(f"  ┌─────────────────────────────────────────────────┐")
        print(f"  │  Update available: v{local_v} → v{remote_v:<20s}│")
        if changelog:
            cl = changelog[:45]
            print(f"  │  {cl:<48s}│")
        print(f"  └─────────────────────────────────────────────────┘")

    try:
        answer = input("\n  Update now? [Y/n] ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print()
        return False

    return answer in ("", "y", "yes")
