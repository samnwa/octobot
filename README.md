# Octobot

```
 ▄██████▄   ▄████████     ███      ▄██████▄
███    ███ ███    ███ ▀█████████▄ ███    ███
███    ███ ███    █▀     ▀███▀▀██ ███    ███
███    ███ ███            ███   ▀ ███    ███
███    ███ ███            ███     ███    ███
███    ███ ███    █▄      ███     ███    ███
███    ███ ███    ███     ███     ███    ███
 ▀██████▀  ████████▀     ▄████▀    ▀██████▀
▀█████████▄   ▄██████▄      ███
  ███    ███ ███    ███ ▀█████████▄
  ███    ███ ███    ███    ▀███▀▀██
 ▄███▄▄▄██▀  ███    ███     ███   ▀
▀▀███▀▀▀██▄  ███    ███     ███
  ███    ██▄ ███    ███     ███
  ███    ███ ███    ███     ███
▄█████████▀   ▀██████▀     ▄████▀
```

A locally-runnable, super-efficient AI tool-calling agent. Inspired by [Octofriend](https://github.com/synthetic-lab/octofriend), [OpenClaw](https://github.com/openclaw/openclaw), and [PicoClaw](https://github.com/sipeed/picoclaw) -- built for developers who want a lightweight, extensible coding assistant that runs right in their terminal.

## Features

- **25 Built-in Tools** -- file ops, shell, web, browser automation, subagents, memory, and more
- **Efficiency Optimizations** -- deferred tool loading, code execution sandbox, smart web extraction, and input examples (inspired by Anthropic's advanced tool calling)
- **Browser Automation + Vision** -- Playwright-powered headless browser with accessibility snapshots, ref-based targeting (like OpenClaw), and vision support for seeing pages
- **Subagents** -- delegate subtasks to independent child agents that run with their own conversation
- **Approval Workflows** -- dangerous operations (rm -rf, sudo, writing to dotfiles) require your confirmation
- **Persistent Memory** -- saves important info to `~/.octobot/memory/MEMORY.md` across sessions
- **Skills System** -- extensible markdown-based skills (compatible with OpenClaw/PicoClaw format)
- **Custom Identity** -- customize agent personality via `~/.octobot/AGENT.md` and `IDENTITY.md`
- **Loop Detection** -- automatically stops repetitive tool-call loops to save tokens
- **Multi-turn Agent Loop** -- chains tool calls to complete complex tasks (up to 50 turns)
- **Rich Terminal UI** -- markdown rendering, syntax highlighting, color-coded panels
- **Thinking Display** -- see the model's reasoning process in real time
- **Token Tracking** -- monitor input/output token usage per session

## Setup

### 1. Get a Synthetic API Key

Sign up at [synthetic.new](https://dev.synthetic.new) and get your API key.

### 2. Set Your API Key

```bash
export SYNTHETIC_API_KEY="your-key-here"
```

Or store it in `~/.octobot/config.json`:

```json
{
  "synthetic_api_key": "your-key-here"
}
```

### 3. Install Dependencies

```bash
pip install anthropic rich click httpx playwright
playwright install chromium
```

### 4. Run

```bash
python main.py
```

## Usage

### Interactive Mode

```bash
python main.py
```

Type your request at the `>` prompt. Octobot will use its tools to read files, write code, run commands, browse the web, and more.

### Single Prompt

```bash
python main.py -s "List all Python files in this project"
```

### Choose a Model

```bash
python main.py -m "hf:meta-llama/Llama-3.3-70B-Instruct"
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `/tools` | List all available tools with descriptions |
| `/skills` | List loaded skills |
| `/reset` | Clear conversation history and close browser |
| `/model` | Show the current model |
| `/model <name>` | Switch to a different model (resets conversation) |
| `/tokens` | Show input/output token usage for the session |
| `/help` | Show all commands |
| `/quit` | Exit octobot |

## Available Tools

### File Operations
| Tool | Description |
|------|-------------|
| `read_file` | Read file contents with optional line offset/limit |
| `write_file` | Create or overwrite files (creates parent dirs) |
| `edit_file` | Replace an exact string in a file (surgical edits) |
| `list_files` | List directory contents or match glob patterns |
| `search_files` | Search for regex patterns across files |
| `tree` | Show directory tree structure |
| `file_info` | Get file metadata (size, dates, permissions) |
| `apply_patch` | Apply unified diff patches to files |

### Shell & Web
| Tool | Description |
|------|-------------|
| `run_command` | Execute shell commands with timeout control |
| `web_fetch` | HTTP GET with smart content extraction (trafilatura) |
| `web_search` | Search the web via DuckDuckGo |

### Browser Automation
| Tool | Description |
|------|-------------|
| `browser_navigate` | Navigate to a URL, get page title and text |
| `browser_snapshot` | Accessibility tree with numbered refs for reliable targeting |
| `browser_click_ref` | Click element by ref number from snapshot (preferred) |
| `browser_type_ref` | Type into element by ref number from snapshot (preferred) |
| `browser_vision` | Screenshot sent as image to model for visual analysis |
| `browser_screenshot` | Take a screenshot and save to file |
| `browser_click` | Click an element by CSS selector (fallback) |
| `browser_type` | Type text into input by CSS selector (fallback) |
| `browser_get_text` | Get text content of the page or a specific element |

### Memory & Agents
| Tool | Description |
|------|-------------|
| `memory_save` | Save information to persistent memory |
| `memory_read` | Read persistent memory from previous sessions |
| `spawn_subagent` | Delegate a subtask to an independent child agent |

### Efficiency Meta-Tools
| Tool | Description |
|------|-------------|
| `tool_search` | Discover tools by name/description; loads full schemas on demand |
| `code_execution` | Python sandbox that chains multiple tool calls in one round trip |

## Approval Workflows

Octobot includes a safety layer that requires your confirmation before executing potentially dangerous operations. When a flagged operation is detected, you'll see a red warning panel and a `[Y/n]` prompt.

### What gets flagged

**Dangerous commands** (via `run_command`):
- Recursive deletion (`rm -rf`)
- Elevated privileges (`sudo`)
- Unsafe permissions (`chmod 777`)
- Device writes (`> /dev/`)
- Disk operations (`dd if=`, `mkfs`)
- Piping remote scripts to shell (`curl ... | sh`)
- Force push (`git push --force`)
- Hard reset (`git reset --hard`)

**Sensitive file modifications** (via `write_file`, `edit_file`, `apply_patch`):
- Shell configs (`.bashrc`, `.zshrc`, `.profile`)
- SSH keys and GPG data (`.ssh/`, `.gnupg/`)
- Environment files (`.env`, `.env.production`)
- System directories (`/etc/`, `/usr/`, `/bin/`)

If you decline, the agent is told "User declined" and can try a different approach.

## Subagents

Octobot can delegate subtasks to independent child agents using the `spawn_subagent` tool. This is useful for isolatable work like research, file analysis, or parallel tasks.

### How subagents work

- Each subagent gets its own conversation history
- Subagents have access to all tools except `spawn_subagent` (no recursive spawning)
- Default limit of 15 turns (configurable per call)
- Subagent activity is displayed in magenta-bordered panels
- When finished, the subagent's summary is returned to the main agent

### Example use case

"Research the FastAPI docs and summarize the authentication options" -- the main agent can spawn a subagent to do the research while continuing with other work.

## Browser Automation

Octobot includes a headless Chromium browser powered by Playwright with two targeting approaches inspired by OpenClaw:

### Snapshot + Ref Targeting (Recommended)

The **hybrid approach** used by OpenClaw. Instead of fragile CSS selectors, the agent takes an accessibility snapshot of the page, which returns a text tree with numbered refs:

```
- heading "Example Domain" [level=1]
- paragraph: Welcome to our site
  [0] link "Sign In"
  [1] link "Learn More"
- form:
  [2] textbox "Email"
  [3] textbox "Password"
  [4] button "Submit"
```

The model reads this as plain text (no vision needed for basic interactions) and acts by ref number: "click ref 4" or "type into ref 2." This is deterministic and reliable.

### Vision Support

For complex visual tasks — verifying layout, reading charts/images, handling CAPTCHAs — the `browser_vision` tool takes a screenshot and sends the actual image to the model as a base64-encoded image block. The model can then describe what it sees and decide next steps.

**Typical workflow:**
1. `browser_navigate` to go to a page
2. `browser_snapshot` to see interactive elements as text refs
3. `browser_type_ref` / `browser_click_ref` to interact by ref number
4. `browser_vision` if you need to visually verify something

### Browser Profile Persistence

To reuse your existing login sessions, set a browser profile in `~/.octobot/config.json`:

```json
{
  "browser_profile": "~/.config/google-chrome/Default"
}
```

This tells Playwright to use your real Chrome profile with all your cookies and sessions. Without this, each session starts with a clean browser.

### How it works

1. On the first browser tool call, Playwright launches a headless Chromium instance
2. The browser stays open so you can chain interactions (navigate, snapshot, fill form, click submit, verify)
3. The browser auto-closes on `/reset`, `/quit`, or exit
4. On NixOS/Replit, library paths are auto-discovered via `ldd` and `nix-store`

### Cross-platform

Playwright works on Windows, macOS, and Linux. Just run `playwright install chromium` to download the browser for your OS.

## Efficiency Optimizations

Octobot implements four techniques inspired by Anthropic's advanced tool calling, done on our end for maximum compatibility:

### 1. Deferred Tool Loading

With 25 tools, sending every schema on every API call wastes tokens. Octobot splits tools into two tiers:

- **Always-loaded** (12 tools): Browser tools, subagents, meta-tools -- full schemas always sent
- **Deferred** (13 tools): File ops, shell, web, memory -- listed as compact name + one-line description in the system prompt

The model can still call deferred tools directly if it knows the parameters. When it doesn't, it uses `tool_search` to load the full schema on demand. This saves significant tokens per request.

### 2. Code Execution Sandbox

Instead of the model making one tool call per turn (call tool, wait for result, call next tool, wait again), the `code_execution` tool lets it write Python code that chains multiple tools in a single round trip:

```python
files = list_files(path="src/")["files"]
for f in files:
    if f.endswith(".py"):
        info = file_info(path=f)
        print(f"{f}: {info['size_bytes']} bytes")
```

This runs in a sandboxed environment with dangerous builtins blocked (`__import__`, `eval`, `exec`, `open`). Only tool functions and safe builtins are available. Has a 30-second timeout.

### 3. Smart Web Extraction

The `web_fetch` tool uses [trafilatura](https://github.com/adbar/trafilatura) to extract just the main content from web pages, stripping navigation, footers, ads, and boilerplate. This typically reduces content from 50,000+ characters to under 15,000 characters of focused text.

Set `extract: false` to get raw stripped HTML when you need the full page.

### 4. Input Examples

Tool definitions include `input_examples` that are embedded into descriptions sent to the model. This helps the model understand correct parameter formats without trial and error, reducing failed tool calls.

## Persistent Memory

Octobot can remember things across sessions. When it saves information using `memory_save`, it's written to `~/.octobot/memory/MEMORY.md`. This memory is loaded into the system prompt on every startup.

Use cases:
- User preferences ("I prefer tabs over spaces")
- Project context ("This project uses FastAPI with SQLAlchemy")
- Important discoveries found during coding sessions

## Skills System

Skills are markdown-based instruction packages that teach octobot new capabilities. They're compatible with the OpenClaw/PicoClaw skill format.

### Creating a Skill

```bash
mkdir -p ~/.octobot/skills/my-skill
```

Create `~/.octobot/skills/my-skill/SKILL.md`:

```markdown
---
name: my_skill
description: A custom skill for my workflow
---

# My Custom Skill

Instructions for octobot on how to use this skill...
```

### Skill Directories

- `~/.octobot/skills/` -- user-level skills (always loaded)
- `./skills/` -- workspace-level skills (project-specific)

## Custom Identity

Customize octobot's personality by creating files in `~/.octobot/`:

- **`AGENT.md`** -- Override the default system prompt with custom behavior instructions
- **`IDENTITY.md`** -- Add personality traits on top of the base behavior

## Architecture

```
main.py                  Entry point
octobot/
  __init__.py            Package init
  config.py              Configuration (API key, model, base URL, constants)
  tools.py               25 tool definitions and execution handlers
  agent.py               Core agent runtime with loop detection + approval
  cli.py                 Interactive CLI with Rich formatting
  memory.py              Persistent memory loading
  skills.py              Skills system (SKILL.md loader)
  identity.py            Identity/personality system
  approval.py            Approval workflows for dangerous operations
  subagent.py            Subagent spawning and management
  browser.py             Playwright browser automation with auto lib discovery
  sandbox.py             Sandboxed Python code execution for multi-tool chaining
```

### How It Works

1. You type a message at the prompt
2. Octobot assembles a system prompt from: identity + memory + skills
3. It sends your message + active tool schemas (12 always-loaded) to the model, with deferred tools listed compactly in the system prompt
4. The model responds with text, thinking, and/or tool calls
5. Dangerous operations are checked against approval rules -- you confirm or decline
6. Octobot executes tool calls locally and sends results back (code_execution runs multiple tools in one trip)
7. Loop detection monitors for repetitive patterns
8. This continues until the model has a final answer (up to 50 turns)

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `SYNTHETIC_API_KEY` | (required) | Your Synthetic API key |
| Model | `hf:zai-org/GLM-4.7` | Default model (supports tool use + thinking) |
| Max tokens | 16,384 | Maximum output tokens per response |
| Max turns | 50 | Maximum tool-calling turns per conversation |
| Subagent max turns | 15 | Maximum turns for subagent calls |
| API base URL | `https://api.synthetic.new/anthropic` | Synthetic API endpoint |

## Inspiration

- **[Octofriend](https://github.com/synthetic-lab/octofriend)** -- Open-source coding helper with great terminal UI
- **[OpenClaw](https://github.com/openclaw/openclaw)** -- Full-featured autonomous agent with skills, browser control, subagents, and loop detection
- **[PicoClaw](https://github.com/sipeed/picoclaw)** -- Ultra-lightweight Go agent with persistent memory and skills system

## Roadmap

- **Async Subagents** -- Run subagents in the background while main agent continues
- **Scheduled Tasks** -- Cron-based recurring agent runs
- **Multi-provider Support** -- Connect to Anthropic, OpenAI, local models
- **MCP Integration** -- Connect to external tool providers via Model Context Protocol

## License

MIT
