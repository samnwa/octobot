import sys
import subprocess

REQUIRED_PACKAGES = {
    "anthropic": "anthropic",
    "click": "click",
    "flask": "flask",
    "httpx": "httpx",
    "playwright": "playwright",
    "rich": "rich",
    "trafilatura": "trafilatura",
}


def check_dependencies():
    missing = []
    for module, package in REQUIRED_PACKAGES.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)

    if not missing:
        return True

    print(f"\nMissing dependencies: {', '.join(missing)}")
    print("\nYou can install them with one of:")
    print("  pip install .                      (recommended)")
    print("  pip install -r requirements.txt")
    print()

    try:
        answer = input("Install now with 'pip install .'? [Y/n] ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print()
        return False

    if answer in ("", "y", "yes"):
        print("\nInstalling dependencies...\n")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "."],
            cwd=sys.path[0] or ".",
        )
        if result.returncode != 0:
            print("\nInstallation failed. Try manually: pip install -r requirements.txt")
            return False
        print("\nDependencies installed successfully!\n")

        try:
            import playwright  # noqa: F401
            print("Installing Playwright Chromium browser...")
            subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
            )
            print()
        except ImportError:
            pass

        return True
    else:
        print("\nRun 'pip install .' when you're ready.")
        return False


if __name__ == "__main__":
    if not check_dependencies():
        sys.exit(1)

    if "--cli" in sys.argv:
        from octobot.cli import main
        main()
    else:
        from octoweb.app import run_web
        run_web()
