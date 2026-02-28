import sys
import subprocess

REQUIRED_PACKAGES = {
    "anthropic": "anthropic",
    "click": "click",
    "flask": "flask",
    "fpdf": "fpdf2",
    "httpx": "httpx",
    "PIL": "pillow",
    "playwright": "playwright",
    "rich": "rich",
    "trafilatura": "trafilatura",
    "yaml": "pyyaml",
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


def check_for_updates():
    if "--skip-update" in sys.argv:
        sys.argv.remove("--skip-update")
        return

    try:
        from octobot.updater import check_for_update, display_update_prompt, apply_update

        update_info = check_for_update()
        if update_info is None:
            return

        if display_update_prompt(update_info):
            success = apply_update(update_info)
            if success:
                print("\n  Please restart octobot to use the new version.\n")
                sys.exit(0)
            else:
                print("\n  Update failed. Continuing with current version.\n")
    except Exception as e:
        print(f"  (Update check skipped: {e})")


if __name__ == "__main__":
    if not check_dependencies():
        sys.exit(1)

    check_for_updates()

    if "--cli" in sys.argv:
        sys.argv.remove("--cli")
        from octobot.cli import main
        main()
    else:
        from octoweb.app import run_web
        run_web()
