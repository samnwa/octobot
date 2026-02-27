import os
import json
import time
import uuid

HISTORY_DIR = os.path.join(os.path.expanduser("~"), ".octobot", "synthchat", "history")


def _ensure_dir():
    os.makedirs(HISTORY_DIR, exist_ok=True)


def _history_path(channel_id):
    return os.path.join(HISTORY_DIR, f"{channel_id}.json")


def save_message(channel_id, msg):
    _ensure_dir()
    path = _history_path(channel_id)

    messages = load_history(channel_id)

    entry = {
        "id": msg.get("id", str(uuid.uuid4())),
        "agent_id": msg.get("agent_id", ""),
        "agent_name": msg.get("agent_name", ""),
        "avatar": msg.get("avatar", ""),
        "color": msg.get("color", ""),
        "role": msg.get("role", ""),
        "content": msg.get("content", ""),
        "tool_use": msg.get("tool_use", None),
        "mentions": msg.get("mentions", []),
        "is_user": msg.get("is_user", False),
        "timestamp": msg.get("timestamp", time.time()),
    }

    if msg.get("documents"):
        entry["documents"] = msg["documents"]

    messages.append(entry)

    with open(path, "w") as f:
        json.dump(messages, f, indent=2)

    return entry


def load_history(channel_id):
    _ensure_dir()
    path = _history_path(channel_id)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def clear_history(channel_id):
    path = _history_path(channel_id)
    if os.path.exists(path):
        os.remove(path)
