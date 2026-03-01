"""
SynthChat Desktop Launcher

Double-click this file (or run `python desktop.py`) to start SynthChat
as a standalone desktop application with its own window.

Requirements:
    pip install pywebview

The launcher:
  1. Starts the SynthChat server in the background
  2. Opens a native desktop window
  3. Stops the server when you close the window
"""

import sys
import subprocess
import threading
import time
import socket


def _find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _wait_for_server(port, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def _check_pywebview():
    try:
        import webview  # noqa: F401
        return True
    except ImportError:
        return False


def _install_pywebview():
    print("\n  pywebview is required for the desktop app.")
    print("  This is a lightweight library that creates a native window.\n")
    try:
        answer = input("  Install it now? (pip install pywebview) [Y/n] ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print()
        return False

    if answer in ("", "y", "yes"):
        print("\n  Installing pywebview...\n")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "pywebview"],
            capture_output=False,
        )
        if result.returncode != 0:
            print("\n  Installation failed. Try: pip install pywebview")
            return False
        print("\n  Installed successfully!\n")
        return True
    return False


def main():
    if not _check_pywebview():
        if not _install_pywebview():
            sys.exit(1)

    import webview

    port = _find_free_port()
    server_process = None

    def start_server():
        nonlocal server_process
        server_process = subprocess.Popen(
            [sys.executable, "-c",
             f"from synthchat.app import create_standalone_app; "
             f"app = create_standalone_app(); "
             f"app.run(host='127.0.0.1', port={port}, debug=False, use_reloader=False)"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    print(f"\n  Starting SynthChat on port {port}...")

    if not _wait_for_server(port):
        print("  Server failed to start. Try: python main-chat.py")
        if server_process:
            server_process.terminate()
        sys.exit(1)

    print("  Ready! Opening desktop window...\n")

    window = webview.create_window(
        "SynthChat",
        f"http://127.0.0.1:{port}/synthchat/",
        width=1200,
        height=800,
        min_size=(800, 500),
        background_color="#1a1d21",
        text_select=True,
    )

    webview.start()

    if server_process:
        server_process.terminate()
        server_process.wait(timeout=5)

    print("  SynthChat closed.")


if __name__ == "__main__":
    main()
