# Octobot

Locally-runnable, super-efficient AI tool-calling agent using the Synthetic API (Anthropic-compatible).

## Architecture

```
main.py                  - Entry point
octobot/
  __init__.py            - Package init
  config.py              - Configuration (API key, model, base URL)
  tools.py               - Tool definitions and execution handlers
  agent.py               - Core agent runtime (API calls, tool loop, display)
  cli.py                 - Interactive CLI with Rich formatting, ASCII banner
README.md                - Comprehensive project documentation
```

## Key Features

- **Tool Calling**: 6 tools (read_file, write_file, list_files, run_command, search_files, edit_file)
- **Efficient Agent Loop**: Multi-turn tool calling with max 50 turns per conversation
- **Rich CLI**: Blue-themed ASCII banner with octopus art, markdown rendering, syntax highlighting, thinking display, token tracking
- **Slash Commands**: /reset, /model, /tokens, /help, /quit

## Configuration

- **API**: Synthetic API at `https://api.synthetic.new/anthropic`
- **Model**: `hf:zai-org/GLM-4.7` (default, supports tool use)
- **Secret**: `SYNTHETIC_API_KEY` (stored as Replit secret)

## Dependencies

- anthropic (SDK for API calls)
- rich (terminal formatting)
- click (CLI framework)

## Running

```bash
python main.py                          # Interactive mode
python main.py -s "your prompt"         # Single prompt mode
python main.py -m "hf:model/name"       # Use a different model
```
