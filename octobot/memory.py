from pathlib import Path

MEMORY_DIR = Path.home() / ".octobot" / "memory"
MEMORY_FILE = MEMORY_DIR / "MEMORY.md"


def load_memory_context():
    if MEMORY_FILE.exists():
        content = MEMORY_FILE.read_text().strip()
        if content:
            return content
    return ""
