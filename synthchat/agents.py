AGENTS = {
    "otto": {
        "id": "otto",
        "name": "Otto",
        "role": "Orchestrator",
        "avatar": "🐙",
        "color": "#00e5c8",
        "description": "Routes tasks and coordinates the team",
        "tools": [],
    },
    "dev": {
        "id": "dev",
        "name": "Dev",
        "role": "Coder",
        "avatar": "⚡",
        "color": "#4ade80",
        "description": "Writes and edits code, manages files",
        "tools": ["read_file", "write_file", "edit_file", "run_command", "list_files", "search_files"],
    },
    "scout": {
        "id": "scout",
        "name": "Scout",
        "role": "Researcher",
        "avatar": "🔍",
        "color": "#fb923c",
        "description": "Searches the web, gathers information",
        "tools": ["web_search", "web_fetch", "browser_navigate", "browser_get_text"],
    },
    "sage": {
        "id": "sage",
        "name": "Sage",
        "role": "Reviewer",
        "avatar": "🦉",
        "color": "#c084fc",
        "description": "Reviews code, suggests improvements",
        "tools": ["read_file", "search_files"],
    },
    "recap": {
        "id": "recap",
        "name": "Recap",
        "role": "Summary",
        "avatar": "📋",
        "color": "#fbbf24",
        "description": "Summarizes completed tasks",
        "tools": [],
    },
}

AGENT_ORDER = ["otto", "dev", "scout", "sage", "recap"]
