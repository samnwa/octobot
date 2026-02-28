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

**v0.1.0** | A locally-runnable, super-efficient AI tool-calling agent. Inspired by [Octofriend](https://github.com/synthetic-lab/octofriend), [OpenClaw](https://github.com/openclaw/openclaw), and [PicoClaw](https://github.com/sipeed/picoclaw) -- built for developers who want a lightweight, extensible coding assistant that runs right in their terminal.

## Quick Start

### Step 1: Get a free API key

Go to [synthetic.new](https://dev.synthetic.new), sign up, and copy your API key. This is what lets Octobot talk to the AI models.

### Step 2: Start Octobot

Download or clone the project, open a terminal in the octobot folder, and run one command:

**Windows** -- open Command Prompt or PowerShell, then run:
```
start.bat
```

**Mac / Linux** -- open Terminal, then run:
```
./start.sh
```

Both scripts install dependencies automatically on first run and open the web interface.

### Step 3: Paste your key and go

A page will open in your browser. Paste the API key you copied in Step 1, click **Start Octobot**, and you're in. Start chatting -- ask it to write code, search the web, create files, or anything else.

> **Power user?** Run `python main.py --cli` for a terminal-only interface instead of the web UI.

## Features

- **25 Built-in Tools** -- file ops, shell, web, browser automation, subagents, memory, and more
- **Web UI** -- dark terminal-style chat interface with file browser sidebar, HTML preview, model selector, command menu, real-time status indicator, and mobile responsiveness
- **First-Run Setup** -- guided setup screen for API key configuration on first launch
- **Efficiency Optimizations** -- deferred tool loading, code execution sandbox, smart web extraction, and input examples (inspired by Anthropic's advanced tool calling)
- **Smart Model Router** -- automatic failover across 4 models with health monitoring, latency tracking, and exponential backoff
- **Browser Automation + Vision** -- Playwright-powered headless browser with accessibility snapshots, ref-based targeting (like OpenClaw), and vision support for seeing pages
- **Subagents** -- delegate subtasks to independent child agents that run with their own conversation
- **Approval Workflows** -- dangerous operations (rm -rf, sudo, writing to dotfiles) require your confirmation
- **Persistent Memory** -- saves important info to `~/.octobot/memory/MEMORY.md` across sessions
- **Skills System** -- extensible markdown-based skills (compatible with OpenClaw/PicoClaw format)
- **Custom Identity** -- customize agent personality via `~/.octobot/AGENT.md` and `IDENTITY.md`
- **Loop Detection** -- automatically stops repetitive tool-call loops to save tokens
- **Multi-turn Agent Loop** -- chains tool calls to complete complex tasks (up to 50 turns)
- **Rich Terminal CLI** -- markdown rendering, syntax highlighting, color-coded panels, slash commands
- **Thinking Display** -- see the model's reasoning process in real time
- **Token Tracking** -- monitor input/output token usage per session
- **SynthChat** -- Slack-like multi-agent workspace with 6 specialized agents, custom agent creation, community library, and document generation ([full docs](synthchat/README.md))

## SynthChat

SynthChat is a multi-agent workspace built into Octobot. Instead of chatting with a single AI, you work with a team of 6 specialized agents that collaborate in real time -- an orchestrator routes tasks, a coder writes code, a researcher searches the web, a reviewer catches bugs, a scheduler manages reminders, and a summarizer wraps everything up.

**Access it** at `http://localhost:5000/synthchat/` when Octobot is running (or standalone via `python main-chat.py`).

**Key features:**

- **6 built-in agents** -- Otto (orchestrator), Dev (coder), Scout (researcher), Sage (reviewer), Scheduler, Recap (summarizer)
- **Custom agents** -- create your own agents with custom tools, skills, and personalities via the UI
- **Agent Library** -- browse, install, and publish agents with one click. Ships with 5 community agents (DataAnalyst, DevOps, Writer, QATester, Designer)
- **Channels** -- organize work into separate channels with different agent rosters
- **Document generation** -- agents create downloadable CSV, HTML, PDF, and PNG files
- **Skills system** -- load reusable knowledge modules into any agent

See the [SynthChat README](synthchat/README.md) for full documentation.

## Examples

The `examples/` directory contains files generated by Octobot to show what it can do:

- **[cookie-recipe-research.html](examples/cookie-recipe-research.html)** -- Asked Octobot to research chocolate chip cookie recipes and create a ratings page. It searched the web, compared recipes, and generated a styled HTML page with ratings and analysis -- all in one conversation.

Try it yourself:

```
> Research the top chocolate chip cookie recipes online and create an HTML page comparing them with ratings
```

Octobot will search the web, extract content from recipe sites, analyze the results, and write a complete HTML file -- which you can preview directly in the web UI's file viewer.

## Setup

The easiest way: just run `./start.sh` and open the web UI — it will prompt you for your API key on first launch.

### Advanced Setup

If you prefer to set your API key via environment variable or config file:

```bash
export SYNTHETIC_API_KEY="your-key-here"
```

Or store it in `~/.octobot/config.json`:

```json
{
  "synthetic_api_key": "your-key-here"
}
```

### Manual Installation

On first run, octobot detects missing dependencies and offers to install them automatically. Just hit Enter to confirm.

If you prefer to install manually:

```bash
pip install .                        # installs from pyproject.toml
playwright install chromium          # downloads the browser for browser tools
```

Or with requirements.txt:

```bash
pip install -r requirements.txt
playwright install chromium
```

> **Why `anthropic`?** The Synthetic API is Anthropic-compatible — it uses the same message format and tool-calling protocol. The `anthropic` Python SDK handles all the API communication so we don't reinvent the wheel.

## Usage

### Web UI (Default)

```bash
python main.py
```

Opens a chat interface in your browser at `http://localhost:5000`. Dark theme, markdown rendering, collapsible tool panels, and a swimming octopus loading animation.

### Terminal CLI

```bash
python main.py --cli
```

Type your request at the `>` prompt. Octobot will use its tools to read files, write code, run commands, browse the web, and more.

### Single Prompt (CLI)

```bash
python main.py --cli -s "List all Python files in this project"
```

### Choose a Model (CLI)

```bash
python main.py --cli -m "hf:meta-llama/Llama-3.3-70B-Instruct"
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
| `/stats` | Show smart router stats (latency, health, failover) |
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
4. On NixOS, library paths are auto-discovered via `ldd` and `nix-store`

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
main.py                  Entry point (web UI default, --cli for terminal)
start.sh                 Auto-install launcher script
octobot/
  __init__.py            Package init + version
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
  router.py              Smart model router with failover, health tracking, latency stats
  octopus.py             Swimming octopus ASCII animation (CLI loading indicator)
octoweb/
  __init__.py            Package init
  app.py                 Flask web server, SSE streaming, file/command APIs
  templates/index.html   Chat UI template with file panel, command menu, model selector
  static/style.css       Terminal-style dark theme, mobile responsive
  static/app.js          Frontend JS (SSE, markdown, tool panels, file browser, status bar)
examples/                Example files generated by Octobot
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

## Models & Benchmarks

Octobot works with any model available on the Synthetic API. We benchmarked the always-on models for tool calling performance using a simple single-tool-call task (`web_search` for "chocolate chip cookie recipe"):

| Model | Time | Input Tokens | Output Tokens | Proper `tool_use` |
|-------|------|-------------|---------------|-------------------|
| **Kimi-K2.5-NVFP4** | **1.5s** | **58** | **49** | Yes |
| Qwen3.5-397B-A17B | 2.8s | 285 | 66 | Yes |
| MiniMax-M2.5 | 3.9s | 203 | 93 | Yes |
| GLM-4.7 | ~3s | 2264 | 41 | No (XML format) |
| Qwen3-Coder-480B | 0.9s | 287 | 26 | Yes (OpenAI) |

**Kimi-K2.5-NVFP4** is the default — it's the fastest, uses the fewest tokens, and produces proper Anthropic `tool_use` blocks. GLM-4.7 works but returns tool calls as XML text, requiring a custom parser (which octobot handles automatically). Qwen3-Coder is extremely fast via the OpenAI endpoint but isn't available on the Anthropic endpoint.

### Smart Routing

Octobot includes a smart model router (`octobot/router.py`) that provides automatic failover and performance tracking:

- **Automatic failover** — if the primary model returns an error, octobot transparently retries with fallback models (Kimi-K2.5 → Qwen3.5-397B → MiniMax-M2.5 → GLM-4.7). You see a brief "Failover" notice but the conversation continues seamlessly
- **Health monitoring** — each model's success/failure rate is tracked. After 3 consecutive failures, a model enters cooldown with exponential backoff (30s → 60s → 120s → up to 5min) before being retried
- **Latency tracking** — every API call records response time, input/output tokens. Use `/stats` in the CLI or `GET /api/router` in the web UI to see per-model performance data
- **Persistent stats** — router statistics are saved to `~/.octobot/router_stats.json` across sessions, building a long-term picture of model reliability

Switch models anytime with `/model <name>` in the CLI or web UI. Check router health with `/stats`.

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `SYNTHETIC_API_KEY` | (required) | Your Synthetic API key |
| Model | `hf:nvidia/Kimi-K2.5-NVFP4` | Default model (fastest, best tool calling) |
| Max tokens | 16,384 | Maximum output tokens per response |
| Max turns | 50 | Maximum tool-calling turns per conversation |
| Subagent max turns | 15 | Maximum turns for subagent calls |
| API base URL | `https://api.synthetic.new/anthropic` | Synthetic API endpoint |

## Security

Octobot runs locally, so your files and code stay on your machine -- only the LLM API sees what you send it. On top of that, multiple safety layers protect against accidental damage:

- **Code sandbox** -- the `code_execution` tool validates Python code at the AST level, blocking imports, dangerous builtins (`eval`, `exec`, `open`, etc.), and dunder attribute access. 30-second timeout prevents infinite loops.
- **Path restrictions** -- file writes are confined to the project directory and `/tmp`. System paths (`/etc/`, `/usr/`, `/bin/`) and sensitive directories (`.ssh/`, `.gnupg/`) are blocked. Paths are resolved to absolute form to prevent traversal attacks.
- **Approval workflows** -- dangerous shell commands (`rm -rf`, `sudo`, `chmod 777`, `dd`, force push, etc.) and sensitive file writes (`.bashrc`, `.env`, `.ssh/`) require explicit `[Y/n]` confirmation before executing.
- **Prompt injection defense** -- external content (web pages, search results) is tagged with `<untrusted_content>` delimiters, scanned for injection patterns, and flagged if suspicious. The system prompt instructs the model to treat tagged content as data, never instructions.

**Limitations to be aware of:** Shell commands run with your user permissions -- the approval blocklist catches common dangers but isn't exhaustive. Prompt injection defenses raise the bar but aren't bulletproof. Sharing a browser profile gives the agent access to your cookies and sessions.

## Inspiration

- **[Octofriend](https://github.com/synthetic-lab/octofriend)** -- Open-source coding helper with great terminal UI
- **[OpenClaw](https://github.com/openclaw/openclaw)** -- Full-featured autonomous agent with skills, browser control, subagents, and loop detection
- **[PicoClaw](https://github.com/sipeed/picoclaw)** -- Ultra-lightweight Go agent with persistent memory and skills system

## License

MIT
