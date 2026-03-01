import sys
from synthchat.app import create_standalone_app

if __name__ == "__main__":
    if "--skip-update" not in sys.argv:
        try:
            from octobot.updater import check_for_update, display_update_prompt, apply_update
            update_info = check_for_update()
            if update_info:
                display_update_prompt(update_info)
                apply_update(update_info)
        except Exception:
            pass
    else:
        sys.argv.remove("--skip-update")

    app = create_standalone_app()
    app.run(host="0.0.0.0", port=3000, debug=False)
