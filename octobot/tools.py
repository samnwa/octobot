import os
import re
import stat
import subprocess
import glob as glob_module
from datetime import datetime
from pathlib import Path

import httpx


PROJECT_ROOT = os.path.abspath(os.getcwd())

FORBIDDEN_PATH_PATTERNS = [
    r'^/etc/', r'^/usr/', r'^/bin/', r'^/sbin/', r'^/boot/',
    r'^/proc/', r'^/sys/', r'^/dev/', r'^/var/log/',
    r'\.ssh/', r'\.gnupg/', r'\.aws/', r'\.kube/',
]


def _resolve_and_check_path(path, write=False):
    resolved = os.path.abspath(os.path.expanduser(path))

    if write:
        for pattern in FORBIDDEN_PATH_PATTERNS:
            if re.search(pattern, resolved):
                return None, f"Access denied: writing to '{resolved}' is outside the allowed area"

        if not resolved.startswith(PROJECT_ROOT) and not resolved.startswith("/tmp"):
            return None, f"Access denied: path '{resolved}' is outside the project directory"

    return resolved, ""


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
        "description": "Fetch a URL via HTTP GET and return extracted content. By default, uses smart content extraction (trafilatura) to return only the main article/body text, stripping navigation, footers, ads, and boilerplate. Set extract=false for raw stripped HTML.",
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
                },
                "extract": {
                    "type": "boolean",
                    "description": "Use smart content extraction (default true). Set false for raw page text."
                }
            },
            "required": ["url"]
        },
        "input_examples": [
            {"url": "https://example.com"},
            {"url": "https://example.com/api", "timeout": 30, "extract": False}
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
    },
    {
        "name": "spawn_subagent",
        "description": "Spawn a subagent to handle a specific task independently. The subagent has access to all file, shell, and web tools but runs with its own conversation. Use for parallelizable or isolatable subtasks.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "Clear description of the task for the subagent to complete"
                },
                "context": {
                    "type": "string",
                    "description": "Optional additional context to help the subagent (e.g., relevant file paths, background info)"
                },
                "max_turns": {
                    "type": "integer",
                    "description": "Maximum number of tool-calling turns. Default 15."
                }
            },
            "required": ["task"]
        }
    },
    {
        "name": "browser_navigate",
        "description": "Navigate to a URL in a headless browser. Returns the page title and visible text content. The browser persists across calls so you can interact with the page after navigating.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to navigate to"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Navigation timeout in milliseconds. Default 30000."
                }
            },
            "required": ["url"]
        }
    },
    {
        "name": "browser_screenshot",
        "description": "Take a screenshot of the current browser page. Returns the file path to the saved PNG image.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "browser_click",
        "description": "Click an element on the current browser page using a CSS selector.",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "CSS selector of the element to click (e.g., 'button.submit', '#login-btn', 'a[href=\"/about\"]')"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in milliseconds to wait for element. Default 5000."
                }
            },
            "required": ["selector"]
        }
    },
    {
        "name": "browser_type",
        "description": "Type text into an input field on the current browser page using a CSS selector.",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "CSS selector of the input element (e.g., 'input[name=\"email\"]', '#search-box')"
                },
                "text": {
                    "type": "string",
                    "description": "The text to type into the field"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in milliseconds to wait for element. Default 5000."
                }
            },
            "required": ["selector", "text"]
        }
    },
    {
        "name": "browser_get_text",
        "description": "Get the text content of the current browser page or a specific element. Useful for reading rendered page content after navigation or interaction.",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "Optional CSS selector to get text from a specific element. If omitted, returns full page body text."
                }
            },
            "required": []
        }
    },
    {
        "name": "browser_snapshot",
        "description": "Take an accessibility snapshot of the current page. Returns a structured text tree of all interactive elements (buttons, links, inputs, etc.) with numbered refs like [0], [1], [2]. Use these refs with browser_click_ref and browser_type_ref for reliable element targeting. Much more reliable than CSS selectors.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "browser_click_ref",
        "description": "Click an interactive element by its ref number from browser_snapshot. Example: if snapshot shows '[3] button \"Submit\"', use ref=3 to click it. More reliable than CSS selectors.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ref": {
                    "type": "integer",
                    "description": "The ref number from the browser_snapshot output (e.g., 0, 1, 2)"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in milliseconds. Default 5000."
                }
            },
            "required": ["ref"]
        }
    },
    {
        "name": "browser_type_ref",
        "description": "Type text into an input element by its ref number from browser_snapshot. Example: if snapshot shows '[5] textbox \"Email\"', use ref=5 to type into it. More reliable than CSS selectors.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ref": {
                    "type": "integer",
                    "description": "The ref number from the browser_snapshot output"
                },
                "text": {
                    "type": "string",
                    "description": "The text to type into the element"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in milliseconds. Default 5000."
                }
            },
            "required": ["ref", "text"]
        }
    },
    {
        "name": "browser_vision",
        "description": "Take a screenshot and return it as a base64-encoded image that will be sent to the model for visual analysis. Use this when you need to SEE the page layout, verify visual elements, read images/charts, or handle CAPTCHAs. Returns the image inline so you can describe what you see.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "tool_search",
        "description": "Search for tools by name or description. Returns full schemas (with parameters) for matching tools. Use this to discover tools you haven't loaded yet. Many tools are available but their schemas are deferred to save tokens — use this to load them when needed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query to match against tool names and descriptions (e.g., 'file', 'browser', 'search', 'edit')"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "code_execution",
        "description": "Execute Python code that can call multiple tools as functions in a single round trip. Each tool is available as a Python function (e.g., read_file(path='x.py'), list_files(path='.'), run_command(command='ls')). Use this to chain tools efficiently: search files, then read matches, then process results — all in one call instead of multiple back-and-forth turns.\n\nAvailable tool functions: read_file, write_file, list_files, run_command, search_files, edit_file, web_fetch, apply_patch, web_search, tree, file_info, memory_save, memory_read. Use print() to output results.\n\nExample:\nfiles = list_files(path='src/')['files']\nfor f in files:\n    if f.endswith('.py'):\n        info = file_info(path=f)\n        print(f\"{f}: {info['size']} bytes\")",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute. Use tool functions like read_file(path='x'), list_files(path='.'), run_command(command='ls'), etc. Use print() to output results."
                }
            },
            "required": ["code"]
        }
    }
]


def _build_description_with_examples(tool_def):
    desc = tool_def["description"]
    examples = tool_def.get("input_examples")
    if examples:
        import json as _json
        example_strs = [_json.dumps(ex, indent=2) for ex in examples]
        desc += "\n\nExamples:\n" + "\n".join(f"```json\n{e}\n```" for e in example_strs)
    return desc


def get_tool_definitions():
    tools = []
    for t in TOOL_DEFINITIONS:
        if t.get("deferred_loading"):
            continue
        tool = {
            "name": t["name"],
            "description": _build_description_with_examples(t),
            "input_schema": {**t["input_schema"]},
        }
        tools.append(tool)
    return tools


def get_all_tool_definitions():
    tools = []
    for t in TOOL_DEFINITIONS:
        tool = {
            "name": t["name"],
            "description": _build_description_with_examples(t),
            "input_schema": {**t["input_schema"]},
        }
        tools.append(tool)
    return tools


def get_deferred_tool_names():
    return [t["name"] for t in TOOL_DEFINITIONS if t.get("deferred_loading")]


def get_deferred_tool_summary():
    lines = []
    for t in TOOL_DEFINITIONS:
        if t.get("deferred_loading"):
            short_desc = t["description"].split(".")[0] + "."
            lines.append(f"- **{t['name']}**: {short_desc}")
    return "\n".join(lines)


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
        "spawn_subagent": _handle_spawn_subagent,
        "browser_navigate": _handle_browser_navigate,
        "browser_screenshot": _handle_browser_screenshot,
        "browser_click": _handle_browser_click,
        "browser_type": _handle_browser_type,
        "browser_get_text": _handle_browser_get_text,
        "browser_snapshot": _handle_browser_snapshot,
        "browser_click_ref": _handle_browser_click_ref,
        "browser_type_ref": _handle_browser_type_ref,
        "browser_vision": _handle_browser_vision,
        "tool_search": _handle_tool_search,
        "code_execution": _handle_code_execution,
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
    resolved, err = _resolve_and_check_path(path)
    if err:
        return {"error": err}
    if not os.path.exists(resolved):
        return {"error": f"File not found: {path}"}
    with open(resolved, "r") as f:
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
    resolved, err = _resolve_and_check_path(path, write=True)
    if err:
        return {"error": err}
    os.makedirs(os.path.dirname(resolved) if os.path.dirname(resolved) else ".", exist_ok=True)
    with open(resolved, "w") as f:
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
    resolved, err = _resolve_and_check_path(path, write=True)
    if err:
        return {"error": err}
    old_string = input_data["old_string"]
    new_string = input_data["new_string"]
    if not os.path.exists(resolved):
        return {"error": f"File not found: {path}"}
    with open(resolved, "r") as f:
        content = f.read()
    count = content.count(old_string)
    if count == 0:
        return {"error": "old_string not found in file"}
    if count > 1:
        return {"error": f"old_string found {count} times - must be unique. Add more context."}
    new_content = content.replace(old_string, new_string, 1)
    with open(resolved, "w") as f:
        f.write(new_content)
    return {"status": "ok", "path": path}


def _handle_web_fetch(input_data):
    url = input_data["url"]
    timeout = input_data.get("timeout", 15)
    extract = input_data.get("extract", True)
    try:
        response = httpx.get(url, timeout=timeout, follow_redirects=True)
    except Exception:
        response = httpx.get(url, timeout=timeout, follow_redirects=True, verify=False)
    response.raise_for_status()
    html = response.text

    if extract:
        try:
            import trafilatura
            extracted = trafilatura.extract(html, include_links=True, include_tables=True)
            if extracted and len(extracted.strip()) > 100:
                text = extracted.strip()
                return {"content": text[:15000], "url": url, "status_code": response.status_code, "extraction": "smart"}
        except Exception:
            pass

    text = re.sub('<[^<]+?>', '', html)
    text = re.sub(r'\n\s*\n', '\n\n', text).strip()
    limit = 15000 if extract else 50000
    return {"content": text[:limit], "url": url, "status_code": response.status_code, "extraction": "raw"}


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


def _handle_spawn_subagent(input_data):
    from .subagent import run_subagent
    task = input_data["task"]
    context = input_data.get("context")
    max_turns = input_data.get("max_turns")
    return run_subagent(task=task, context=context, max_turns=max_turns)


def _handle_browser_navigate(input_data):
    from .browser import get_browser_manager
    url = input_data["url"]
    timeout = input_data.get("timeout", 30000)
    return get_browser_manager().navigate(url, timeout=timeout)


def _handle_browser_screenshot(input_data):
    from .browser import get_browser_manager
    return get_browser_manager().screenshot()


def _handle_browser_click(input_data):
    from .browser import get_browser_manager
    selector = input_data["selector"]
    timeout = input_data.get("timeout", 5000)
    return get_browser_manager().click(selector, timeout=timeout)


def _handle_browser_type(input_data):
    from .browser import get_browser_manager
    selector = input_data["selector"]
    text = input_data["text"]
    timeout = input_data.get("timeout", 5000)
    return get_browser_manager().type_text(selector, text, timeout=timeout)


def _handle_browser_get_text(input_data):
    from .browser import get_browser_manager
    selector = input_data.get("selector")
    return get_browser_manager().get_text(selector=selector)


def _handle_browser_snapshot(input_data):
    from .browser import get_browser_manager
    return get_browser_manager().snapshot()


def _handle_browser_click_ref(input_data):
    from .browser import get_browser_manager
    ref = input_data["ref"]
    timeout = input_data.get("timeout", 5000)
    return get_browser_manager().click_ref(ref, timeout=timeout)


def _handle_browser_type_ref(input_data):
    from .browser import get_browser_manager
    ref = input_data["ref"]
    text = input_data["text"]
    timeout = input_data.get("timeout", 5000)
    return get_browser_manager().type_ref(ref, text, timeout=timeout)


def _handle_browser_vision(input_data):
    from .browser import get_browser_manager
    return get_browser_manager().screenshot(return_base64=True)


def _handle_tool_search(input_data):
    import json as _json
    query = input_data["query"].lower()
    matches = []
    for t in TOOL_DEFINITIONS:
        name = t["name"].lower()
        desc = t["description"].lower()
        if query in name or query in desc:
            matches.append({
                "name": t["name"],
                "description": t["description"],
                "input_schema": t["input_schema"],
            })
    if not matches:
        words = query.split()
        for t in TOOL_DEFINITIONS:
            name = t["name"].lower()
            desc = t["description"].lower()
            if any(w in name or w in desc for w in words):
                matches.append({
                    "name": t["name"],
                    "description": t["description"],
                    "input_schema": t["input_schema"],
                })
    return {"matches": matches, "count": len(matches)}


def _handle_code_execution(input_data):
    from .sandbox import execute_code
    code = input_data["code"]
    sandbox_tools = {
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
    return execute_code(code, sandbox_tools)
