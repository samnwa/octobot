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

- **13 Built-in Tools** -- file ops, shell, web fetch, web search, patches, memory, and more
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
pip install anthropic rich click
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

Type your request at the `>` prompt. Octobot will use its tools to read files, write code, run commands, and more.

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
| `/reset` | Clear conversation history |
| `/model` | Show the current model |
| `/model <name>` | Switch to a different model (resets conversation) |
| `/tokens` | Show input/output token usage for the session |
| `/help` | Show all commands |
| `/quit` | Exit octobot |

## Available Tools

| Tool | Description |
|------|-------------|
| `read_file` | Read file contents with optional line offset/limit |
| `write_file` | Create or overwrite files (creates parent dirs) |
| `edit_file` | Replace an exact string in a file (surgical edits) |
| `list_files` | List directory contents or match glob patterns |
| `search_files` | Search for regex patterns across files |
| `run_command` | Execute shell commands with timeout control |
| `web_fetch` | HTTP GET a URL and extract plain text content |
| `web_search` | Search the web via DuckDuckGo |
| `apply_patch` | Apply unified diff patches to files |
| `tree` | Show directory tree structure |
| `file_info` | Get file metadata (size, dates, permissions) |
| `memory_save` | Save information to persistent memory |
| `memory_read` | Read persistent memory from previous sessions |

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
  config.py              Configuration (API key, model, base URL)
  tools.py               13 tool definitions and execution handlers
  agent.py               Core agent runtime with loop detection
  cli.py                 Interactive CLI with Rich formatting
  memory.py              Persistent memory loading
  skills.py              Skills system (SKILL.md loader)
  identity.py            Identity/personality system
```

### How It Works

1. You type a message at the prompt
2. Octobot assembles a system prompt from: identity + memory + skills
3. It sends your message + all 13 tool definitions to the model (via Synthetic API)
4. The model responds with text, thinking, and/or tool calls
5. Octobot executes tool calls locally and sends results back
6. Loop detection monitors for repetitive patterns
7. This continues until the model has a final answer (up to 50 turns)

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `SYNTHETIC_API_KEY` | (required) | Your Synthetic API key |
| Model | `hf:zai-org/GLM-4.7` | Default model (supports tool use + thinking) |
| Max tokens | 16,384 | Maximum output tokens per response |
| Max turns | 50 | Maximum tool-calling turns per conversation |
| API base URL | `https://api.synthetic.new/anthropic` | Synthetic API endpoint |

## Inspiration

- **[Octofriend](https://github.com/synthetic-lab/octofriend)** -- Open-source coding helper with great terminal UI
- **[OpenClaw](https://github.com/openclaw/openclaw)** -- Full-featured autonomous agent with skills, browser control, subagents, and loop detection
- **[PicoClaw](https://github.com/sipeed/picoclaw)** -- Ultra-lightweight Go agent with persistent memory and skills system

## Roadmap

- **Subagents** -- Spawn background agents for complex task delegation
- **Browser Automation** -- Playwright-based web interaction
- **Scheduled Tasks** -- Cron-based recurring agent runs
- **Approval Workflows** -- Confirm before destructive operations
- **Multi-provider Support** -- Connect to Anthropic, OpenAI, local models

## License

MIT
