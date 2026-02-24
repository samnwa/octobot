import os
import re
import stat
import subprocess
import glob as glob_module
from datetime import datetime
from pathlib import Path

import httpx


TOOL_DEFINITIONS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file at the given path. Returns the file content as a string.",
        "allowed_caller": "code_execution_20260120",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute or relative path to the file to read"
                },
                "offset": {
                    "type": "integer",
                    "description": "Line number to start reading from (1-indexed). Optional."
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of lines to read. Optional."
                }
            },
            "required": ["path"]
        },
        "input_examples": [
            {"path": "src/main.py"},
            {"path": "README.md", "offset": 1, "limit": 50}
        ],
        "deferred_loading": True
    },
    {
        "name": "write_file",
        "description": "Write content to a file, creating it if it doesn't exist or overwriting if it does. Creates parent directories as needed.",
        "allowed_caller": "code_execution_20260120",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to write"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file"
                }
            },
            "required": ["path", "content"]
        },
        "input_examples": [
            {"path": "output.txt", "content": "Hello, world!"},
            {"path": "src/config.json", "content": "{\"key\": \"value\"}"}
        ],
        "deferred_loading": True
    },
    {
        "name": "list_files",
        "description": "List files and directories at the given path. Supports glob patterns for filtering.",
        "allowed_caller": "code_execution_20260120",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path to list, or a glob pattern like '**/*.py'"
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Whether to list recursively. Default false."
                }
            },
            "required": ["path"]
        },
        "input_examples": [
            {"path": "."},
            {"path": "src/**/*.py", "recursive": True}
        ],
        "deferred_loading": True
    },
    {
        "name": "run_command",
        "description": "Execute a shell command and return its stdout, stderr, and exit code. Use for running scripts, installing packages, git operations, etc.",
        "allowed_caller": "code_execution_20260120",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds. Default 30."
                },
                "cwd": {
                    "type": "string",
                    "description": "Working directory. Default is current directory."
                }
            },
            "required": ["command"]
        },
        "input_examples": [
            {"command": "ls -la"},
            {"command": "python test.py", "timeout": 60},
            {"command": "git status", "cwd": "/home/user/project"}
        ],
        "deferred_loading": True
    },
    {
        "name": "search_files",
        "description": "Search for a pattern (regex) across files. Returns matching lines with file paths and line numbers.",
        "allowed_caller": "code_execution_20260120",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Regex pattern to search for"
                },
                "path": {
                    "type": "string",
                    "description": "Directory or file to search in. Default is current directory."
                },
                "file_pattern": {
                    "type": "string",
                    "description": "Glob pattern to filter files, e.g. '*.py'"
                }
            },
            "required": ["pattern"]
        },
        "input_examples": [
            {"pattern": "def main", "path": "src/"},
            {"pattern": "TODO|FIXME", "file_pattern": "*.py"}
        ],
        "deferred_loading": True
    },
    {
        "name": "edit_file",
        "description": "Replace an exact string in a file with new content. The old_string must match exactly (including whitespace). Use for surgical edits without rewriting the whole file.",
        "allowed_caller": "code_execution_20260120",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to edit"
                },
                "old_string": {
                    "type": "string",
                    "description": "Exact string to find and replace"
                },
                "new_string": {
                    "type": "string",
                    "description": "String to replace old_string with"
                }
            },
            "required": ["path", "old_string", "new_string"]
        },
        "input_examples": [
            {
                "path": "src/app.py",
                "old_string": "DEBUG = True",
                "new_string": "DEBUG = False"
            }
        ],
        "deferred_loading": True
    },
    {
        "name": "web_fetch",
        "description": "Fetch a URL via HTTP GET and return the content as plain text (HTML tags stripped).",
        "allowed_caller": "code_execution_20260120",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to fetch"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Request timeout in seconds. Default 15."
                }
            },
            "required": ["url"]
        },
        "input_examples": [
            {"url": "https://example.com"},
            {"url": "https://example.com/api", "timeout": 30}
        ],
        "deferred_loading": True
    },
    {
        "name": "apply_patch",
        "description": "Apply a unified diff patch to one or more files. Accepts standard unified diff format with --- +++ and @@ hunk headers.",
        "allowed_caller": "code_execution_20260120",
        "input_schema": {
            "type": "object",
            "properties": {
                "patch": {
                    "type": "string",
                    "description": "The unified diff patch content to apply"
                }
            },
            "required": ["patch"]
        },
        "input_examples": [
            {"patch": "--- a/file.py\n+++ b/file.py\n@@ -1,3 +1,3 @@\n line1\n-old line\n+new line\n line3\n"}
        ],
        "deferred_loading": True
    },
    {
        "name": "web_search",
        "description": "Search the web using DuckDuckGo. Returns titles, URLs, and snippets for the top results.",
        "allowed_caller": "code_execution_20260120",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query"
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return. Default 5."
                }
            },
            "required": ["query"]
        },
        "input_examples": [
            {"query": "python asyncio tutorial"},
            {"query": "latest rust release", "num_results": 10}
        ],
        "deferred_loading": True
    },
    {
        "name": "tree",
        "description": "Show directory tree structure with indented formatting. Useful for understanding project layout.",
        "allowed_caller": "code_execution_20260120",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Root directory path. Default is current directory."
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum depth to traverse. Default 3."
                }
            },
            "required": []
        },
        "input_examples": [
            {"path": "."},
            {"path": "src", "max_depth": 2}
        ],
        "deferred_loading": True
    },
    {
        "name": "file_info",
        "description": "Get file metadata (size, modification time, permissions) without reading the file content.",
        "allowed_caller": "code_execution_20260120",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file"
                }
            },
            "required": ["path"]
        },
        "input_examples": [
            {"path": "src/main.py"}
        ],
        "deferred_loading": True
    },
    {
        "name": "memory_save",
        "description": "Save information to persistent memory. Appends markdown-formatted content to ~/.octobot/memory/MEMORY.md for later recall.",
        "allowed_caller": "code_execution_20260120",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Markdown-formatted content to append to memory"
                }
            },
            "required": ["content"]
        },
        "input_examples": [
            {"content": "## Project Notes\n- Uses Flask backend\n- Database is PostgreSQL"}
        ],
        "deferred_loading": True
    },
    {
        "name": "memory_read",
        "description": "Read the current persistent memory file (~/.octobot/memory/MEMORY.md). Returns all previously saved memory content.",
        "allowed_caller": "code_execution_20260120",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        },
        "input_examples": [
            {}
        ],
        "deferred_loading": True
    }
]


def get_tool_definitions():
    tools = []
    for t in TOOL_DEFINITIONS:
        tool = {
            "name": t["name"],
            "description": t["description"],
            "input_schema": {**t["input_schema"]},
        }
        tools.append(tool)
    return tools


def get_deferred_tool_names():
    return [t["name"] for t in TOOL_DEFINITIONS if t.get("deferred_loading")]


def execute_tool(name, input_data):
    handlers = {
        "read_file": _handle_read_file,
        "write_file": _handle_write_file,
        "list_files": _handle_list_files,
        "run_command": _handle_run_command,
        "search_files": _handle_search_files,
        "edit_file": _handle_edit_file,
        "web_fetch": _handle_web_fetch,
        "apply_patch": _handle_apply_patch,
        "web_search": _handle_web_search,
        "tree": _handle_tree,
        "file_info": _handle_file_info,
        "memory_save": _handle_memory_save,
        "memory_read": _handle_memory_read,
    }
    handler = handlers.get(name)
    if not handler:
        return {"error": f"Unknown tool: {name}"}
    try:
        return handler(input_data)
    except Exception as e:
        return {"error": f"{type(e).__name__}: {str(e)}"}


def _handle_read_file(input_data):
    path = input_data["path"]
    if not os.path.exists(path):
        return {"error": f"File not found: {path}"}
    with open(path, "r") as f:
        lines = f.readlines()
    offset = input_data.get("offset", 1)
    limit = input_data.get("limit")
    start = max(0, offset - 1)
    if limit:
        lines = lines[start:start + limit]
    else:
        lines = lines[start:]
    numbered = []
    for i, line in enumerate(lines, start=start + 1):
        numbered.append(f"{i:>6}| {line.rstrip()}")
    return {"content": "\n".join(numbered), "total_lines": len(lines)}


def _handle_write_file(input_data):
    path = input_data["path"]
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w") as f:
        f.write(input_data["content"])
    return {"status": "ok", "path": path, "bytes_written": len(input_data["content"])}


def _handle_list_files(input_data):
    path = input_data["path"]
    recursive = input_data.get("recursive", False)
    if "*" in path or "?" in path:
        matches = glob_module.glob(path, recursive=recursive)
        return {"files": sorted(matches)}
    if not os.path.exists(path):
        return {"error": f"Path not found: {path}"}
    if os.path.isfile(path):
        return {"files": [path]}
    entries = []
    if recursive:
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for f in files:
                if not f.startswith("."):
                    entries.append(os.path.relpath(os.path.join(root, f), path))
    else:
        for entry in sorted(os.listdir(path)):
            if entry.startswith("."):
                continue
            full = os.path.join(path, entry)
            suffix = "/" if os.path.isdir(full) else ""
            entries.append(entry + suffix)
    return {"files": entries}


def _handle_run_command(input_data):
    command = input_data["command"]
    timeout = input_data.get("timeout", 30)
    cwd = input_data.get("cwd")
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        output = {}
        if result.stdout:
            output["stdout"] = result.stdout[:50000]
        if result.stderr:
            output["stderr"] = result.stderr[:10000]
        output["exit_code"] = result.returncode
        return output
    except subprocess.TimeoutExpired:
        return {"error": f"Command timed out after {timeout}s"}


def _handle_search_files(input_data):
    pattern = input_data["pattern"]
    path = input_data.get("path", ".")
    file_pattern = input_data.get("file_pattern")
    cmd_parts = ["grep", "-rn", "--color=never"]
    if file_pattern:
        cmd_parts.extend(["--include", file_pattern])
    cmd_parts.extend(["-E", pattern, path])
    try:
        result = subprocess.run(
            cmd_parts,
            capture_output=True,
            text=True,
            timeout=15,
        )
        lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
        if len(lines) > 200:
            lines = lines[:200]
            lines.append(f"... truncated ({len(lines)}+ matches)")
        return {"matches": lines, "count": len(lines)}
    except subprocess.TimeoutExpired:
        return {"error": "Search timed out after 15s"}


def _handle_edit_file(input_data):
    path = input_data["path"]
    old_string = input_data["old_string"]
    new_string = input_data["new_string"]
    if not os.path.exists(path):
        return {"error": f"File not found: {path}"}
    with open(path, "r") as f:
        content = f.read()
    count = content.count(old_string)
    if count == 0:
        return {"error": "old_string not found in file"}
    if count > 1:
        return {"error": f"old_string found {count} times - must be unique. Add more context."}
    new_content = content.replace(old_string, new_string, 1)
    with open(path, "w") as f:
        f.write(new_content)
    return {"status": "ok", "path": path}


def _handle_web_fetch(input_data):
    url = input_data["url"]
    timeout = input_data.get("timeout", 15)
    response = httpx.get(url, timeout=timeout, follow_redirects=True)
    response.raise_for_status()
    html = response.text
    text = re.sub('<[^<]+?>', '', html)
    text = re.sub(r'\n\s*\n', '\n\n', text).strip()
    return {"content": text[:50000], "url": url, "status_code": response.status_code}


def _handle_apply_patch(input_data):
    patch_text = input_data["patch"]
    lines = patch_text.split('\n')
    files_patched = []
    current_file = None
    hunks = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('--- '):
            i += 1
            continue
        if line.startswith('+++ '):
            path = line[4:].strip()
            if path.startswith('b/'):
                path = path[2:]
            if current_file and hunks:
                _apply_hunks(current_file, hunks)
                files_patched.append(current_file)
                hunks = []
            current_file = path
            i += 1
            continue
        if line.startswith('@@ '):
            match = re.match(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
            if match:
                hunk = {
                    "old_start": int(match.group(1)),
                    "old_count": int(match.group(2)) if match.group(2) else 1,
                    "new_start": int(match.group(3)),
                    "new_count": int(match.group(4)) if match.group(4) else 1,
                    "lines": []
                }
                i += 1
                while i < len(lines):
                    l = lines[i]
                    if l.startswith('@@ ') or l.startswith('--- ') or l.startswith('+++ '):
                        break
                    hunk["lines"].append(l)
                    i += 1
                hunks.append(hunk)
                continue
        i += 1
    if current_file and hunks:
        _apply_hunks(current_file, hunks)
        files_patched.append(current_file)
    return {"status": "ok", "files_patched": files_patched}


def _apply_hunks(path, hunks):
    if os.path.exists(path):
        with open(path, "r") as f:
            file_lines = f.readlines()
    else:
        file_lines = []
    offset = 0
    for hunk in hunks:
        start = hunk["old_start"] - 1 + offset
        old_lines = []
        new_lines = []
        for l in hunk["lines"]:
            if l.startswith('-'):
                old_lines.append(l[1:])
            elif l.startswith('+'):
                new_lines.append(l[1:] + '\n')
            elif l.startswith(' '):
                old_lines.append(l[1:])
                new_lines.append(l[1:] + '\n')
            else:
                old_lines.append(l)
                new_lines.append(l + '\n')
        file_lines[start:start + len(old_lines)] = new_lines
        offset += len(new_lines) - len(old_lines)
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w") as f:
        f.writelines(file_lines)


def _handle_web_search(input_data):
    query = input_data["query"]
    num_results = input_data.get("num_results", 5)
    response = httpx.get(
        "https://html.duckduckgo.com/html/",
        params={"q": query},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=15,
        follow_redirects=True,
    )
    response.raise_for_status()
    html = response.text
    results = []
    result_blocks = re.findall(
        r'<a[^>]+class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?'
        r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
        html,
        re.DOTALL,
    )
    for url, title, snippet in result_blocks[:num_results]:
        title_clean = re.sub('<[^<]+?>', '', title).strip()
        snippet_clean = re.sub('<[^<]+?>', '', snippet).strip()
        results.append({"title": title_clean, "url": url, "snippet": snippet_clean})
    return {"results": results, "query": query}


def _handle_tree(input_data):
    root = input_data.get("path", ".")
    max_depth = input_data.get("max_depth", 3)
    entries = []
    count = 0
    max_entries = 500

    def _walk(dir_path, prefix, depth):
        nonlocal count
        if depth > max_depth or count >= max_entries:
            return
        try:
            items = sorted(os.listdir(dir_path))
        except PermissionError:
            return
        items = [item for item in items if not item.startswith('.')]
        dirs = []
        files = []
        for item in items:
            full = os.path.join(dir_path, item)
            if os.path.isdir(full):
                dirs.append(item)
            else:
                files.append(item)
        all_items = dirs + files
        for i, item in enumerate(all_items):
            if count >= max_entries:
                entries.append(f"{prefix}... (truncated at {max_entries} entries)")
                return
            is_last = i == len(all_items) - 1
            connector = "└── " if is_last else "├── "
            full = os.path.join(dir_path, item)
            suffix = "/" if os.path.isdir(full) else ""
            entries.append(f"{prefix}{connector}{item}{suffix}")
            count += 1
            if os.path.isdir(full) and depth < max_depth:
                extension = "    " if is_last else "│   "
                _walk(full, prefix + extension, depth + 1)

    entries.append(root)
    count += 1
    _walk(root, "", 1)
    return {"tree": "\n".join(entries)}


def _handle_file_info(input_data):
    path = input_data["path"]
    if not os.path.exists(path):
        return {"error": f"Path not found: {path}"}
    st = os.stat(path)
    return {
        "path": path,
        "size_bytes": st.st_size,
        "modified": datetime.fromtimestamp(st.st_mtime).isoformat(),
        "created": datetime.fromtimestamp(st.st_ctime).isoformat(),
        "permissions": stat.filemode(st.st_mode),
        "is_file": os.path.isfile(path),
        "is_directory": os.path.isdir(path),
    }


MEMORY_PATH = Path.home() / '.octobot' / 'memory' / 'MEMORY.md'


def _handle_memory_save(input_data):
    content = input_data["content"]
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MEMORY_PATH, "a") as f:
        f.write(content + "\n\n")
    return {"status": "ok", "path": str(MEMORY_PATH)}


def _handle_memory_read(input_data):
    if not MEMORY_PATH.exists():
        return {"content": "", "message": "No memory file found. Use memory_save to create one."}
    with open(MEMORY_PATH, "r") as f:
        content = f.read()
    return {"content": content, "path": str(MEMORY_PATH)}
