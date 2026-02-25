import json
import time
from pathlib import Path
from .config import CONFIG_DIR

HISTORY_DIR = CONFIG_DIR / "history"

def _ensure_dir():
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

def _session_path(session_id):
    return HISTORY_DIR / f"{session_id}.json"

def generate_session_id():
    return f"session_{int(time.time() * 1000)}"

def save_session(session_id, model, messages, input_tokens=0, output_tokens=0):
    _ensure_dir()
    data = {
        "session_id": session_id,
        "model": model,
        "messages": _serialize_messages(messages),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "updated_at": time.time(),
    }
    path = _session_path(session_id)
    if path.exists():
        try:
            existing = json.loads(path.read_text())
            data["created_at"] = existing.get("created_at", data["updated_at"])
        except (json.JSONDecodeError, KeyError):
            data["created_at"] = data["updated_at"]
    else:
        data["created_at"] = data["updated_at"]
    path.write_text(json.dumps(data, default=str))

def load_session(session_id):
    path = _session_path(session_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        data["messages"] = _deserialize_messages(data.get("messages", []))
        return data
    except (json.JSONDecodeError, KeyError):
        return None

def list_sessions(limit=20):
    _ensure_dir()
    sessions = []
    for f in sorted(HISTORY_DIR.glob("session_*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(f.read_text())
            preview = _get_preview(data)
            sessions.append({
                "session_id": data.get("session_id", f.stem),
                "model": data.get("model", "unknown"),
                "preview": preview,
                "message_count": len(data.get("messages", [])),
                "input_tokens": data.get("input_tokens", 0),
                "output_tokens": data.get("output_tokens", 0),
                "created_at": data.get("created_at", 0),
                "updated_at": data.get("updated_at", 0),
            })
        except (json.JSONDecodeError, KeyError):
            continue
        if len(sessions) >= limit:
            break
    return sessions

def delete_session(session_id):
    path = _session_path(session_id)
    if path.exists():
        path.unlink()
        return True
    return False

def _get_preview(data):
    for msg in data.get("messages", []):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                text = " ".join(
                    b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
                )
            else:
                text = str(content)
            if text.strip():
                return text.strip()[:100]
    return "(empty)"

def _serialize_messages(messages):
    serialized = []
    for msg in messages:
        entry = {"role": msg["role"]}
        content = msg.get("content", "")
        if isinstance(content, str):
            entry["content"] = content
        elif isinstance(content, list):
            entry["content"] = [_serialize_block(b) for b in content]
        else:
            entry["content"] = str(content)
        serialized.append(entry)
    return serialized

def _serialize_block(block):
    if isinstance(block, dict):
        return block
    if hasattr(block, "type"):
        if block.type == "text":
            return {"type": "text", "text": block.text}
        elif block.type == "thinking":
            return {"type": "thinking", "thinking": getattr(block, "thinking", "")}
        elif block.type == "tool_use":
            return {
                "type": "tool_use",
                "id": block.id,
                "name": block.name,
                "input": block.input,
            }
        elif block.type == "tool_result":
            return {
                "type": "tool_result",
                "tool_use_id": getattr(block, "tool_use_id", ""),
                "content": getattr(block, "content", ""),
            }
    return {"type": "text", "text": str(block)}

def _deserialize_messages(messages):
    result = []
    for msg in messages:
        entry = {"role": msg["role"]}
        content = msg.get("content", "")
        if isinstance(content, str):
            entry["content"] = content
        elif isinstance(content, list):
            entry["content"] = content
        else:
            entry["content"] = str(content)
        result.append(entry)
    return result
