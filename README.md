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

A locally-runnable, super-efficient AI tool-calling agent. Inspired by [Octofriend](https://github.com/synthetic-lab/octofriend), [OpenClaw](https://github.com/cline/cline), and [PicoClaw](https://github.com/nichochar/picocline) -- built for developers who want a lightweight, extensible coding assistant that runs right in their terminal.

## Features

- **6 Built-in Tools** -- read, write, edit, search files and run shell commands
- **Multi-turn Agent Loop** -- automatically chains tool calls to complete complex tasks (up to 50 turns)
- **Rich Terminal UI** -- markdown rendering, syntax highlighting, color-coded panels
- **Thinking Display** -- see the model's reasoning process in real time
- **Token Tracking** -- monitor input/output token usage per session
- **Model Switching** -- change models on the fly without restarting
- **Single-shot Mode** -- run a one-off prompt from the command line

## Setup

### 1. Get a Synthetic API Key

Sign up at [synthetic.new](https://dev.synthetic.new) and get your API key.

### 2. Set Your API Key

Set the `SYNTHETIC_API_KEY` environment variable:

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
| `/reset` | Clear conversation history and start fresh |
| `/model` | Show the current model |
| `/model <name>` | Switch to a different model (resets conversation) |
| `/tokens` | Show input/output token usage for the session |
| `/help` | Show available commands |
| `/quit` | Exit octobot |

## Available Tools

| Tool | Description |
|------|-------------|
| `read_file` | Read file contents with optional line offset/limit |
| `write_file` | Create or overwrite files (creates parent dirs automatically) |
| `edit_file` | Replace an exact string in a file (surgical edits) |
| `list_files` | List directory contents or match glob patterns |
| `search_files` | Search for regex patterns across files (like grep) |
| `run_command` | Execute shell commands with timeout and working directory control |

## Architecture

```
main.py                  Entry point
octobot/
  __init__.py            Package init
  config.py              Configuration (API key, model, base URL)
  tools.py               Tool definitions and execution handlers
  agent.py               Core agent runtime (API loop, tool dispatch, display)
  cli.py                 Interactive CLI with Rich formatting
```

### How It Works

1. You type a message at the prompt
2. Octobot sends it to the model (via Synthetic API) along with tool definitions
3. The model responds with text, thinking, and/or tool calls
4. Octobot executes any tool calls locally and sends results back to the model
5. This loop continues until the model has a final answer (up to 50 turns)

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `SYNTHETIC_API_KEY` | (required) | Your Synthetic API key |
| Model | `hf:zai-org/GLM-4.7` | Default model (supports tool use) |
| Max tokens | 16,384 | Maximum output tokens per response |
| Max turns | 50 | Maximum tool-calling turns per conversation |
| API base URL | `https://api.synthetic.new/anthropic` | Synthetic API endpoint |

## Roadmap

- **Code Execution Sandbox** -- Anthropic's `code_execution_20260120` for in-sandbox code orchestration
- **Tool Search** -- Dynamic `tool_search` with `deferred_loading` for on-demand tool discovery
- **Skills System** -- Reusable markdown-based agent behaviors (inspired by OpenClaw's AgentSkills)
- **Persistent Memory** -- Context retention across sessions via local files
- **Browser Automation** -- Playwright-based web interaction tools
- **Loop Detection** -- Prevent repetitive no-progress tool call cycles

## License

MIT
