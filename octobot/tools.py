import os
import subprocess
import glob as glob_module


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
